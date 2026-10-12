from __future__ import annotations

from bias_optimizer.dsl.ast import Expr
from bias_optimizer.novelty.descriptors import describe_program
from bias_optimizer.optimizer_bench.objective import ast_hash
from bias_optimizer.optimizer_bench.schema import CandidateEvaluation, SearchTrace
from bias_optimizer.optimizer_bench.statistics import summarize_primary


def _partial_trace() -> SearchTrace:
    evaluations = []
    for index in range(1, 23):
        program = Expr(
            "connected_components",
            (
                Expr(
                    "threshold",
                    (Expr("image"),),
                    {"value": index / 100},
                ),
            ),
        )
        evaluations.append(
            CandidateEvaluation(
                candidate_id=ast_hash(program),
                evaluation_index=index,
                fitness=0.5 + index / 1_000,
                accuracy=0.7,
                feature_dim=1,
                runtime_ms=2.0,
                structural_descriptor=describe_program(program).cell,
                program=program,
                metadata={"structural_novelty": 0.1},
            )
        )
    return SearchTrace(
        optimizer="typed_random",
        optimizer_seed=101,
        evaluated_candidates=tuple(evaluations),
        proposal_attempts=10,
        valid_proposal_count=8,
        invalid_count=0,
        duplicate_count=4,
        rejected_by_constraint_count=2,
        llm_calls=0,
        llm_tokens=0,
        proposal_time_ms=5.0,
        evaluation_time_ms=100.0,
        total_wall_time_ms=150.0,
        complete=False,
        termination_reason="proposal_attempt_cap_reached",
        budget_total_evaluations=200,
        budget_seed_evaluations=20,
        budget_max_proposal_attempts=540,
    )


def test_incomplete_runs_are_censored_at_the_last_evaluation() -> None:
    protocol = {
        "study_id": "test-v32",
        "protocol_sha256": "frozen-test-hash",
        "primary_metrics": {
            "search_curve_indices": list(range(20, 201)),
            "thresholds": {"test_cutoff": {"value": 0.51}},
            "paired_bootstrap": {"seed": 11, "resamples": 100},
        },
    }
    summary = summarize_primary((_partial_trace(),), protocol)
    optimizer = summary["optimizers"]["typed_random"]

    assert summary["complete_runs"] == 0
    assert optimizer["metrics"]["final_best_fitness"]["n"] == 0
    assert optimizer["metrics"]["incomplete_last_observed_best_fitness"]["n"] == 1
    assert optimizer["curve"]["n_at_evaluation"][2] == 1
    assert optimizer["curve"]["n_at_evaluation"][3] == 0
    assert optimizer["thresholds"]["test_cutoff"]["probability_reached"] is None
    assert (
        optimizer["thresholds"]["test_cutoff"][
            "incomplete_evaluations_to_threshold"
        ]["mean"]
        == 20
    )
