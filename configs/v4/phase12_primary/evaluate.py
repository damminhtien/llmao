"""EvE shell-step adapter for the finalized V4 discovery evaluator."""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


class TerminalContractError(RuntimeError):
    """Stop a seed when its pinned source, runtime, or data boundary breaks."""


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_failure(
    log_root: Path,
    message: str,
    details: str = "",
    *,
    terminal: bool = False,
) -> None:
    score = {
        "score": 0.0,
        "summary": message,
        "status": "failed",
        "discovery_ready": False,
    }
    (log_root / "score.yaml").write_text(
        json.dumps(score, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (log_root / "error.txt").write_text(f"{message}\n{details}", encoding="utf-8")
    _write_json(
        log_root / "primary_record.json",
        {
            "kind": "adaptive_proposal",
            "status": "fatal_protocol_failure" if terminal else "failed",
            "failure": message,
            "details": details,
            "recorded_at_utc": datetime.now(UTC).isoformat(),
        },
    )


def _run(command: list[str], *, cwd: Path, timeout: int) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=cwd,
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
    )


def _empty_lineage() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "candidate_id": None,
        "generation": -1,
        "language_hash": None,
        "language_lineage": [],
    }


def _parent_state(workspace_root: Path) -> tuple[dict[str, Any], str | None]:
    phase_workspace = workspace_root.parent.parent / "solver_workspaces" / workspace_root.name
    metadata = phase_workspace / ".scaling_evolve" / "worker.yaml"
    if not metadata.is_file():
        return _empty_lineage(), None
    readme = phase_workspace / "README.md"
    if not readme.is_file():
        raise ValueError("Phase 2 workspace is missing its rendered README")
    matches = re.findall(
        r"^\s*-\s+`solver_examples/([^/]+)/`\s+<-\s+prefill\s*$",
        readme.read_text(encoding="utf-8"),
        flags=re.MULTILINE,
    )
    if len(matches) != 1:
        raise ValueError(f"expected one rendered prefill marker, found {len(matches)}")
    prefill_id = matches[0]
    state_path = workspace_root / "solver_examples" / prefill_id / "logs/evaluate/lineage_state.json"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    if not isinstance(state, dict) or state.get("schema_version") != 1:
        raise ValueError(f"invalid evaluator lineage state: {state_path}")
    if not isinstance(state.get("language_lineage"), list):
        raise TypeError("lineage state must carry ordered language snapshots")
    return state, prefill_id


