from __future__ import annotations

import json
import random

import numpy as np

from bias_optimizer.domain.evaluation import Evaluation
from bias_optimizer.domain.program import ProgramBiasSpec
from bias_optimizer.dsl.ast import Expr
from bias_optimizer.dsl.compiler import ProgramCompiler
from bias_optimizer.dsl.validator import ProgramConstraints, SearchTrack
from bias_optimizer.llm.program_proposer import _compact_program_signature
from bias_optimizer.novelty.descriptors import describe_program
from bias_optimizer.optimizer_bench.budget import SearchBudget
from bias_optimizer.optimizer_bench.mutations import typed_crossover, typed_mutation
from bias_optimizer.optimizer_bench.objective import ast_hash
from bias_optimizer.optimizer_bench.optimizers.base import OptimizationContext
from bias_optimizer.optimizer_bench.optimizers.llm_common import (
    LLMIterativeOptimizer,
    LLMOneShotOptimizer,
)
from bias_optimizer.optimizer_bench.optimizers.typed_random import TypedRandomOptimizer
from bias_optimizer.optimizer_bench.oracle import SearchOracle
from bias_optimizer.optimizer_bench.random_ast import SamplingFailure, sample_random_ast
from bias_optimizer.optimizer_bench.runner import (
    OPTIMIZERS,
    load_seed_programs,
    verify_protocol,
)
from bias_optimizer.optimizer_bench.schema import CandidateEvaluation, CandidateProposal
from bias_optimizer.optimizer_bench.trace import read_trace, write_trace


class _FixedProgramEvaluator:
    def __init__(self) -> None:
        self.calls = 0

    def evaluate(self, _bias):
        self.calls += 1
        return Evaluation(
            accuracy_500=0.75,
            accuracy_5000=None,
            feature_dim=3,
            feature_runtime_ms=10.0,
            training_runtime_ms=2.0,
            inference_runtime_ms=1.0,
            confusion_matrix=np.zeros((10, 10), dtype=np.int64),
        )


class _PromptClient:
    model = "qwen3.5:35b-mlx"

    def __init__(self, program: Expr) -> None:
        self.program = program
        self.prompts: list[str] = []

    def generate(self, prompt: str) -> str:
        self.prompts.append(prompt)
        return json.dumps(
            {
                "proposals": [
                    {
                        "name": "mock_candidate",
                        "hypothesis": "A typed mock proposal tests prompt boundaries.",
                        "mechanism": "mock structure",
                        "program": self.program.to_dict(),
                        "prediction": "The candidate has a measurable validation score.",
                        "falsification": "Reject it if the score is poor.",
                    }
                ]
            }
        )


def _constraints() -> ProgramConstraints:
    return ProgramConstraints(
        track=SearchTrack.DISCOVERY,
        max_feature_dim=128,
        max_depth=6,
        max_nodes=127,
        forbid_raw_pixels=True,
    )


def _candidate() -> Expr:
    return Expr(
        "normalize",
        (Expr("spatial_split", (Expr("image"),), {"rows": 1, "cols": 1}),),
    )


def _context(
    seed_programs: tuple[Expr, ...], *, generation: int = 1
) -> OptimizationContext:
    return OptimizationContext(
        optimizer="llm_one_shot",
        optimizer_seed=101,
        generation=generation,
        proposal_attempt_start=1,
        remaining_attempts=540,
        batch_size=1,
        constraints=_constraints(),
        seed_programs=seed_programs,
        evaluated=(),
    )


def test_all_optimizers_share_same_seed_programs() -> None:
    protocol = verify_protocol()
    seeds = load_seed_programs(protocol)
    assert len(seeds) == 20
    assert len({seed.program.to_json() for seed in seeds}) == 20
    assert tuple(OPTIMIZERS) == (
        "typed_random",
        "genetic_programming",
        "llm_one_shot",
        "llm_iterative",
    )


def test_all_optimizers_share_same_budget() -> None:
    protocol = verify_protocol()
    budget = SearchBudget()
    assert (
        budget.total_evaluations
        == protocol["budget"]["total_unique_evaluations_per_run"]
        == 200
    )
    assert budget.seed_evaluations == protocol["budget"]["seed_evaluations"] == 20
    assert budget.new_evaluations == 180
    assert budget.max_proposal_attempts == 3 * budget.new_evaluations


def test_same_candidate_same_oracle_result() -> None:
    evaluator = _FixedProgramEvaluator()
    oracle = SearchOracle(evaluator=evaluator, constraints=_constraints())
    first = oracle.evaluate(_candidate(), evaluation_index=1)
    second = oracle.evaluate(_candidate(), evaluation_index=2)
    assert first is second
    assert evaluator.calls == 1
    assert oracle.evaluated_count == 1


def test_optimizer_cannot_access_labels_or_test_data() -> None:
    oracle = SearchOracle(
        evaluator=_FixedProgramEvaluator(), constraints=_constraints()
    )
    proposal = CandidateProposal(
        program=_candidate(),
        proposal_id="proposal-1",
        optimizer="typed_random",
        optimizer_seed=101,
        generation=1,
        parent_ids=(),
        mechanism_metadata=None,
        proposal_attempt=1,
    )
    context = _context(())
    assert not hasattr(oracle, "validation_labels")
    assert not hasattr(oracle, "test_data")
    assert not hasattr(context, "labels")
    assert not hasattr(proposal, "test_data")


