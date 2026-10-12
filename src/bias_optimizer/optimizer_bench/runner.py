"""Protocol-checked, common-budget execution for all V3.2 optimizers."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from time import perf_counter
from typing import Any

from bias_optimizer.data.mnist import MNISTDataConfig
from bias_optimizer.domain.program import ProgramBiasSpec
from bias_optimizer.dsl.compiler import ProgramCompiler
from bias_optimizer.dsl.validator import ProgramConstraints, SearchTrack
from bias_optimizer.evaluation.protocol import load_frozen_protocol
from bias_optimizer.ml.evaluator import Evaluator, ProgramEvaluator
from bias_optimizer.novelty.descriptors import mechanism_family
from bias_optimizer.optimizer_bench.artifacts import register_run
from bias_optimizer.optimizer_bench.budget import SearchBudget
from bias_optimizer.optimizer_bench.objective import ast_hash
from bias_optimizer.optimizer_bench.optimizers.base import (
    OptimizationContext,
    Optimizer,
    ProposalBatch,
)
from bias_optimizer.optimizer_bench.optimizers.genetic_programming import (
    GeneticProgrammingOptimizer,
)
from bias_optimizer.optimizer_bench.optimizers.llm_common import (
    LLMIterativeOptimizer,
    LLMOneShotOptimizer,
)
from bias_optimizer.optimizer_bench.optimizers.typed_random import TypedRandomOptimizer
from bias_optimizer.optimizer_bench.oracle import SearchOracle
from bias_optimizer.optimizer_bench.schema import (
    CandidateEvaluation,
    CandidateProposal,
    SearchTrace,
)
from bias_optimizer.optimizer_bench.trace import write_trace

ROOT = Path(__file__).resolve().parents[3]
PROTOCOL_PATH = ROOT / "results/v32/protocol.json"
PROTOCOL_CHECKSUM_PATH = ROOT / "results/v32/protocol.sha256"
MANIFEST_PATH = ROOT / "results/v32/manifest.json"
OPTIMIZERS = (
    "typed_random",
    "genetic_programming",
    "llm_one_shot",
    "llm_iterative",
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_protocol(root: Path = ROOT) -> dict[str, Any]:
    root = Path(root)
    load_frozen_protocol(root)
    protocol_path = root / "results/v32/protocol.json"
    checksum_path = root / "results/v32/protocol.sha256"
    manifest_path = root / "results/v32/manifest.json"
    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    digest = sha256(protocol_path)
    expected_line = f"{digest}  protocol.json"
    if checksum_path.read_text(encoding="ascii").strip() != expected_line:
        raise ValueError("V3.2 protocol checksum is invalid")
    if manifest.get("protocol", {}).get("sha256") != digest:
        raise ValueError("V3.2 protocol hash does not match its manifest")
    protected = protocol["protected_inputs"]["protected_source_sha256"]
    for relative, expected in protected.items():
        path = root / relative
        if not path.is_file() or sha256(path) != expected:
            raise ValueError(f"protected V2/V3 source changed: {relative}")
    input_hashes = {
        "results/v3_program_search_discovery.jsonl": protocol["protected_inputs"][
            "v3_archive_sha256"
        ],
        "results/v3_frozen_finalists.json": protocol["protected_inputs"][
            "v3_finalist_manifest_sha256"
        ],
        "results/program_search_discovery.jsonl": protocol["protected_inputs"][
            "v2_archive_sha256"
        ],
        "results/v31/protocol.json": protocol["protected_inputs"][
            "v31_protocol_sha256"
        ],
        "results/v31/manifest.json": protocol["protected_inputs"][
            "v31_manifest_sha256"
        ],
    }
    for relative, expected in input_hashes.items():
        if sha256(root / relative) != expected:
            raise ValueError(f"protected V2/V3/V3.1 artifact changed: {relative}")
    protocol["protocol_sha256"] = digest
    return protocol


def load_seed_programs(protocol: dict[str, Any]) -> tuple[ProgramBiasSpec, ...]:
    seeds = tuple(
        ProgramBiasSpec.from_dict(item["bias"])
        for item in protocol["frozen_search_space"]["seed_programs"]
    )
    if len(seeds) != 20 or len({item.program.to_json() for item in seeds}) != 20:
        raise ValueError("frozen protocol must contain 20 unique seed ASTs")
    return seeds


def optimizer_factory(
    name: str,
    seed: int,
    constraints: ProgramConstraints,
    response_path: Path,
    *,
    client: object | None = None,
) -> Optimizer:
    if name == "typed_random":
        return TypedRandomOptimizer(seed, constraints)
    if name == "genetic_programming":
        return GeneticProgrammingOptimizer(seed, constraints)
    if name == "llm_one_shot":
        return LLMOneShotOptimizer(seed, constraints, response_path, client=client)
    if name == "llm_iterative":
        return LLMIterativeOptimizer(seed, constraints, response_path, client=client)
    raise ValueError(f"unknown optimizer {name!r}")


def _rejected_by_constraint(message: str) -> bool:
    lowered = message.lower()
    return any(
        token in lowered
        for token in ("exceeds", "limit", "not allowed", "must be at most")
    )


def _seed_proposal(
    bias: ProgramBiasSpec, optimizer: str, seed: int, index: int
) -> CandidateProposal:
    ast_digest = ast_hash(bias.program)
    return CandidateProposal(
        program=bias.program,
        proposal_id=f"seed:{index}:{ast_digest}",
        optimizer=optimizer,
        optimizer_seed=seed,
        generation=0,
        parent_ids=(),
        mechanism_metadata={
            "name": bias.name,
            "hypothesis": bias.hypothesis,
            "mechanism": bias.mechanism,
            "prediction": bias.prediction,
            "falsification": bias.falsification,
            "seed_candidate": True,
        },
        proposal_attempt=1,
    )


def run_optimizer(
    optimizer_name: str,
    optimizer_seed: int,
    *,
    budget: SearchBudget | None = None,
    output_root: Path = ROOT / "results/v32/runs",
    data_dir: Path | None = None,
    client: object | None = None,
    phase: str = "primary",
    condition: str | None = None,
) -> SearchTrace:
    protocol = verify_protocol()
    if phase == "semantic_ablation":
        if condition not in {"semantic_dsl", "anonymized_dsl"}:
            raise ValueError("semantic-ablation runs require a supported condition")
    elif condition is not None:
        raise ValueError("condition is only valid for semantic-ablation runs")
    if optimizer_name not in OPTIMIZERS:
        raise ValueError(f"optimizer must be one of {OPTIMIZERS}")
    if type(optimizer_seed) is not int or optimizer_seed < 0:
        raise ValueError("optimizer_seed must be a non-negative integer")
    selected_budget = budget or SearchBudget()
    if selected_budget.seed_evaluations != 20:
        raise ValueError("the frozen V3.2 search requires exactly 20 seed evaluations")
    seeds = load_seed_programs(protocol)
    constraints = ProgramConstraints(
        track=SearchTrack.DISCOVERY,
        max_feature_dim=128,
        max_depth=6,
        max_nodes=127,
        forbid_raw_pixels=True,
        require_vector_root=False,
    )
    compiler = ProgramCompiler(constraints)
    data_config = MNISTDataConfig(data_dir=Path(data_dir)) if data_dir else None
    evaluator = ProgramEvaluator(
        evaluator=Evaluator(data_config=data_config),
        compiler=compiler,
        train_sizes=(500,),
    )
    oracle = SearchOracle(evaluator=evaluator, constraints=constraints)
    run_dir = Path(output_root) / optimizer_name / f"seed_{optimizer_seed}"
    response_path = run_dir / "llm_responses.jsonl"
    if optimizer_name.startswith("llm_"):
        # A restarted run must begin with a fresh proposal-batch counter and archive.
        response_path.unlink(missing_ok=True)
    optimizer = optimizer_factory(
        optimizer_name,
        optimizer_seed,
        constraints,
        response_path,
        client=client,
    )

    started = perf_counter()
    proposals: list[CandidateProposal] = []
    evaluated: list[CandidateEvaluation] = []
    seen_ids: set[str] = set()
    for index, bias in enumerate(seeds, start=1):
        compiler.compile(bias.program)
        proposal = _seed_proposal(bias, optimizer_name, optimizer_seed, index)
        row = oracle.evaluate(
            bias.program,
            evaluation_index=index,
            previously_evaluated=tuple(seed.program for seed in seeds[: index - 1]),
            metadata=proposal.mechanism_metadata,
        )
        proposals.append(proposal)
        evaluated.append(row)
        seen_ids.add(row.candidate_id)
    optimizer.on_seed_evaluations(tuple(proposals), tuple(evaluated))

    proposal_attempts = valid_proposals = invalid = duplicates = constrained = 0
    llm_calls = llm_tokens = 0
    proposal_time_ms = 0.0
    termination_reason: str | None = None
    generation = 1

    while len(evaluated) < selected_budget.total_evaluations:
        generation_target = min(18, selected_budget.total_evaluations - len(evaluated))
        generation_start_count = len(evaluated)
        while len(evaluated) - generation_start_count < generation_target:
            remaining_attempts = (
                selected_budget.max_proposal_attempts - proposal_attempts
            )
            if remaining_attempts <= 0:
                termination_reason = "proposal_attempt_cap_reached"
                break
            remaining_in_generation = generation_target - (
                len(evaluated) - generation_start_count
            )
            context = OptimizationContext(
                optimizer=optimizer_name,
                optimizer_seed=optimizer_seed,
                generation=generation,
                proposal_attempt_start=proposal_attempts + 1,
                remaining_attempts=remaining_attempts,
                batch_size=min(4, remaining_in_generation),
                constraints=constraints,
                seed_programs=tuple(seed.program for seed in seeds),
                evaluated=tuple(evaluated),
            )
            proposal_started = perf_counter()
            batch: ProposalBatch = optimizer.propose(context)
            proposal_time_ms += (perf_counter() - proposal_started) * 1_000
            if batch.attempts > remaining_attempts:
                termination_reason = "proposal_attempt_cap_would_be_exceeded"
                break
            proposal_attempts += batch.attempts
            valid_proposals += batch.valid_proposal_count
            invalid += batch.invalid_count
            duplicates += batch.duplicate_count
            constrained += batch.rejected_by_constraint_count
            llm_calls += batch.llm_calls
            llm_tokens += batch.llm_tokens
            if not batch.proposals and batch.attempts == 0:
                termination_reason = (
                    "optimizer_could_not_propose_within_remaining_budget"
                )
                break
            for proposal in batch.proposals:
                try:
                    compiler.compile(proposal.program)
                except (TypeError, ValueError) as exc:
                    if _rejected_by_constraint(str(exc)):
                        constrained += 1
                    else:
                        invalid += 1
                    continue
                candidate_id = ast_hash(proposal.program)
                if candidate_id in seen_ids:
                    duplicates += 1
                    continue
                requested_family = (proposal.mechanism_metadata or {}).get(
                    "requested_mechanism_family"
                )
                if (
                    requested_family is not None
                    and mechanism_family(proposal.program) != requested_family
                ):
                    constrained += 1
                    continue
                metadata = {
                    **(proposal.mechanism_metadata or {}),
                    "generation": generation,
                    "parent_ids": list(proposal.parent_ids),
                    "proposal_id": proposal.proposal_id,
                    "proposal_attempt": proposal.proposal_attempt,
                }
                row = oracle.evaluate(
                    proposal.program,
                    evaluation_index=len(evaluated) + 1,
                    previously_evaluated=tuple(
                        prior.program
                        for prior in evaluated
                        if prior.program is not None
                    ),
                    metadata=metadata,
                )
                evaluated.append(row)
                seen_ids.add(candidate_id)
                optimizer.on_evaluation(proposal, row)
                if len(evaluated) >= selected_budget.total_evaluations:
                    break
            if batch.attempts == 0 and not batch.proposals:
                termination_reason = "optimizer_returned_no_proposals"
                break
        optimizer.finish_generation()
        if termination_reason is not None:
            break
        generation += 1

    complete = len(evaluated) == selected_budget.total_evaluations
    if not complete and termination_reason is None:
        termination_reason = "run_incomplete"
    trace = SearchTrace(
        optimizer=optimizer_name,
        optimizer_seed=optimizer_seed,
        evaluated_candidates=tuple(evaluated),
        proposal_attempts=proposal_attempts,
        valid_proposal_count=valid_proposals,
        invalid_count=invalid,
        duplicate_count=duplicates,
        rejected_by_constraint_count=constrained,
        llm_calls=llm_calls,
        llm_tokens=llm_tokens,
        proposal_time_ms=proposal_time_ms,
        evaluation_time_ms=oracle.evaluation_time_ms,
        total_wall_time_ms=(perf_counter() - started) * 1_000,
        complete=complete,
        termination_reason=termination_reason,
        budget_total_evaluations=selected_budget.total_evaluations,
        budget_seed_evaluations=selected_budget.seed_evaluations,
        budget_max_proposal_attempts=selected_budget.max_proposal_attempts,
    )
    path = run_dir / "trace.json"
    write_trace(trace, path)
    register_run(
        trace,
        path,
        phase=phase,
        manifest_path=MANIFEST_PATH,
        condition=condition,
    )
    return trace
