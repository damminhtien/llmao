"""Run one seed of the preregistered V4 primary language discovery study."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import traceback
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
EVE_ROOT = ROOT.parent / "eve"
sys.path.insert(0, str(EVE_ROOT / "src"))
sys.path.insert(0, str(ROOT / "experiments"))

if __package__:
    from .v4_primary_contract import validate_contract
else:
    from v4_primary_contract import validate_contract

MAX_ATTEMPTS = 540
UNIQUE_TARGET = 200
TOKEN_CAP = 500_000_000
SEED_COUNT = 20
SOURCE_PROGRAMS = ROOT / "V4_INITIAL_PROGRAMS.json"
G0_LANGUAGE = ROOT / "configs/v4/phase12_primary/task/candidate/language.json"
TASK_ROOT = ROOT / "configs/v4/phase12_primary/task"
PROMPT_ROOT = ROOT / "configs/v4/phase12_primary/prompt"
GUIDANCE_ROOT = ROOT / "configs/v4/phase12_primary/initial_guidance"
ADAPTER = ROOT / "configs/v4/phase12_primary/evaluate.py"
EVALUATION_STEP = ROOT / "configs/v4/phase12_primary/evaluation.sh"
CONTEXT_BUILDER = ROOT / "experiments/v4_build_primary_context.py"
PRIMARY_EVALUATOR = ROOT / "experiments/v4_evaluate_primary_candidate.py"


def _digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _json_bytes(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n").encode()


def _write_atomic(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_bytes(payload)
    temporary.replace(path)


def _state_json_value(value: Any) -> Any:
    if isinstance(value, tuple):
        return [_state_json_value(item) for item in value]
    if isinstance(value, list):
        return [_state_json_value(item) for item in value]
    return value


def _state_tuple(value: Any) -> Any:
    if isinstance(value, list):
        return tuple(_state_tuple(item) for item in value)
    return value


def _json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _run(command: list[str], *, cwd: Path, timeout: int = 120) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )


def _compose_config(*, run_root: Path, seed: int, checker_bundle: Path, run_id: str):
    from hydra import compose, initialize_config_dir
    from omegaconf import OmegaConf

    overrides = [
        "application=llmao_v4_language_pilot",
        "optimizer=llmao_v4_language_pilot",
        "evaluation=llmao_v4_language_pilot",
    ]
    with initialize_config_dir(
        version_base="1.3",
        config_dir=str(EVE_ROOT / "configs/eve"),
    ):
        config = compose(config_name="llmao_v4", overrides=overrides)
    updates = {
        "run_id": run_id,
        "run_root": str(run_root),
        "label": f"v4-primary-discovery-{seed}",
        "application.name": f"llmao-v4-primary-discovery-{seed}",
        "application.path": str(TASK_ROOT),
        "application.editable.files": ["candidate/language.json", "candidate/program.json"],
        "application.editable.folders": [],
        "optimizer.initial_guidance": str(GUIDANCE_ROOT),
        "optimizer.workers.items.0.name": "v4-primary-discovery",
        "optimizer.workers.items.0.immutable": str(checker_bundle.parent),
        "optimizer.workers.items.0.prompt": str(PROMPT_ROOT),
        "evaluation.steps": [str(EVALUATION_STEP)],
        "evaluation.failure_score": {
            "score": 0.0,
            "summary": "primary discovery evaluation failed",
        },
        "evaluation.seed_solver_score": None,
        "evaluation.seed_solver_skip_evaluation": False,
        "evaluation.include_solver_examples": True,
        "driver.executable": str(ROOT / "scripts/codex-v4-sandbox"),
        "driver.model": "gpt-6-luna",
        "driver.reasoning_effort": "max",
        "driver.system_prompt_file": str(ROOT / "configs/v4/phase12_primary_worker.md"),
        "driver.rollout_max_turns": 80,
        "driver.timeout_seconds": 3600,
        "driver.budget_prompt": True,
        "driver.approval_policy": "never",
        "driver.sandbox_mode": "workspace-write",
        "driver.allow_network": False,
        "driver.web_search": "disabled",
        "driver.enable_multi_agent": False,
        "driver.open_iterm2": False,
        "loop.max_iterations": MAX_ATTEMPTS,
        "loop.n_workers_phase2": 1,
        "loop.n_parallel_phase2": 1,
        "loop.n_solver_examples_phase2": 32,
        "loop.n_optimizer_examples_phase2": 1,
        "loop.produce_optimizer_in_phase2": 1,
        "loop.boundary_repair_attempts": 0,
        "loop.enable_resume": True,
        "loop.workspace_root": str(run_root),
        "loop.artifact_root": str(run_root / "artifacts"),
        "loop.solver_db_path": str(run_root / "solver_lineage.db"),
        "loop.optimizer_db_path": str(run_root / "optimizer_lineage.db"),
        "logger.csv.enabled": True,
        "logger.wandb.enabled": False,
    }
    for key, value in updates.items():
        OmegaConf.update(config, key, value, merge=True, force_add=True)
    return config


def _configure_evaluator_environment(contract: dict[str, Any]) -> None:
    protocol_path = Path(contract["protocol_path"]).resolve(strict=True)
    data_dir = Path(contract["verified_data_dir"])
    env = {
        "LLMAO_EXPECTED_COMMIT": contract["llmao_commit"],
        "LLMAO_PROJECT_ROOT": str(ROOT),
        "LLMAO_PYTHON": contract["runtime"]["llmao_python"],
        "LLMAO_PHASE12_ADAPTER_PYTHON": contract["runtime"]["eve_python"],
        "LLMAO_PHASE12_ADAPTER": str(ADAPTER),
        "LLMAO_PHASE12_CONTEXT_BUILDER": str(CONTEXT_BUILDER),
        "LLMAO_PHASE12_EVALUATOR": str(PRIMARY_EVALUATOR),
        "LLMAO_PHASE12_PROTOCOL": str(protocol_path),
        "LLMAO_PHASE12_PROTOCOL_SHA256": contract["protocol_sha256"],
        "LLMAO_DATA_DIR": str(data_dir),
    }
    os.environ.update(env)


def _initial_entries(
    *,
    run_root: Path,
    contract: dict[str, Any],
) -> list[Any]:
    from scaling_evolve.algorithms.eve.populations.entry import PopulationEntry

    manifest = _json(SOURCE_PROGRAMS)
    if manifest.get("program_count") != SEED_COUNT or len(manifest.get("programs", [])) != SEED_COUNT:
        raise ValueError("common initial-program manifest must contain exactly twenty programs")
    language_text = G0_LANGUAGE.read_text(encoding="utf-8")
    expected_g0_hash = contract["verified_protocol"]["language_conditions"]["G0"][
        "manifest_sha256"
    ]
    if manifest["language_sha256"]["G0"] != expected_g0_hash:
        raise ValueError("common initial programs do not use the protocol G0 language")
    entries: list[PopulationEntry] = []
    input_root = run_root / "initial_inputs"
    for index, record in enumerate(manifest["programs"]):
        candidate_dir = input_root / f"seed_{index:02d}" / "candidate"
        candidate_dir.mkdir(parents=True, exist_ok=True)
        (candidate_dir / "language.json").write_text(language_text, encoding="utf-8")
        (candidate_dir / "program.json").write_text(
            json.dumps(record["program"], indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        context_path = candidate_dir.parent / "context.json"
        state_path = candidate_dir.parent / "lineage_state.json"
        context_result = _run(
            [
                contract["runtime"]["llmao_python"],
                str(CONTEXT_BUILDER),
                str(candidate_dir),
                str(context_path),
                "--protocol",
                str(contract["protocol_path"]),
                "--generation",
                "0",
                "--lineage-state-output",
                str(state_path),
            ],
            cwd=run_root,
        )
        if context_result.returncode:
            raise RuntimeError(f"initial candidate {index} context failed: {context_result.stderr}")
        artifact_path = candidate_dir.parent / "evaluator.json"
        evaluator_log = candidate_dir.parent / "evaluator.log"
        evaluation_result = _run(
            [
                contract["runtime"]["llmao_python"],
                str(PRIMARY_EVALUATOR),
                str(candidate_dir),
                "--context",
                str(context_path),
                "--protocol",
                str(contract["protocol_path"]),
                "--protocol-sha256",
                contract["protocol_sha256"],
                "--data-dir",
                os.environ["LLMAO_DATA_DIR"],
                "--output",
                str(artifact_path),
                "--log",
                str(evaluator_log),
            ],
            cwd=run_root,
            timeout=1_800,
        )
        if evaluation_result.returncode:
            raise RuntimeError(
                f"initial candidate {index} evaluator failed: {evaluation_result.stderr}"
            )
        artifact = _json(artifact_path)
        if artifact.get("status") != "discovery_scored" or artifact.get("discovery_ready") is not True:
            raise RuntimeError(f"initial candidate {index} did not receive a discovery score")
        score = float(artifact["discovery_fitness"])
        score_payload = {
            "score": score,
            "summary": "common G0 seed; zero invented-macro penalty",
            "status": "discovery_scored",
            "discovery_ready": True,
            "score_source": "discovery_fitness",
            "seed_index": index,
            "candidate_id": artifact["candidate"]["candidate_id"],
            "expanded_program_sha256": artifact["candidate"]["expanded_program_sha256"],
            "stage_one_fitness": artifact["evaluation"]["stage_one_fitness"],
            "discovery_fitness": score,
            "protocol_sha256": contract["protocol_sha256"],
        }
        lineage_state = _json(state_path)
        record_payload = {
            "kind": "common_initial_program",
            "seed_index": index,
            "program_manifest_sha256": contract["initial_programs_sha256"],
            "ast_sha256": record["ast_sha256"],
            "expanded_program_sha256": artifact["candidate"]["expanded_program_sha256"],
            "candidate_id": artifact["candidate"]["candidate_id"],
            "evaluation_seed": 42,
            "input_tokens": 0,
            "output_tokens": 0,
            "cached_input_tokens": 0,
        }
        logs = {
            "evaluate/context.json": context_path.read_text(encoding="utf-8"),
            "evaluate/lineage_state.json": state_path.read_text(encoding="utf-8"),
            "evaluate/parent_language_lineage.json": "[]\n",
            "evaluate/lineage_parent.json": _json_bytes(
                {"eve_prefill_id": None, "parent_candidate_id": None, "generation": 0}
            ).decode(),
            "evaluate/evaluator.json": artifact_path.read_text(encoding="utf-8"),
            "evaluate/evaluator.log": evaluator_log.read_text(encoding="utf-8"),
            "evaluate/score.yaml": json.dumps(score_payload, indent=2, sort_keys=True) + "\n",
            "evaluate/token_usage.json": _json_bytes(
                {
                    "total": {
                        "input_tokens": 0,
                        "output_tokens": 0,
                        "cache_read_tokens": 0,
                        "cache_creation_tokens": 0,
                        "agent_turns": 0,
                    },
                    "attempts": [],
                }
            ).decode(),
            "evaluate/primary_record.json": _json_bytes(record_payload).decode(),
        }
        if lineage_state.get("generation") != 0 or lineage_state.get("language_hash") != artifact[
            "candidate"
        ]["language_sha256"]:
            raise ValueError(f"initial candidate {index} lineage does not match its score")
        entries.append(
            PopulationEntry(
                id=f"seed_{contract['seed']}_{index:02d}",
                files={
                    "candidate/language.json": language_text,
                    "candidate/program.json": (candidate_dir / "program.json").read_text(),
                },
                score={"score": score},
                logs=logs,
            )
        )
    unique = {
        _json_value(entry.logs["evaluate/primary_record.json"])["expanded_program_sha256"]
        for entry in entries
    }
    if len(unique) != SEED_COUNT:
        raise ValueError("the twenty common initial programs are not unique expanded ASTs")
    return entries


def _json_value(value: str) -> Any:
    return json.loads(value)


def _rollout_usage(result: Any) -> dict[str, int | float]:
    totals: dict[str, int | float] = {
        "input_tokens": 0,
        "output_tokens": 0,
        "cached_input_tokens": 0,
        "cache_creation_tokens": 0,
        "native_turns": 0,
        "wallclock_seconds": 0.0,
    }
    for rollout in result.rollouts:
        usage = getattr(rollout, "usage", None)
        if usage is None:
            continue
        totals["input_tokens"] += int(getattr(usage, "input_tokens", 0) or 0)
        totals["output_tokens"] += int(getattr(usage, "output_tokens", 0) or 0)
        totals["cached_input_tokens"] += int(getattr(usage, "cache_read_tokens", 0) or 0)
        totals["cache_creation_tokens"] += int(
            getattr(usage, "cache_creation_tokens", 0) or 0
        )
        totals["native_turns"] += int(getattr(usage, "agent_turns", 0) or 0)
        totals["wallclock_seconds"] += float(getattr(usage, "wallclock_seconds", 0.0) or 0.0)
    return totals


def _entry_eval(entry: Any) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    raw_artifact = entry.logs.get("evaluate/evaluator.json")
    raw_record = entry.logs.get("evaluate/primary_record.json")
    artifact = json.loads(raw_artifact) if raw_artifact else None
    record = json.loads(raw_record) if raw_record else None
    return artifact, record


def _population_counts(entries: list[Any]) -> tuple[int, int, set[str]]:
    seen: set[str] = set()
    successful = 0
    for entry in entries:
        artifact, _ = _entry_eval(entry)
        if not artifact or artifact.get("status") != "discovery_scored":
            continue
        candidate = artifact.get("candidate") or {}
        expanded_hash = candidate.get("expanded_program_sha256")
        if not isinstance(expanded_hash, str):
            continue
        successful += 1
        seen.add(expanded_hash)
    return successful, len(seen), seen


def _expanded_hashes(entries: list[Any], *, exclude_id: str | None = None) -> set[str]:
    hashes: set[str] = set()
    for entry in entries:
        if entry.id == exclude_id:
            continue
        artifact, _ = _entry_eval(entry)
        if not artifact or artifact.get("status") != "discovery_scored":
            continue
        expanded_hash = (artifact.get("candidate") or {}).get(
            "expanded_program_sha256"
        )
        if isinstance(expanded_hash, str):
            hashes.add(expanded_hash)
    return hashes


def _entry_token_usage(entry: Any) -> dict[str, int]:
    totals = {"input_tokens": 0, "output_tokens": 0, "cached_input_tokens": 0}
    raw = entry.logs.get("optimize/token_usage.json")
    if not raw:
        return totals
    payload = json.loads(raw)
    reported = payload.get("total", {})
    totals["input_tokens"] = int(reported.get("input_tokens", 0) or 0)
    totals["output_tokens"] = int(reported.get("output_tokens", 0) or 0)
    totals["cached_input_tokens"] = int(reported.get("cache_read_tokens", 0) or 0)
    return totals


def _entry_json_log(entry: Any, path: str) -> Any:
    raw = entry.logs.get(path)
    if not raw:
        return None
    return json.loads(raw)


def _verify_protocol_matches_runner(protocol: dict[str, Any], seed: int) -> None:
    discovery = protocol["primary_discovery"]
    candidate_budget = discovery["candidate_budget"]
    token_budget = discovery["token_budget"]
    runtime = discovery["runtime_limits"]
    design = protocol["primary_design"]
    expected = (
        seed in discovery["discovery_seeds"],
        candidate_budget["unique_successful_expanded_asts"] == UNIQUE_TARGET,
        candidate_budget["common_initial_ast_count"] == SEED_COUNT,
        candidate_budget["adaptive_unique_evaluations"] == UNIQUE_TARGET - SEED_COUNT,
        candidate_budget["adaptive_proposal_attempt_cap"] == MAX_ATTEMPTS,
        candidate_budget["exact_expanded_ast_repeats_advance_unique_budget"] is False,
        candidate_budget["count_invalid_repeat_timeout_and_failure_as_attempt"] is True,
        candidate_budget["no_replacement_proposals"] is True,
        token_budget["reported_input_plus_output_tokens"] == TOKEN_CAP,
        token_budget["cached_input_counted_once"] is True,
        token_budget["seed_evaluations_model_tokens"] == 0,
        runtime["native_turns_per_proposal"] == 80,
        runtime["proposal_timeout_seconds"] == 3_600,
        runtime["boundary_repair_attempts"] == 0,
        runtime["evaluator_timeout_seconds"] == 1_800,
        runtime["workers"] == 1,
        runtime["parallel_workers"] == 1,
        runtime["read_only_solver_examples"] == 32,
        design["exact_cli_model_identifier"] == "gpt-6-luna",
        design["requested_reasoning_effort"] == "max",
        design["backend"] == "codex_tmux",
        design["official_test_access"] is False,
        discovery["official_test_access"] is False,
        protocol["primary_discovery"]["discovery_objective"]["penalty_coefficient"]
        == 0.0005,
    )
    if not all(expected):
        raise ValueError("finalized protocol settings differ from the Phase 12 runner")


def _write_jsonl(path: Path, value: dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(value, sort_keys=True, allow_nan=False) + "\n")


def _rng_state(factory: Any) -> dict[str, Any]:
    return {
        "optimizer_population": _state_json_value(factory.loop.optimizer_pop._rng.getstate()),
        "solver_population": _state_json_value(factory.loop.solver_pop._rng.getstate()),
        "workspace_builder": _state_json_value(
            factory.loop.solver_workspace_builder._rng.getstate()
        ),
    }


def _restore_rng(factory: Any, state: dict[str, Any]) -> None:
    fields = {
        "optimizer_population": factory.loop.optimizer_pop._rng,
        "solver_population": factory.loop.solver_pop._rng,
        "workspace_builder": factory.loop.solver_workspace_builder._rng,
    }
    if set(state) != set(fields):
        raise ValueError("primary resume state has an invalid RNG set")
    for name, generator in fields.items():
        generator.setstate(_state_tuple(state[name]))


def _write_iteration_snapshot(
    *,
    run_root: Path,
    step: int,
    seed: int,
    contract: dict[str, Any],
    attempts: int,
    token_total: int,
    rng_state: dict[str, Any],
    status: str,
) -> dict[str, Any]:
    state = {
        "schema_version": 1,
        "seed": seed,
        "contract_sha256": contract["verified_contract_sha256"],
        "protocol_sha256": contract["protocol_sha256"],
        "completed_iterations": step,
        "adaptive_attempts": attempts,
        "reported_input_plus_output_tokens": token_total,
        "rng_state": rng_state,
        "status": status,
        "updated_at_utc": datetime.now(UTC).isoformat(),
    }
    path = run_root / "state_snapshots" / f"iteration_{step:04d}.json"
    _write_atomic(path, _json_bytes(state))
    _write_atomic(run_root / "run_state.json", _json_bytes(state))
    return state


def _pending_workspaces(run_root: Path, *, completed_step: int) -> list[Path]:
    result: list[Path] = []
    workspace_root = run_root / "solver_workspaces"
    if not workspace_root.is_dir():
        return result
    for path in sorted(workspace_root.iterdir()):
        if not path.is_dir() or "_step_" not in path.name:
            continue
        marker = path.name.split("_step_", 1)[1].split("_", 1)[0]
        if marker.isdigit() and int(marker) > completed_step:
            result.append(path)
    return result


def _interrupted_usage(workspace: Path) -> dict[str, int]:
    from scaling_evolve.providers.agent.codex_isolation import extract_usage

    totals = {
        "input_tokens": 0,
        "output_tokens": 0,
        "cached_input_tokens": 0,
        "native_turns": 0,
    }
    transcript_root = workspace / ".codex-driver-transcripts"
    for path in sorted(transcript_root.glob("*.jsonl")) if transcript_root.is_dir() else []:
        report = extract_usage(path, from_line=0)
        totals["input_tokens"] += int(report.get("input_tokens", 0))
        totals["output_tokens"] += int(report.get("output_tokens", 0))
        totals["cached_input_tokens"] += int(report.get("cached_input_tokens", 0))
        totals["native_turns"] += int(report.get("agent_turns", 0))
    return totals


def _export_population(run_root: Path, factory: Any) -> None:
    solver_path = run_root / "solver_population.jsonl"
    optimizer_path = run_root / "optimizer_population.jsonl"
    solver_path.write_text("", encoding="utf-8")
    optimizer_path.write_text("", encoding="utf-8")
    for entry in factory.loop.solver_pop.entries():
        artifact, record = _entry_eval(entry)
        payload = {
            "id": entry.id,
            "files": entry.files,
            "score": entry.score,
            "candidate": (artifact or {}).get("candidate"),
            "evaluation": (artifact or {}).get("evaluation"),
            "evaluation_context": _entry_json_log(entry, "evaluate/context.json"),
            "parent_language_lineage": _entry_json_log(
                entry, "evaluate/parent_language_lineage.json"
            ),
            "lineage_parent": _entry_json_log(entry, "evaluate/lineage_parent.json"),
            "lineage_state": _entry_json_log(entry, "evaluate/lineage_state.json"),
            "primary_record": record,
            "evaluation_status": (artifact or {}).get("status"),
            "score_record": _entry_json_log(entry, "evaluate/score.yaml"),
            "evaluator_artifact": artifact,
            "token_usage": _entry_json_log(entry, "optimize/token_usage.json"),
            "optimizer_token_usage": _entry_token_usage(entry),
        }
        _write_jsonl(solver_path, payload)
    for entry in factory.loop.optimizer_pop.entries():
        files_hash = hashlib.sha256()
        for relative, content in sorted(entry.files.items()):
            files_hash.update(relative.encode())
            files_hash.update(b"\0")
            files_hash.update(content.encode())
            files_hash.update(b"\0")
        payload = {
            "id": entry.id,
            "guidance_sha256": files_hash.hexdigest(),
            "files": entry.files,
            "score": entry.score,
            "log_paths": sorted(entry.logs),
        }
        _write_jsonl(optimizer_path, payload)


def _build_final_manifest(
    *,
    run_root: Path,
    contract: dict[str, Any],
    seed: int,
    state: dict[str, Any],
    factory: Any,
    run_status: str,
) -> dict[str, Any]:
    _export_population(run_root, factory)
    solver_entries = factory.loop.solver_pop.entries()
    successful, unique, hashes = _population_counts(solver_entries)
    best = max(
        (
            float(entry.score["score"])
            for entry in solver_entries
            if entry.score.get("score") is not None
        ),
        default=None,
    )
    token_total = int(state["reported_input_plus_output_tokens"])
    records: list[dict[str, Any]] = []
    for path in sorted(run_root.rglob("*")):
        if not path.is_file() or path.name in {"run_manifest.json", "run_manifest.json.sha256"}:
            continue
        if path.is_symlink():
            records.append(
                {
                    "path": path.relative_to(run_root).as_posix(),
                    "kind": "symlink",
                    "target": os.readlink(path),
                }
            )
            continue
        records.append(
            {
                "path": path.relative_to(run_root).as_posix(),
                "sha256": _digest(path.read_bytes()),
                "size_bytes": path.stat().st_size,
            }
        )
    manifest = {
        "schema_version": 1,
        "seed": seed,
        "status": run_status,
        "contract_sha256": contract["verified_contract_sha256"],
        "protocol_sha256": contract["protocol_sha256"],
        "llmao_commit": contract["llmao_commit"],
        "eve_commit": contract["eve_commit"],
        "initial_programs_sha256": contract["initial_programs_sha256"],
        "common_seed_count": SEED_COUNT,
        "adaptive_attempts": int(state["adaptive_attempts"]),
        "unique_successful_expanded_asts": unique,
        "successful_candidate_evaluations": successful,
        "unique_expanded_ast_sha256": sorted(hashes),
        "reported_input_plus_output_tokens": token_total,
        "token_cap": TOKEN_CAP,
        "best_discovery_fitness": best,
        "solver_population_entries": len(solver_entries),
        "optimizer_guidance_revisions": factory.loop.optimizer_pop.size(),
        "official_test_access": False,
        "files": records,
    }
    raw = _json_bytes(manifest)
    digest = _digest(raw)
    _write_atomic(run_root / "run_manifest.json", raw)
    _write_atomic(
        run_root / "run_manifest.json.sha256",
        f"{digest}  run_manifest.json\n".encode(),
    )
    return manifest


def _phase2_runner(factory: Any, *, step: int, proposal: int):
    from scaling_evolve.algorithms.eve.workflow.phase2 import Phase2BatchRunner

    loop = factory.loop
    return Phase2BatchRunner(
        solver_workspace_builder=loop.solver_workspace_builder,
        driver=loop.solver_driver,
        solver_evaluator=loop.solver_evaluator,
        step_label=f"step_{step}_attempt_{proposal:04d}",
        iteration=step,
        total_iterations=MAX_ATTEMPTS,
        solver_pop=loop.solver_pop,
        optimizer_pop=loop.optimizer_pop,
        n_workers_phase2=1,
        n_parallel_phase2=1,
        n_solver_examples_phase2=32,
        n_optimizer_examples_phase2=1,
        n_produced_optimizers_phase2=1,
        optimizer_sampler=loop.phase2_optimizer_sampler,
        solver_sampler=loop.phase2_solver_sampler,
        prefill_sampler=loop.phase2_prefill_sampler,
        optimizer_examples_sampler=loop.phase2_optimizer_examples_sampler,
        produced_optimizer_sampler=loop.phase2_produced_optimizer_sampler,
    )


def _run_primary(
    *,
    contract: dict[str, Any],
    seed: int,
    resume: bool,
    validate_only: bool,
) -> int:
    _verify_protocol_matches_runner(contract["verified_protocol"], seed)
    from omegaconf import OmegaConf
    from scaling_evolve.algorithms.eve.factory import EveFactory
    from scaling_evolve.algorithms.eve.problem.repo import RepoTaskProblem
    from scaling_evolve.algorithms.eve.runner import _instantiate_eve_logger_group
    from scaling_evolve.algorithms.eve.runtime.driver import build_role_drivers
    from scaling_evolve.algorithms.eve.runtime.resume import (
        prepare_resume,
        read_checkpoint,
    )
    from scaling_evolve.algorithms.eve.workflow.evaluation import (
        build_evaluation_plan,
        build_solver_evaluator,
    )
    from scaling_evolve.algorithms.eve.workflow.phase3 import score_optimizers

    run_root = Path(contract["verified_run_root"])
    checker_bundle = Path(contract["checker_bundle_path"]).resolve(strict=True)
    run_id = f"v4_primary_discovery_{seed}_{contract['protocol_sha256'][:10]}"
    cfg = _compose_config(
        run_root=run_root,
        seed=seed,
        checker_bundle=checker_bundle,
        run_id=run_id,
    )
    if validate_only:
        payload = {
            "valid": True,
            "seed": seed,
            "run_id": run_id,
            "run_root": str(run_root),
            "protocol_sha256": contract["protocol_sha256"],
            "application_path": str(cfg.application.path),
            "evaluation_step": str(cfg.evaluation.steps[0]),
            "checker_bundle": str(checker_bundle),
            "max_iterations": cfg.loop.max_iterations,
            "workers": cfg.loop.n_workers_phase2,
            "parallel_workers": cfg.loop.n_parallel_phase2,
            "boundary_repair_attempts": cfg.loop.boundary_repair_attempts,
        }
        print(json.dumps(payload, sort_keys=True))
        return 0

    if resume:
        checkpoint = read_checkpoint(run_root)
        if checkpoint is None:
            raise ValueError("cannot resume primary discovery without an Eve checkpoint")
        pending = _pending_workspaces(
            run_root,
            completed_step=checkpoint.last_completed_iteration,
        )
        pending_usage = [
            {"workspace": str(path), "tokens": _interrupted_usage(path)} for path in pending
        ]
        resume_plan = prepare_resume(run_root)
        anchor = resume_plan.start_iteration
        state_path = run_root / "state_snapshots" / f"iteration_{anchor:04d}.json"
        if not state_path.is_file():
            raise ValueError("primary resume state snapshot is missing at the Eve checkpoint")
        state = _json(state_path)
        if state.get("contract_sha256") != contract["verified_contract_sha256"]:
            raise ValueError("resume checkpoint belongs to a different launch contract")
    else:
        anchor = 0
        state = None
        pending_usage = []
        run_root.mkdir(parents=True, exist_ok=False)

    _configure_evaluator_environment(contract)
    app_config = OmegaConf.to_container(cfg.application, resolve=True)
    run_config = OmegaConf.create(OmegaConf.to_container(cfg, resolve=True))
    problem = RepoTaskProblem.from_config(
        app_config,
        cache_root=run_root / ".repo_cache",
        search_root=EVE_ROOT,
    )
    run_root.mkdir(parents=True, exist_ok=True)
    drivers = build_role_drivers(
        OmegaConf.to_container(cfg.driver, resolve=True),
        run_root=run_root,
        worker_slots=1,
        pricing_table=None,
    )
    try:
        evaluation_plan = build_evaluation_plan(
            problem,
            evaluation_config=OmegaConf.select(run_config, "evaluation", default=None),
            search_root=EVE_ROOT,
        )
        solver_evaluator = build_solver_evaluator(
            problem,
            evaluation_plan=evaluation_plan,
            evaluation_failure_score=OmegaConf.to_container(
                run_config.evaluation.failure_score, resolve=True
            ),
            boundary_failure_score=OmegaConf.to_container(
                run_config.application.boundary_failure_score, resolve=True
            ),
            seed_solver_score=None,
            seed_solver_skip_evaluation=False,
            include_solver_examples=True,
            evaluation_driver_factory=drivers.eval_driver_factory,
        )
        logger = _instantiate_eve_logger_group(cfg.logger, run_config)
        with EveFactory.from_config(
            run_config,
            solver_evaluator,
            solver_driver=drivers.solver_driver,
            logger=logger,
            task_problem=problem,
            search_root=EVE_ROOT,
        ) as factory:
            rngs = {
                "optimizer_population": (factory.loop.optimizer_pop._rng, seed + 1),
                "solver_population": (factory.loop.solver_pop._rng, seed + 2),
                "workspace_builder": (factory.loop.solver_workspace_builder._rng, seed + 3),
            }
            if resume:
                _restore_rng(factory, state["rng_state"])
                attempts = int(state["adaptive_attempts"])
                token_total = int(state["reported_input_plus_output_tokens"])
                loop_step = anchor
                for pending_item in pending_usage:
                    usage = pending_item["tokens"]
                    increment = int(usage["input_tokens"]) + int(usage["output_tokens"])
                    token_total += increment
                    attempts += 1
                    pending_record = {
                        "kind": "interrupted_proposal",
                        "status": "interrupted_infrastructure",
                        "consumed_attempt": attempts,
                        "workspace": pending_item["workspace"],
                        "token_usage": usage,
                        "reported_input_plus_output_tokens": increment,
                        "recorded_at_utc": datetime.now(UTC).isoformat(),
                    }
                    _write_jsonl(run_root / "trajectory.jsonl", pending_record)
                    _write_jsonl(run_root / "interrupted_attempts.jsonl", pending_record)
                factory.loop._iterations_completed = anchor
            else:
                for generator, rng_seed in rngs.values():
                    generator.seed(rng_seed)
                factory.seed_initial_guidance(search_root=EVE_ROOT)
                entries = _initial_entries(run_root=run_root, contract=contract)
                factory.seed_solver_population(entries)
                attempts = 0
                token_total = 0
                loop_step = 0
                state = _write_iteration_snapshot(
                    run_root=run_root,
                    step=0,
                    seed=seed,
                    contract=contract,
                    attempts=attempts,
                    token_total=token_total,
                    rng_state=_rng_state(factory),
                    status="running",
                )
                _write_jsonl(
                    run_root / "trajectory.jsonl",
                    {
                        "kind": "common_initial_set",
                        "candidate_count": SEED_COUNT,
                        "unique_expanded_asts": SEED_COUNT,
                        "program_manifest_sha256": contract["initial_programs_sha256"],
                        "recorded_at_utc": datetime.now(UTC).isoformat(),
                    },
                )
                factory.loop._persist_iteration_boundary(0)
            if state is None:
                raise RuntimeError("primary run state did not initialize")
            factory.loop._iterations_completed = loop_step
            if resume:
                # The checkpoint snapshot accounts for completed proposals.
                token_total = int(state["reported_input_plus_output_tokens"]) + sum(
                    int(item["tokens"]["input_tokens"])
                    + int(item["tokens"]["output_tokens"])
                    for item in pending_usage
                )

            run_status = "running"
            last_state = state
            for _ in range(loop_step, MAX_ATTEMPTS):
                successful, unique_count, _ = _population_counts(
                    factory.loop.solver_pop.entries()
                )
                if unique_count >= UNIQUE_TARGET:
                    run_status = "complete"
                    break
                if attempts >= MAX_ATTEMPTS:
                    run_status = "incomplete_attempt_cap"
                    break
                if token_total >= TOKEN_CAP:
                    run_status = "incomplete_token_cap"
                    break

                # Attempt IDs include interrupted workspaces archived by EvE.
                step = attempts + 1
                factory.loop._persist_iteration_boundary(step - 1)
                proposal_number = attempts + 1
                results = _phase2_runner(
                    factory,
                    step=step,
                    proposal=proposal_number,
                ).run()
                attempts += 1
                if len(results) != 1:
                    record = {
                        "kind": "adaptive_proposal",
                        "attempt": attempts,
                        "iteration": step,
                        "status": "terminal_infrastructure_failure",
                        "result_count": len(results),
                        "recorded_at_utc": datetime.now(UTC).isoformat(),
                    }
                    _write_jsonl(run_root / "trajectory.jsonl", record)
                    factory.loop._iterations_completed = step
                    last_state = _write_iteration_snapshot(
                        run_root=run_root,
                        step=step,
                        seed=seed,
                        contract=contract,
                        attempts=attempts,
                        token_total=token_total,
                        rng_state=_rng_state(factory),
                        status="incomplete_terminal_infrastructure_failure",
                    )
                    factory.loop._persist_iteration_boundary(step)
                    run_status = "incomplete_terminal_infrastructure_failure"
                    break

                result = results[0]
                score_optimizers(
                    optimizers=[result.optimizer],
                    phase2_results=results,
                    optimizer_pop=factory.loop.optimizer_pop,
                    optimizer_evaluator=factory.loop.optimizer_evaluator,
                )
                usage = _rollout_usage(result)
                increment = int(usage["input_tokens"]) + int(usage["output_tokens"])
                token_total += increment
                produced = result.produced_solver
                artifact, candidate_record = _entry_eval(produced)
                before_hashes = _expanded_hashes(
                    factory.loop.solver_pop.entries(), exclude_id=produced.id
                )
                candidate = (artifact or {}).get("candidate") or {}
                expanded_hash = candidate.get("expanded_program_sha256")
                repeated = isinstance(expanded_hash, str) and expanded_hash in before_hashes
                evaluation_status = (artifact or {}).get("status", "missing_evaluator_artifact")
                boundary_violation = any(
                    "boundary/forbidden_changes.txt" in path
                    for path in result.optimizer_log_tree
                )
                record = {
                    "kind": "adaptive_proposal",
                    "attempt": attempts,
                    "iteration": step,
                    "solver_entry_id": produced.id,
                    "candidate_id": candidate.get("candidate_id"),
                    "parent_candidate_id": candidate.get("parent_candidate_id"),
                    "generation": candidate.get("generation"),
                    "language_sha256": candidate.get("language_sha256"),
                    "expanded_program_sha256": expanded_hash,
                    "duplicate_expanded_ast": repeated,
                    "status": evaluation_status,
                    "stage_one_fitness": (artifact or {}).get("evaluation", {}).get(
                        "stage_one_fitness"
                    ),
                    "discovery_fitness": (artifact or {}).get("discovery_fitness"),
                    "optimizer_id": result.optimizer.id,
                    "guidance_revision_sha256": hashlib.sha256(
                        json.dumps(result.optimizer.files, sort_keys=True).encode()
                    ).hexdigest(),
                    "workspace_id": result.workspace_id,
                    "worker_name": result.worker_name,
                    "token_usage": usage,
                    "reported_input_plus_output_tokens": increment,
                    "cumulative_reported_input_plus_output_tokens": token_total,
                    "boundary_violation": boundary_violation,
                    "recorded_at_utc": datetime.now(UTC).isoformat(),
                }
                if candidate_record is not None:
                    record["primary_record"] = candidate_record
                _write_jsonl(run_root / "trajectory.jsonl", record)
                if factory.loop.logger is not None:
                    factory.loop.logger.on_iteration(
                        iteration=step,
                        solver_entries=factory.loop.solver_pop.entries(),
                        optimizer_entries=factory.loop.optimizer_pop.entries(),
                        phase2_results=results,
                    )
                factory.loop._iterations_completed = step
                successful, unique_count, _ = _population_counts(
                    factory.loop.solver_pop.entries()
                )
                run_status = "running"
                if boundary_violation:
                    run_status = "terminated_protected_boundary_violation"
                elif candidate_record and candidate_record.get("status") == "fatal_protocol_failure":
                    run_status = "incomplete_terminal_protocol_failure"
                elif token_total > TOKEN_CAP:
                    run_status = "incomplete_token_cap_overrun"
                elif unique_count >= UNIQUE_TARGET:
                    run_status = "complete"
                elif attempts >= MAX_ATTEMPTS:
                    run_status = "incomplete_attempt_cap"
                elif token_total >= TOKEN_CAP:
                    run_status = "incomplete_token_cap"
                last_state = _write_iteration_snapshot(
                    run_root=run_root,
                    step=step,
                    seed=seed,
                    contract=contract,
                    attempts=attempts,
                    token_total=token_total,
                    rng_state=_rng_state(factory),
                    status=run_status,
                )
                factory.loop._persist_iteration_boundary(step)
                _write_atomic(run_root / "progress.json", _json_bytes(
                    {
                        "seed": seed,
                        "status": run_status,
                        "adaptive_attempts": attempts,
                        "successful_candidates": successful,
                        "unique_successful_expanded_asts": unique_count,
                        "reported_input_plus_output_tokens": token_total,
                        "updated_at_utc": datetime.now(UTC).isoformat(),
                    }
                ))
                if run_status != "running":
                    break
            else:
                run_status = "incomplete_attempt_cap"

            if run_status == "running":
                _, unique_count, _ = _population_counts(factory.loop.solver_pop.entries())
                run_status = "complete" if unique_count >= UNIQUE_TARGET else "incomplete_attempt_cap"
            if factory.loop.logger is not None:
                factory.loop.logger.finish(
                    solver_entries=factory.loop.solver_pop.entries(),
                    optimizer_entries=factory.loop.optimizer_pop.entries(),
                    iterations_completed=factory.loop.iterations_completed,
                )
            last_state = _write_iteration_snapshot(
                run_root=run_root,
                step=factory.loop.iterations_completed,
                seed=seed,
                contract=contract,
                attempts=attempts,
                token_total=token_total,
                rng_state=_rng_state(factory),
                status=run_status,
            )
            _build_final_manifest(
                run_root=run_root,
                contract=contract,
                seed=seed,
                state=last_state,
                factory=factory,
                run_status=run_status,
            )
            print(
                json.dumps(
                    {
                        "seed": seed,
                        "status": run_status,
                        "attempts": attempts,
                        "successful_candidates": _population_counts(
                            factory.loop.solver_pop.entries()
                        )[0],
                        "unique_successful_expanded_asts": _population_counts(
                            factory.loop.solver_pop.entries()
                        )[1],
                        "reported_input_plus_output_tokens": token_total,
                        "run_root": str(run_root),
                    },
                    sort_keys=True,
                )
            )
            return 0 if run_status == "complete" else 2
    except BaseException:
        if not validate_only and run_root.exists():
            failure = {
                "seed": seed,
                "status": "interrupted_or_failed",
                "traceback": traceback.format_exc(),
                "recorded_at_utc": datetime.now(UTC).isoformat(),
            }
            with (run_root / "failures.jsonl").open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(failure, sort_keys=True) + "\n")
        raise
    finally:
        drivers.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", required=True, type=Path)
    parser.add_argument("--seed", type=int)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()
    contract = validate_contract(
        args.contract,
        expected_seed=args.seed,
        allow_existing_run_root=args.resume,
    )
    return _run_primary(
        contract=contract,
        seed=int(contract["seed"]),
        resume=args.resume,
        validate_only=args.validate_only,
    )


if __name__ == "__main__":
    raise SystemExit(main())
