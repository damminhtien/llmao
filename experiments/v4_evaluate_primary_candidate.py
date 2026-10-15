"""Evaluate one candidate under the finalized V4 discovery protocol."""

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
from bias_optimizer.v4.discovery import (
    apply_discovery_score,
    load_finalized_protocol,
    verify_source_pins,
)
from bias_optimizer.v4.evaluator import (
    evaluate_candidate,
    failure_artifact,
    validate_protocol,
)


def _write_new(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")


def _primary_evaluator_digest(protocol: dict[str, Any]) -> tuple[str, list[dict[str, str]]]:
    sources = verify_source_pins(ROOT, protocol)
    records = [{"path": name, "sha256": digest} for name, digest in sorted(sources.items())]
    digest = hashlib.sha256()
    for record in records:
        digest.update(record["path"].encode("utf-8"))
        digest.update(b"\0")
        digest.update(bytes.fromhex(record["sha256"]))
        digest.update(b"\0")
    return digest.hexdigest(), records


def _inside(path: Path, directory: Path) -> bool:
    try:
        path.resolve(strict=False).relative_to(directory.resolve(strict=False))
        return True
    except ValueError:
        return False


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("candidate_directory", type=Path)
    parser.add_argument("--context", type=Path, required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--protocol-sha256", required=True)
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--log", type=Path, required=True)
    args = parser.parse_args()

    candidate_directory = args.candidate_directory.resolve(strict=False)
    output_path = args.output.resolve(strict=False)
    log_path = args.log.resolve(strict=False)
    candidate_id: str | None = None
    protocol: dict[str, Any] | None = None
    stage = "protocol_validation"
    failure: Exception | None = None
    failure_traceback: str | None = None
    artifact: dict[str, Any]
    snapshot_hash = "0" * 64
    source_records: list[dict[str, str]] = []
    try:
        if output_path == log_path or _inside(output_path, candidate_directory) or _inside(
            log_path, candidate_directory
        ):
            raise ValueError("primary score artifacts must be outside the candidate directory")
        if output_path.exists() or log_path.exists():
            raise FileExistsError("primary score artifact paths must be new")
        protocol, protocol_sha256 = load_finalized_protocol(
            args.protocol,
            expected_sha256=args.protocol_sha256,
        )
        if protocol_sha256 != args.protocol_sha256:
            raise ValueError("primary protocol digest mismatch")
        _ = validate_protocol(args.protocol)
        snapshot_hash, source_records = _primary_evaluator_digest(protocol)
        if args.candidate_directory.is_symlink() or not candidate_directory.is_dir():
            raise ValueError("candidate path must be a regular directory")
        context_path = args.context.resolve(strict=True)
        if args.context.is_symlink() or _inside(context_path, candidate_directory):
            raise ValueError("trusted candidate context must stay outside the candidate directory")
        data_dir = args.data_dir.resolve(strict=False)
        if _inside(data_dir, candidate_directory) or _inside(data_dir, ROOT):
            raise ValueError("primary MNIST cache must be outside the LLMAO checkout and worker")

        stage = "candidate_validation"
        context = read_json(context_path)
        if isinstance(context, dict) and isinstance(context.get("candidate_id"), str):
            candidate_id = context["candidate_id"]
        candidate = load_candidate_directory(candidate_directory, context=context)
        stage = "candidate_evaluation"
        evaluator = Evaluator(
            LearnerConfig(regularization_c=1.0, max_iter=1_000, seed=42),
            data_config=MNISTDataConfig(
                seed=42,
                validation_size=2_000,
                data_dir=data_dir,
            ),
        )
        stage_one = evaluate_candidate(
            candidate,
            evaluator,
            evaluator_version_sha256=snapshot_hash,
            protocol_status="finalized_primary",
            cache_namespace="mnist_v4_primary_expanded_ast",
        )
        artifact = apply_discovery_score(
            stage_one,
            candidate.language,
            protocol_sha256=protocol_sha256,
            parent_candidate_id=candidate.provenance.parent_candidate_id,
        )
    except Exception as exc:  # noqa: BLE001 - preserve each rejected attempt
        failure = exc
        failure_traceback = traceback.format_exc()
        artifact = failure_artifact(
            evaluator_version_sha256=snapshot_hash,
            protocol_status=(str(protocol.get("status")) if protocol else None),
            stage=stage,
            error=exc,
            candidate_id=candidate_id,
        )
        artifact["protocol_sha256"] = args.protocol_sha256

    artifact["evaluator_sources"] = source_records
    artifact["input_sha256"] = {
        name: hashlib.sha256(path.read_bytes()).hexdigest()
        for name, path in (
            ("context", args.context.resolve(strict=False)),
            ("language", candidate_directory / "language.json"),
            ("program", candidate_directory / "program.json"),
        )
        if path.is_file() and not path.is_symlink()
    }
    artifact["recorded_at_utc"] = datetime.now(UTC).isoformat()
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("x", encoding="utf-8") as stream:
        stream.write(f"candidate_id={candidate_id or 'unknown'}\n")
        stream.write(f"evaluator_version_sha256={snapshot_hash}\n")
        stream.write(f"status={artifact['status']}\n")
        if failure_traceback:
            stream.write(failure_traceback)
    _write_new(output_path, artifact)
    print(json.dumps({"status": artifact["status"], "artifact": str(output_path)}))
    return 1 if failure is not None else 0


if __name__ == "__main__":
    raise SystemExit(main())