def _guidance_hash(workspace_root: Path) -> str:
    digest = hashlib.sha256()
    guidance_root = workspace_root / "guidance"
    for path in sorted(item for item in guidance_root.rglob("*") if item.is_file()):
        digest.update(path.relative_to(guidance_root).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def _evaluate(
    workspace_root: Path,
    solver_root: Path,
    log_root: Path,
    project_root: Path,
) -> None:
    expected_commit = os.environ["LLMAO_EXPECTED_COMMIT"]
    protocol = Path(os.environ["LLMAO_PHASE12_PROTOCOL"]).resolve(strict=True)
    context_builder = Path(os.environ["LLMAO_PHASE12_CONTEXT_BUILDER"]).resolve(strict=True)
    evaluator = Path(os.environ["LLMAO_PHASE12_EVALUATOR"]).resolve(strict=True)
    expected_protocol_sha = os.environ["LLMAO_PHASE12_PROTOCOL_SHA256"]
    data_dir = Path(os.environ["LLMAO_DATA_DIR"]).resolve()
    python = Path(os.environ["LLMAO_PYTHON"]).resolve(strict=True)
    if len(expected_commit) != 40 or any(c not in "0123456789abcdef" for c in expected_commit):
        raise TerminalContractError("LLMAO_EXPECTED_COMMIT must be a full lowercase Git SHA")
    if not python.is_file() or not os.access(python, os.X_OK):
        raise TerminalContractError("LLMAO_PYTHON must be an executable interpreter")
    for name, path in (("context builder", context_builder), ("primary evaluator", evaluator)):
        if not path.is_file():
            raise TerminalContractError(f"primary {name} is missing: {path}")

    head = _run(["git", "-C", str(project_root), "rev-parse", "HEAD"], cwd=workspace_root, timeout=30)
    if head.returncode or head.stdout.strip() != expected_commit:
        raise TerminalContractError("LLMAO checkout does not match the frozen primary contract")
    status = _run(
        ["git", "-C", str(project_root), "status", "--porcelain", "--untracked-files=all"],
        cwd=workspace_root,
        timeout=30,
    )
    if status.returncode or status.stdout.strip():
        raise TerminalContractError("LLMAO source checkout must remain clean during discovery")
    if data_dir == project_root or project_root in data_dir.parents:
        raise TerminalContractError("LLMAO_DATA_DIR must be outside the LLMAO checkout")
    data_dir.mkdir(parents=True, exist_ok=True)

    parent_state, prefill_id = _parent_state(workspace_root)
    _write_json(log_root / "lineage_state.json", parent_state)
    _write_json(log_root / "parent_language_lineage.json", parent_state["language_lineage"])
    generation = parent_state["generation"] + 1 if prefill_id else 0
    if prefill_id and not parent_state.get("candidate_id"):
        _write_failure(log_root, "selected prefill has no valid V4 candidate lineage")
        return
    context_path = log_root / "context.json"
    validated_state_path = log_root / "validated_lineage_state.json"
    context_command = [
        str(python),
        str(context_builder),
        str(solver_root / "candidate"),
        str(context_path),
        "--protocol",
        str(protocol),
        "--parent-lineage",
        str(log_root / "parent_language_lineage.json"),
        "--generation",
        str(generation),
        "--guidance-hash",
        _guidance_hash(workspace_root),
        "--lineage-state-output",
        str(validated_state_path),
    ]
    if prefill_id:
        context_command.extend(["--parent-candidate-id", str(parent_state["candidate_id"])])
    context_result = _run(context_command, cwd=workspace_root, timeout=120)
    (log_root / "context_command.log").write_text(
        context_result.stdout + context_result.stderr, encoding="utf-8"
    )
    if context_result.returncode:
        _write_failure(log_root, "candidate context validation failed", context_result.stderr)
        return
    validated_state = json.loads(validated_state_path.read_text(encoding="utf-8"))
    _write_json(log_root / "lineage_state.json", validated_state)
    validated_state_path.unlink()
    _write_json(
        log_root / "lineage_parent.json",
        {
            "eve_prefill_id": prefill_id,
            "parent_candidate_id": parent_state.get("candidate_id"),
            "parent_language_hash": parent_state.get("language_hash"),
            "generation": generation,
        },
    )

    command = [
        str(python),
        str(evaluator),
        str(solver_root / "candidate"),
        "--context",
        str(context_path),
        "--protocol",
        str(protocol),
        "--protocol-sha256",
        expected_protocol_sha,
        "--data-dir",
        str(data_dir),
        "--output",
        str(log_root / "evaluator.json"),
        "--log",
        str(log_root / "evaluator.log"),
    ]
    result = _run(command, cwd=workspace_root, timeout=1_800)
    (log_root / "evaluator_command.log").write_text(
        result.stdout + result.stderr, encoding="utf-8"
    )
    artifact_path = log_root / "evaluator.json"
    if not artifact_path.is_file():
        _write_failure(
            log_root,
            "primary evaluator did not produce its artifact",
            f"exit_code={result.returncode}\n{result.stderr}",
        )
        return
    artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
    evaluation = artifact.get("evaluation")
    score = artifact.get("discovery_fitness")
    if (
        result.returncode
        or artifact.get("status") != "discovery_scored"
        or artifact.get("discovery_ready") is not True
        or not isinstance(evaluation, dict)
        or isinstance(score, bool)
        or not isinstance(score, (int, float))
        or not math.isfinite(score)
    ):
        failure = artifact.get("failure") or {}
        _write_failure(
            log_root,
            "primary candidate evaluation failed",
            json.dumps(failure),
            terminal=failure.get("stage") == "protocol_validation",
        )
        return
    payload = {
        "score": float(score),
        "summary": "finalized V4 discovery fitness",
        "status": artifact["status"],
        "protocol_status": artifact["protocol_status"],
        "protocol_sha256": artifact["protocol_sha256"],
        "score_source": "discovery_fitness",
        "candidate_id": artifact["candidate"]["candidate_id"],
        "parent_candidate_id": artifact["candidate"]["parent_candidate_id"],
        "generation": artifact["candidate"]["generation"],
        "parent_prefill_id": prefill_id,
        "language_sha256": artifact["candidate"]["language_sha256"],
        "expanded_program_sha256": artifact["candidate"]["expanded_program_sha256"],
        "evaluation_seed": artifact["candidate"]["evaluation_seed"],
        "stage_one_fitness": evaluation["stage_one_fitness"],
        "discovery_fitness": float(score),
        "accuracy_500": evaluation["accuracy_500"],
        "feature_dimension": evaluation["feature_dimension"],
        "feature_runtime_ms": evaluation["feature_runtime_ms"],
        "training_runtime_ms": evaluation["training_runtime_ms"],
        "inference_runtime_ms": evaluation["inference_runtime_ms"],
        "language_complexity": evaluation["language_complexity"],
        "language_penalty": evaluation["language_penalty"],
        "discovery_ready": True,
        "evaluator_version_sha256": artifact["evaluator_version_sha256"],
    }
    (log_root / "score.yaml").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    _write_json(
        log_root / "primary_record.json",
        {
            "kind": "adaptive_proposal",
            "status": artifact["status"],
            "candidate_id": artifact["candidate"]["candidate_id"],
            "parent_candidate_id": artifact["candidate"]["parent_candidate_id"],
            "generation": artifact["candidate"]["generation"],
            "language_sha256": artifact["candidate"]["language_sha256"],
            "expanded_program_sha256": artifact["candidate"]["expanded_program_sha256"],
            "introduced_macros": artifact["candidate"]["introduced_macros"],
            "language_macros": artifact["candidate"]["language_macros"],
            "stage_one_fitness": evaluation["stage_one_fitness"],
            "discovery_fitness": float(score),
            "recorded_at_utc": datetime.now(UTC).isoformat(),
        },
    )
    (log_root / "error.txt").unlink(missing_ok=True)


def main() -> int:
    if len(sys.argv) != 5:
        raise SystemExit("usage: evaluate.py WORKSPACE SOLVER LOGS LLMAO_ROOT")
    workspace, solver, logs, project = [Path(value).expanduser().resolve() for value in sys.argv[1:]]
    logs.mkdir(parents=True, exist_ok=True)
    try:
        _evaluate(workspace, solver, logs, project)
    except Exception as exc:  # noqa: BLE001 - a failed attempt still gets a score record
        _write_failure(
            logs,
            f"{type(exc).__name__}: {exc}",
            terminal=isinstance(exc, TerminalContractError),
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