def test_random_ast_always_type_valid_or_explicitly_rejected() -> None:
    rng = random.Random(303)
    compiler = ProgramCompiler(_constraints())
    returned = 0
    rejected = 0
    for _ in range(200):
        try:
            program = sample_random_ast(rng, constraints=_constraints())
        except SamplingFailure:
            rejected += 1
            continue
        compiler.compile(program)
        assert "flatten_pixels" not in {node.op for node in _walk(program)}
        returned += 1
    assert returned > 0
    assert returned + rejected == 200


def test_gp_mutation_preserves_types() -> None:
    compiler = ProgramCompiler(_constraints())
    seeds = load_seed_programs(verify_protocol())
    failures = 0
    for index in range(20):
        try:
            mutated = typed_mutation(
                seeds[index].program, random.Random(index), constraints=_constraints()
            )
        except SamplingFailure:
            failures += 1
            continue
        compiler.compile(mutated)
    assert failures < 20


def test_gp_crossover_preserves_types() -> None:
    image = Expr("image")
    left = Expr(
        "concat",
        (
            Expr("spatial_split", (image,), {"rows": 1, "cols": 1}),
            Expr("spatial_split", (image,), {"rows": 1, "cols": 2}),
        ),
    )
    right = Expr(
        "concat",
        (
            Expr("spatial_split", (image,), {"rows": 1, "cols": 2}),
            Expr("spatial_split", (image,), {"rows": 1, "cols": 1}),
        ),
    )
    child = typed_crossover(left, right, random.Random(404), constraints=_constraints())
    ProgramCompiler(_constraints()).compile(child)


def test_llm_one_shot_receives_no_scores(tmp_path) -> None:
    seeds = load_seed_programs(verify_protocol())
    client = _PromptClient(_candidate())
    optimizer = LLMOneShotOptimizer(
        101,
        _constraints(),
        response_path=tmp_path / "responses.jsonl",
        client=client,
    )
    proposals = tuple(
        CandidateProposal(
            program=seed.program,
            proposal_id=f"seed-{index}",
            optimizer="llm_one_shot",
            optimizer_seed=101,
            generation=0,
            parent_ids=(),
            mechanism_metadata={
                "name": seed.name,
                "hypothesis": seed.hypothesis,
                "mechanism": seed.mechanism,
                "prediction": seed.prediction,
                "falsification": seed.falsification,
            },
            proposal_attempt=1,
        )
        for index, seed in enumerate(seeds)
    )
    rows = tuple(
        CandidateEvaluation(
            candidate_id=ast_hash(seed.program),
            evaluation_index=index,
            fitness=0.5,
            accuracy=0.5,
            feature_dim=3,
            runtime_ms=10.0,
            structural_descriptor=describe_program(seed.program).cell,
            program=seed.program,
        )
        for index, seed in enumerate(seeds, start=1)
    )
    optimizer.on_seed_evaluations(proposals, rows)
    optimizer.propose(_context(tuple(seed.program for seed in seeds)))
    prompt = client.prompts[0]
    assert '"top_candidates":[]' in prompt
    assert '"accuracy_500"' not in prompt
    assert '"underexplored_cells":[]' in prompt
    assert all(
        _compact_program_signature(seed.program.to_json()) in prompt for seed in seeds
    )


def test_one_shot_family_schedule_does_not_advance_from_evaluations(tmp_path) -> None:
    optimizer = LLMOneShotOptimizer(
        101,
        _constraints(),
        response_path=tmp_path / "responses.jsonl",
        client=_PromptClient(_candidate()),
    )
    program = _candidate()
    proposal = CandidateProposal(
        program=program,
        proposal_id="one-shot-test",
        optimizer="llm_one_shot",
        optimizer_seed=101,
        generation=1,
        parent_ids=(),
        mechanism_metadata=None,
        proposal_attempt=1,
    )
    evaluation = CandidateEvaluation(
        candidate_id=ast_hash(program),
        evaluation_index=21,
        fitness=0.8,
        accuracy=0.8,
        feature_dim=1,
        runtime_ms=10.0,
        structural_descriptor=describe_program(program).cell,
        program=program,
    )
    optimizer.on_evaluation(proposal, evaluation)
    assert optimizer._family_counts == {}
    assert optimizer._one_shot_schedule_position == 0


