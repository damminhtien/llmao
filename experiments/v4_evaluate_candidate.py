"""Evaluate a V4 candidate directory with the frozen V3.2 stage-one protocol."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import traceback
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from bias_optimizer.data.mnist import MNISTDataConfig
from bias_optimizer.ml.evaluator import Evaluator
from bias_optimizer.ml.learner import LearnerConfig
from bias_optimizer.v4.candidate import load_candidate_directory
from bias_optimizer.v4.candidate.loader import read_json
from bias_optimizer.v4.evaluator import (
    evaluate_candidate,
    evaluator_source_snapshot,
    failure_artifact,
    validate_protocol,
)
from bias_optimizer.v4.language.base_language import G0_LANGUAGE

try:
    from .v4_artifact_paths import resolve_v4_output_path
except ImportError:
    from v4_artifact_paths import resolve_v4_output_path


def _inside(path: Path, directory: Path) -> bool:
    try:
        path.resolve(strict=False).relative_to(directory.resolve(strict=False))
        return True
    except ValueError:
        return False


def _write_json_exclusive(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")


def _argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("candidate_directory", type=Path)
    parser.add_argument(
        "--context",
        type=Path,
        required=True,
        help="Evaluator-managed provenance and trusted parent-language history JSON.",
    )
    parser.add_argument("--data-dir", type=Path, default=ROOT / "data")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--log", type=Path)
    return parser


def _run(args: argparse.Namespace) -> int:
    candidate_directory = args.candidate_directory.resolve(strict=False)
    run_stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    default_artifact_path = (
        ROOT / "results/v4/evaluations" / f"{candidate_directory.name}-{run_stamp}.json"
    )
    default_log_path = (
        ROOT / "results/v4/evaluator_logs" / f"{candidate_directory.name}-{run_stamp}.log"
    )
    path_error: ValueError | None = None
    try:
        artifact_path = resolve_v4_output_path(
            args.output if args.output else default_artifact_path, repo_root=ROOT
        )
        log_path = resolve_v4_output_path(
            args.log if args.log else default_log_path, repo_root=ROOT
        )
    except ValueError as exc:
        print(json.dumps({"status": "rejected", "error": str(exc)}), file=sys.stderr)
        return 2
    if path_error is None and (
        _inside(artifact_path, candidate_directory)
        or _inside(log_path, candidate_directory)
    ):
        path_error = ValueError(
            "score artifacts and evaluator logs must be outside the candidate directory"
        )
    elif path_error is None and artifact_path == log_path:
        path_error = ValueError("score artifact and evaluator log paths must differ")
    elif path_error is None and (artifact_path.exists() or log_path.exists()):
        path_error = FileExistsError("score artifact and evaluator log paths must be new")
    if path_error is not None:
        artifact_path = default_artifact_path
        log_path = default_log_path

    snapshot = evaluator_source_snapshot(ROOT)
    protocol: dict[str, Any] | None = None
    candidate_id: str | None = None
    stage = "invocation_validation"
    failure: Exception | None = None
    failure_traceback: str | None = None
    artifact: dict[str, Any]
    try:
        if path_error is not None:
            raise path_error
        if args.candidate_directory.is_symlink() or not candidate_directory.is_dir():
            raise ValueError("candidate path must be a regular directory")
        context_path = args.context.resolve(strict=False)
        if args.context.is_symlink() or not context_path.is_file():
            raise ValueError("evaluator context must be a regular file")
        if _inside(context_path, candidate_directory):
            raise ValueError("evaluator context must be outside the candidate directory")
        data_dir = args.data_dir.resolve(strict=False)
        if _inside(data_dir, candidate_directory):
            raise ValueError("dataset cache must be outside the candidate directory")

        stage = "protocol_validation"
        protocol = validate_protocol(ROOT / "results/v4/protocol.json")
        protocol_status = str(protocol.get("status", "unknown"))
        expected_g0_hash = protocol["language_conditions"]["G0"]["manifest_sha256"]
        if expected_g0_hash != G0_LANGUAGE.sha256:
            raise ValueError("runtime G0 language hash does not match the V4 protocol")

        stage = "candidate_validation"
        context = read_json(context_path)
        if isinstance(context, dict) and isinstance(context.get("candidate_id"), str):
            candidate_id = context["candidate_id"]
        candidate = load_candidate_directory(candidate_directory, context=context)
        candidate_id = candidate.candidate_id

        stage = "candidate_evaluation"
        evaluator = Evaluator(
            LearnerConfig(regularization_c=1.0, max_iter=1_000, seed=42),
            data_config=MNISTDataConfig(
                seed=42,
                validation_size=2_000,
                data_dir=data_dir,
            ),
        )
        artifact = evaluate_candidate(
            candidate,
            evaluator,
            evaluator_version_sha256=snapshot["sha256"],
            protocol_status=protocol_status,
        )
    except Exception as exc:  # noqa: BLE001 - every evaluator failure gets an artifact
        failure = exc
        failure_traceback = traceback.format_exc()
        artifact = failure_artifact(
            evaluator_version_sha256=snapshot["sha256"],
            protocol_status=(
                str(protocol.get("status", "unknown")) if protocol else None
            ),
            stage=stage,
            error=exc,
            candidate_id=candidate_id,
        )

    artifact["evaluator_sources"] = snapshot["sources"]
    artifact["input_sha256"] = {
        name: _sha256(path)
        for name, path in (
            ("context", args.context.resolve(strict=False)),
            ("language", candidate_directory / "language.json"),
            ("program", candidate_directory / "program.json"),
        )
        if path.is_file() and not path.is_symlink()
    }
    artifact["recorded_at_utc"] = datetime.now(UTC).isoformat()

    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("x", encoding="utf-8") as log_file:
        log_file.write(f"candidate_id={candidate_id or 'unknown'}\n")
        log_file.write(f"evaluator_version_sha256={snapshot['sha256']}\n")
        log_file.write(f"status={artifact['status']}\n")
        if failure_traceback is not None:
            log_file.write(failure_traceback)

    _write_json_exclusive(artifact_path, artifact)
    print(json.dumps({"status": artifact["status"], "artifact": str(artifact_path)}))
    return 1 if failure is not None else 0


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    args = _argument_parser().parse_args()
    try:
        return _run(args)
    except Exception as exc:  # noqa: BLE001 - report command-level failures succinctly
        print(f"V4 evaluator error: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
