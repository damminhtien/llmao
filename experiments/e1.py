"""Preflight and run the bounded exploratory G0 vs G_pilot search."""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import urlopen

from bias_optimizer.data.mnist_e1 import (
    E1MNISTDataConfig,
    load_mnist_e1_search_data,
)
from bias_optimizer.dsl.ast import Expr
from bias_optimizer.dsl.compiler import ProgramCompiler
from bias_optimizer.dsl.validator import ProgramConstraints, SearchTrack
from bias_optimizer.evaluation.protocol import EvaluationDataset
from bias_optimizer.llm.ollama_client import OllamaLLMClient
from bias_optimizer.ml.evaluator import Evaluator, ProgramEvaluator
from bias_optimizer.optimizer_bench.budget import SearchBudget
from bias_optimizer.optimizer_bench.e1 import (
    DEFAULT_E1_RESOURCE_CAPS,
    E1BudgetedClient,
    E1BudgetExceeded,
    E1IterativeOptimizer,
    E1TokenAccountingError,
    E1TokenLedger,
    common_seed_proposals,
    load_e1_pilot_language,
    verify_e1_grammar,
)
from bias_optimizer.optimizer_bench.objective import ast_hash
from bias_optimizer.optimizer_bench.optimizers.base import OptimizationContext
from bias_optimizer.optimizer_bench.oracle import SearchOracle
from bias_optimizer.optimizer_bench.runner import load_seed_programs, verify_protocol
from bias_optimizer.optimizer_bench.schema import (
    CandidateEvaluation,
    CandidateProposal,
    SearchTrace,
)
from bias_optimizer.optimizer_bench.trace import write_trace
from bias_optimizer.v4.language import G0_LANGUAGE, MacroLanguage

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = ROOT / "results/v4/e1/runs/seed_101"
DATA_CONFIG = E1MNISTDataConfig()
SEED = 101
_CONSTRAINTS = ProgramConstraints(
    track=SearchTrack.DISCOVERY,
    max_feature_dim=128,
    max_depth=6,
    max_nodes=127,
    forbid_raw_pixels=True,
    require_vector_root=False,
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _e1_candidate_eligibility(
    program: Expr,
    compiler: ProgramCompiler,
    seen_ids: set[str],
) -> tuple[str | None, str | None]:
    """Apply E1's structural and expanded-AST uniqueness gates."""
    try:
        compiler.compile(program)
    except (TypeError, ValueError):
        return "constraint", None
    candidate_id = ast_hash(program)
    if candidate_id in seen_ids:
        return "duplicate", candidate_id
    return None, candidate_id


def _active_v4_conflicts() -> list[str]:
    conflicts: list[str] = []
    tmux = subprocess.run(["tmux", "ls"], capture_output=True, text=True, check=False)
    if tmux.returncode == 0:
        conflicts.extend(
            f"tmux: {line}"
            for line in tmux.stdout.splitlines()
            if re.search(r"(?i)(v14|v4|discovery)", line)
        )
    ps = subprocess.run(
        ["ps", "-axo", "pid=,command="], capture_output=True, text=True, check=True
    )
    for line in ps.stdout.splitlines():
        match = re.match(r"\s*(\d+)\s+(.*)", line)
        if match is None or int(match.group(1)) == os.getpid():
            continue
        command = match.group(2)
        if re.search(
            r"(?i)(v14|v4_run_primary_discovery|discovery-\d{4}|codex-v4-sandbox)",
            command,
        ) and "experiments.e1" not in command:
            conflicts.append(f"process {match.group(1)}: {command}")
    return conflicts


def _verify_local_model(*, check_server: bool) -> dict[str, str | bool]:
    client = OllamaLLMClient.from_environment()
    host = urlsplit(client.base_url).hostname
    if client.model != "qwen3.5:35b-mlx":
        raise ValueError("E1 requires the existing qwen3.5:35b-mlx Ollama model")
    if host not in {"127.0.0.1", "localhost", "::1"}:
        raise ValueError("E1 requires a local Ollama endpoint")
    result: dict[str, str | bool] = {
        "model": client.model,
        "base_url": client.base_url,
        "server_available": False,
    }
    if check_server:
        with urlopen(f"{client.base_url}/api/tags", timeout=3) as response:
            tags = json.loads(response.read())
        names = {
            model.get("name")
            for model in tags.get("models", [])
            if isinstance(model, dict)
        }
        if client.model not in names:
            raise ValueError(f"pinned local Ollama model is unavailable: {client.model}")
        result["server_available"] = True
    return result


def _verified_protocol_and_seeds() -> tuple[dict, tuple]:
    protocol = verify_protocol(ROOT)
    seeds = load_seed_programs(protocol)
    if len(seeds) != 20 or len({bias.program.to_json() for bias in seeds}) != 20:
        raise ValueError("E1 must use the 20 unique frozen V3.2 initial programs")
    compiler = ProgramCompiler(_CONSTRAINTS)
    for bias in seeds:
        compiler.compile(bias.program)
    return protocol, seeds


def run_preflight(
    *,
    data_config: E1MNISTDataConfig = DATA_CONFIG,
    output_root: Path = OUTPUT_ROOT,
    check_model_server: bool = True,
) -> dict[str, object]:
    """Run no-token checks and load only checksum-pinned training IDX files."""
    protocol, seeds = _verified_protocol_and_seeds()
    language, pilot_manifest = load_e1_pilot_language(ROOT)
    grammar_g0 = verify_e1_grammar(None)
    grammar_pilot = verify_e1_grammar(language)
    search_data = load_mnist_e1_search_data(data_config)
    dataset = EvaluationDataset.from_mnist_search(search_data)
    if dataset.evaluation_partition != "official_train_validation":
        raise ValueError("E1 search split must come only from the official train partition")
    if len(search_data.train_labels) != 58_000 or len(search_data.validation_labels) != 2_000:
        raise ValueError("E1 search loader did not preserve the frozen V3.2 split sizes")
    conflicts = _active_v4_conflicts()
    if conflicts:
        raise RuntimeError("active V4 run conflicts with E1: " + "; ".join(conflicts))
    run_root = Path(output_root)
    if run_root.exists():
        raise FileExistsError(f"E1 output directory must be fresh: {run_root}")
    model = _verify_local_model(check_server=check_model_server)
    data_manifest_path = data_config.cache_dir / "e1_search_data_manifest.json"
    data_manifest = json.loads(data_manifest_path.read_text(encoding="utf-8"))
    return {
        "preflight": "passed",
        "seed": SEED,
        "common_initial_programs": len(seeds),
        "common_initial_programs_sha256": hashlib.sha256(
            "\n".join(bias.program.to_json() for bias in seeds).encode("utf-8")
        ).hexdigest(),
        "v32_protocol_sha256": protocol["protocol_sha256"],
        "g0_language_sha256": G0_LANGUAGE.sha256,
        "g_pilot_manifest_sha256": _sha256(ROOT / "results/v4/languages/g_pilot_e1.json"),
        "g_pilot_language_sha256": language.sha256,
        "g_pilot_macro_names": sorted(language.macro_map),
        "g_pilot_selection_status": pilot_manifest["status"],
        "grammar_g0": grammar_g0,
        "grammar_g_pilot": grammar_pilot,
        "dataset_source": data_manifest["source"],
        "dataset_split": data_manifest["split"],
        "dataset_manifest_sha256": _sha256(data_manifest_path),
        "dataset_fingerprint": dataset.fingerprint,
        "dataset_shape": {
            "train_images": list(search_data.train_images.shape),
            "train_labels": list(search_data.train_labels.shape),
            "validation_images": list(search_data.validation_images.shape),
            "validation_labels": list(search_data.validation_labels.shape),
        },
        "official_test_access": "not used; E1 loader reads only the two pinned train IDX files",
        "model": model,
        "resource_caps": {
            "adaptive_attempts_per_condition": DEFAULT_E1_RESOURCE_CAPS.max_attempts,
            "model_requests_per_condition": DEFAULT_E1_RESOURCE_CAPS.max_requests,
            "request_timeout_seconds": DEFAULT_E1_RESOURCE_CAPS.request_timeout_seconds,
            "output_tokens_per_request": DEFAULT_E1_RESOURCE_CAPS.max_output_tokens,
            "reserved_total_tokens_per_condition": DEFAULT_E1_RESOURCE_CAPS.max_total_tokens,
            "aggregate_reserved_tokens_max": 2 * DEFAULT_E1_RESOURCE_CAPS.max_total_tokens,
        },
        "outputs_are_fresh": True,
    }


def _score_common_initial_programs(
    seeds: tuple,
    search_data,
) -> tuple[CandidateEvaluation, ...]:
    compiler = ProgramCompiler(_CONSTRAINTS)
    evaluator = ProgramEvaluator(
        evaluator=Evaluator(search_data=search_data),
        compiler=compiler,
        train_sizes=(500,),
    )
    oracle = SearchOracle(evaluator=evaluator, constraints=_CONSTRAINTS)
    rows: list[CandidateEvaluation] = []
    for index, bias in enumerate(seeds, start=1):
        compiler.compile(bias.program)
        rows.append(
            oracle.evaluate(
                bias.program,
                evaluation_index=index,
                previously_evaluated=tuple(item.program for item in seeds[: index - 1]),
                metadata={
                    "name": bias.name,
                    "hypothesis": bias.hypothesis,
                    "mechanism": bias.mechanism,
                    "seed_candidate": True,
                },
            )
        )
    if len(rows) != 20 or len({row.candidate_id for row in rows}) != 20:
        raise ValueError("E1 common initial evaluation did not produce 20 unique scores")
    return tuple(rows)


def _run_pair_with_shared_scores(initial_rows, run_condition):
    """Pass the exact same initial score tuple to both isolated conditions."""
    return (
        run_condition("g0", initial_rows),
        run_condition("g_pilot", initial_rows),
    )


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def _seed_proposals(
    seeds: tuple,
    optimizer_name: str = "llm_iterative",
    *,
    seed: int = SEED,
) -> tuple[CandidateProposal, ...]:
    base = common_seed_proposals(seeds, seed)
    return tuple(
        CandidateProposal(
            program=item.program,
            proposal_id=item.proposal_id,
            optimizer=optimizer_name,
            optimizer_seed=item.optimizer_seed,
            generation=item.generation,
            parent_ids=item.parent_ids,
            mechanism_metadata=item.mechanism_metadata,
            proposal_attempt=item.proposal_attempt,
        )
        for item in base
    )


def _run_condition(
    condition: str,
    seeds: tuple,
    initial_rows: tuple[CandidateEvaluation, ...],
    search_data,
    language: MacroLanguage | None,
    output_dir: Path,
    *,
    seed: int = SEED,
    prompt_guidance: str | None = None,
    metrics_filename: str = "e1_metrics.json",
    checkpoint_progress: bool = False,
) -> SearchTrace:
    if condition not in {"g0", "g_pilot"}:
        raise ValueError("condition must be g0 or g_pilot")
    budget = SearchBudget(
        total_evaluations=40,
        seed_evaluations=20,
        max_proposal_attempts=DEFAULT_E1_RESOURCE_CAPS.max_attempts,
    )
    output_dir.mkdir(parents=True, exist_ok=False)
    constraints = _CONSTRAINTS
    compiler = ProgramCompiler(constraints)
    evaluator = ProgramEvaluator(
        evaluator=Evaluator(search_data=search_data),
        compiler=compiler,
        train_sizes=(500,),
    )
    oracle = SearchOracle(evaluator=evaluator, constraints=constraints)
    response_path = output_dir / "llm_responses.jsonl"
    ledger = E1TokenLedger()
    local_client = OllamaLLMClient.from_environment()
    client = E1BudgetedClient(
        local_client,
        ledger,
        output_dir / "model_calls.jsonl",
        seed=seed,
    )
    optimizer = E1IterativeOptimizer(
        seed,
        constraints,
        response_path,
        client=client,
        language=language,
        prompt_guidance=prompt_guidance,
    )
    optimizer_name = "llm_iterative"
    seed_proposals = _seed_proposals(seeds, optimizer_name, seed=seed)
    optimizer.on_seed_evaluations(seed_proposals, initial_rows)

    total_started = time.perf_counter()
    evaluated = list(initial_rows)
    seen_ids = {row.candidate_id for row in initial_rows}
    attempts = valid = invalid = duplicates = constrained = calls = tokens = 0
    proposal_ms = 0.0
    candidate_curve = [{"evaluated_candidates": 20, "best_fitness": max(row.fitness for row in evaluated)}]
    attempt_curve: list[dict[str, object]] = []
    termination_reason: str | None = None
    generation = 1

    def current_trace(*, complete: bool, reason: str | None) -> SearchTrace:
        return SearchTrace(
            optimizer=optimizer_name,
            optimizer_seed=seed,
            evaluated_candidates=tuple(evaluated),
            proposal_attempts=attempts,
            valid_proposal_count=valid,
            invalid_count=invalid,
            duplicate_count=duplicates,
            rejected_by_constraint_count=constrained,
            llm_calls=calls,
            llm_tokens=tokens,
            proposal_time_ms=proposal_ms,
            evaluation_time_ms=oracle.evaluation_time_ms,
            total_wall_time_ms=(time.perf_counter() - total_started) * 1_000,
            complete=complete,
            termination_reason=reason,
            budget_total_evaluations=budget.total_evaluations,
            budget_seed_evaluations=budget.seed_evaluations,
            budget_max_proposal_attempts=budget.max_proposal_attempts,
        )

    def metrics_payload(status: str, reason: str | None) -> dict[str, object]:
        return {
            "condition": condition,
            "seed": seed,
            "status": status,
            "candidate_best_so_far": candidate_curve,
            "attempt_best_so_far": attempt_curve,
            "attempts": attempts,
            "valid_proposals": valid,
            "invalid_proposals": invalid,
            "duplicates": duplicates,
            "constraint_rejections": constrained,
            "evaluated_adaptive_candidates": len(evaluated) - 20,
            "g_pilot_macros_used": sorted(
                {
                    name
                    for row in evaluated[20:]
                    for name in (row.metadata or {}).get("g_pilot_macros_used", [])
                }
            ),
            "token_budget": ledger.to_dict(),
            "termination_reason": reason,
        }

    def save_progress() -> None:
        if checkpoint_progress:
            write_trace(
                current_trace(complete=False, reason="in_progress"),
                output_dir / "trace.json",
            )
            _write_json(
                output_dir / metrics_filename,
                metrics_payload("in_progress", "in_progress"),
            )

    save_progress()
    while len(evaluated) < budget.total_evaluations:
        if attempts >= budget.max_proposal_attempts:
            termination_reason = "adaptive_attempt_cap_reached"
            break
        if ledger.requests >= DEFAULT_E1_RESOURCE_CAPS.max_requests:
            termination_reason = "model_request_cap_reached"
            break
        generation_target = min(18, budget.total_evaluations - len(evaluated))
        generation_start = len(evaluated)
        while len(evaluated) - generation_start < generation_target:
            remaining = budget.max_proposal_attempts - attempts
            if remaining <= 0:
                termination_reason = "adaptive_attempt_cap_reached"
                break
            context = OptimizationContext(
                optimizer=optimizer_name,
                optimizer_seed=seed,
                generation=generation,
                proposal_attempt_start=attempts + 1,
                remaining_attempts=remaining,
                batch_size=min(4, generation_target - (len(evaluated) - generation_start)),
                constraints=constraints,
                seed_programs=tuple(seed.program for seed in seeds),
                evaluated=tuple(evaluated),
            )
            batch_start = attempts
            started = time.perf_counter()
            try:
                batch = optimizer.propose(context)
            except E1BudgetExceeded as exc:
                termination_reason = str(exc).replace("E1 ", "").replace(" ", "_")
                break
            except E1TokenAccountingError:
                termination_reason = "token_accounting_failure"
                break
            proposal_ms += (time.perf_counter() - started) * 1_000
            if batch.attempts > remaining:
                termination_reason = "proposal_attempt_cap_would_be_exceeded"
                break
            attempts += batch.attempts
            valid += batch.valid_proposal_count
            invalid += batch.invalid_count
            duplicates += batch.duplicate_count
            constrained += batch.rejected_by_constraint_count
            calls += batch.llm_calls
            tokens += batch.llm_tokens
            best_before_batch = max(row.fitness for row in evaluated)
            best_by_attempt = [best_before_batch] * batch.attempts
            for proposal in batch.proposals:
                rejection, candidate_id = _e1_candidate_eligibility(
                    proposal.program, compiler, seen_ids
                )
                if rejection == "constraint":
                    constrained += 1
                    continue
                if rejection == "duplicate":
                    duplicates += 1
                    continue
                if candidate_id is None:
                    raise RuntimeError("eligible E1 candidate has no canonical identity")
                metadata = {
                    **(proposal.mechanism_metadata or {}),
                    "generation": generation,
                    "parent_ids": list(proposal.parent_ids),
                    "proposal_id": proposal.proposal_id,
                    "proposal_attempt": proposal.proposal_attempt,
                    "condition": condition,
                }
                row = oracle.evaluate(
                    proposal.program,
                    evaluation_index=len(evaluated) + 1,
                    previously_evaluated=tuple(
                        item.program for item in evaluated if item.program is not None
                    ),
                    metadata=metadata,
                )
                evaluated.append(row)
                seen_ids.add(candidate_id)
                optimizer.on_evaluation(proposal, row)
                candidate_curve.append(
                    {
                        "evaluated_candidates": len(evaluated),
                        "best_fitness": max(item.fitness for item in evaluated),
                    }
                )
                save_progress()
                offset = proposal.proposal_attempt - (batch_start + 1)
                if 0 <= offset < len(best_by_attempt):
                    best_by_attempt[offset] = max(
                        best_by_attempt[offset], row.fitness
                    )
            running_best = best_before_batch
            for index, value in enumerate(best_by_attempt):
                running_best = max(running_best, value)
                attempt_curve.append(
                    {
                        "attempt": batch_start + index + 1,
                        "best_fitness": running_best,
                    }
                )
            save_progress()
            if ledger.accounting_error is not None:
                termination_reason = "token_accounting_failure"
                break
            if batch.attempts == 0:
                termination_reason = "optimizer_returned_no_attempts"
                break
            if len(evaluated) - generation_start >= generation_target:
                break
        optimizer.finish_generation()
        if termination_reason is not None:
            break
        if len(evaluated) - generation_start < generation_target:
            termination_reason = "generation_stopped_before_target"
            break
        generation += 1
    if termination_reason is None:
        termination_reason = (
            "candidate_budget_reached" if len(evaluated) >= 40 else "adaptive_attempt_cap_reached"
        )
    trace = current_trace(complete=True, reason=termination_reason)
    write_trace(trace, output_dir / "trace.json")
    _write_json(
        output_dir / metrics_filename,
        metrics_payload("completed", termination_reason),
    )
    return trace


def run_e1(
    *,
    data_config: E1MNISTDataConfig = DATA_CONFIG,
    output_root: Path = OUTPUT_ROOT,
) -> dict[str, object]:
    """Execute both bounded conditions; E1-PREP must not call this function."""
    preflight = run_preflight(data_config=data_config, output_root=output_root)
    protocol, seeds = _verified_protocol_and_seeds()
    language, pilot_manifest = load_e1_pilot_language(ROOT)
    search_data = load_mnist_e1_search_data(data_config)
    initial_rows = _score_common_initial_programs(seeds, search_data)
    output_root = Path(output_root)
    output_root.mkdir(parents=True, exist_ok=False)
    common_path = output_root / "common_initial_evaluations.json"
    _write_json(
        common_path,
        {
            "schema_version": 1,
            "seed": SEED,
            "programs": [bias.program.to_dict() for bias in seeds],
            "scores": [row.to_dict() for row in initial_rows],
            "sha256": hashlib.sha256(
                json.dumps([row.to_dict() for row in initial_rows], sort_keys=True, separators=(",", ":")).encode()
            ).hexdigest(),
        },
    )
    gp0, gp = _run_pair_with_shared_scores(
        initial_rows,
        lambda condition, rows: _run_condition(
            condition,
            seeds,
            rows,
            search_data,
            language if condition == "g_pilot" else None,
            output_root / condition,
        ),
    )
    summary = {
        "schema_version": 1,
        "status": "completed_exploratory_e1",
        "seed": SEED,
        "v32_protocol_sha256": protocol["protocol_sha256"],
        "g_pilot_manifest_sha256": preflight["g_pilot_manifest_sha256"],
        "g_pilot_language_sha256": language.sha256,
        "g_pilot_official_star": pilot_manifest["official_G_star"],
        "common_initial_scores_sha256": _sha256(common_path),
        "conditions": {
            "g0": {"attempts": gp0.proposal_attempts, "evaluations": len(gp0.evaluated_candidates)},
            "g_pilot": {"attempts": gp.proposal_attempts, "evaluations": len(gp.evaluated_candidates)},
        },
        "resource_caps": preflight["resource_caps"],
    }
    _write_json(output_root / "e1_summary.json", summary)
    return summary


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--preflight", action="store_true")
    mode.add_argument("--run", action="store_true")
    parser.add_argument("--data-dir", type=Path, default=DATA_CONFIG.cache_dir)
    parser.add_argument("--output-root", type=Path, default=OUTPUT_ROOT)
    arguments = parser.parse_args(argv)
    config = E1MNISTDataConfig(cache_dir=arguments.data_dir)
    if arguments.preflight:
        print(json.dumps(run_preflight(data_config=config, output_root=arguments.output_root), indent=2, sort_keys=True))
        return 0
    print(json.dumps(run_e1(data_config=config, output_root=arguments.output_root), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