def test_llm_iterative_receives_only_allowed_history(tmp_path) -> None:
    seeds = load_seed_programs(verify_protocol())
    client = _PromptClient(_candidate())
    optimizer = LLMIterativeOptimizer(
        101,
        _constraints(),
        response_path=tmp_path / "iterative.jsonl",
        client=client,
    )
    proposals = tuple(
        CandidateProposal(
            program=seed.program,
            proposal_id=f"seed-{index}",
            optimizer="llm_iterative",
            optimizer_seed=101,
            generation=0,
            parent_ids=(),
            mechanism_metadata={
                "name": seed.name,
                "hypothesis": seed.hypothesis,
                "mechanism": seed.mechanism,
                "prediction": seed.prediction,
                "falsification": seed.falsification,
            },
            proposal_attempt=1,
        )
        for index, seed in enumerate(seeds)
    )
    rows = tuple(
        CandidateEvaluation(
            candidate_id=ast_hash(seed.program),
            evaluation_index=index,
            fitness=0.5,
            accuracy=0.5,
            feature_dim=3,
            runtime_ms=10.0,
            structural_descriptor=describe_program(seed.program).cell,
            program=seed.program,
            metadata={
                "name": seed.name,
                "hypothesis": seed.hypothesis,
                "mechanism": seed.mechanism,
                "prediction": seed.prediction,
                "falsification": seed.falsification,
            },
        )
        for index, seed in enumerate(seeds, start=1)
    )
    optimizer.on_seed_evaluations(proposals, rows)
    optimizer.propose(_context(tuple(seed.program for seed in seeds)))
    prompt = client.prompts[0]
    assert '"accuracy_500"' in prompt
    assert '"underexplored_cells"' in prompt
    assert '"explored_programs"' in prompt
    assert '"mechanism_focus"' in prompt
    assert "confusion_matrix" not in prompt
    assert all(
        _compact_program_signature(seed.program.to_json()) in prompt for seed in seeds
    )


def test_one_shot_does_not_precount_duplicate_adaptive_history(tmp_path) -> None:
    optimizer = LLMOneShotOptimizer(
        101,
        _constraints(),
        response_path=tmp_path / "responses.jsonl",
        client=_PromptClient(_candidate()),
    )
    bias = ProgramBiasSpec(
        name="repeated",
        hypothesis="A valid program is repeated across one-shot batches.",
        mechanism="mock",
        program=_candidate(),
        prediction="It can be parsed.",
        falsification="Reject if invalid.",
    )
    response = json.dumps({"proposals": [bias.to_dict()]})
    optimizer._seen_asts.add(bias.program.to_json())
    accounting = optimizer._account_responses(
        ({"response": response},),
        1,
        duplicate_reference=optimizer._seed_asts,
    )
    assert accounting["validity"] == (1, 0, 0, 0)


def test_duplicates_do_not_consume_evaluation_budget() -> None:
    evaluator = _FixedProgramEvaluator()
    oracle = SearchOracle(evaluator=evaluator, constraints=_constraints())
    seen: set[str] = set()
    candidate = _candidate()
    candidate_id = ast_hash(candidate)
    seen.add(candidate_id)
    if candidate_id not in seen:
        oracle.evaluate(candidate, evaluation_index=1)
    assert oracle.evaluated_count == 0
    assert evaluator.calls == 0


def test_seed_candidates_consume_evaluation_budget() -> None:
    budget = SearchBudget()
    seeds = load_seed_programs(verify_protocol())
    assert len(seeds) == budget.seed_evaluations == 20
    assert budget.total_evaluations - len(seeds) == 180


def test_candidate_hash_is_canonical() -> None:
    image = Expr("image")
    left = Expr("spatial_split", (image,), {"rows": 2, "cols": 3})
    right = Expr("spatial_split", (image,), {"cols": 3, "rows": 2})
    assert left.to_json() == right.to_json()
    assert ast_hash(left) == ast_hash(right)


def test_same_optimizer_seed_is_reproducible_where_deterministic() -> None:
    first = TypedRandomOptimizer(505, _constraints())
    second = TypedRandomOptimizer(505, _constraints())
    context = _context(())
    proposal_a = first.propose(context).proposals[0]
    proposal_b = second.propose(context).proposals[0]
    assert proposal_a.program.to_json() == proposal_b.program.to_json()


def test_protocol_hash_verified_before_run() -> None:
    protocol = verify_protocol()
    assert protocol["study_id"] == "v3.2-optimizer-value-study"


def test_trace_serialization_round_trip(tmp_path) -> None:
    row = CandidateEvaluation(
        candidate_id=ast_hash(_candidate()),
        evaluation_index=1,
        fitness=0.7,
        accuracy=0.75,
        feature_dim=1,
        runtime_ms=10.0,
        structural_descriptor=describe_program(_candidate()).cell,
        program=_candidate(),
    )
    from bias_optimizer.optimizer_bench.schema import SearchTrace

    trace = SearchTrace(
        optimizer="typed_random",
        optimizer_seed=101,
        evaluated_candidates=(row,),
        proposal_attempts=1,
        valid_proposal_count=1,
        invalid_count=0,
        duplicate_count=0,
        rejected_by_constraint_count=0,
        llm_calls=0,
        llm_tokens=0,
        proposal_time_ms=1.0,
        evaluation_time_ms=2.0,
        total_wall_time_ms=3.0,
        complete=False,
    )
    path = tmp_path / "trace.json"
    write_trace(trace, path)
    loaded = read_trace(path)
    assert loaded.to_dict() == trace.to_dict()


def _walk(program: Expr) -> tuple[Expr, ...]:
    return (program, *(node for child in program.args for node in _walk(child)))
