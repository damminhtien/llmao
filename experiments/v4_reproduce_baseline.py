"""Reproduce the frozen V3.2 smoke search without writing into V3.2 results."""

from __future__ import annotations

import hashlib
import json
import platform
import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

import numpy as np

import bias_optimizer.optimizer_bench.runner as v32_runner
from bias_optimizer.data.mnist import load_mnist_search_data
from bias_optimizer.llm.ollama_client import OllamaLLMClient
from bias_optimizer.optimizer_bench.budget import SearchBudget
from bias_optimizer.optimizer_bench.trace import read_trace

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "results/v4/baseline_reproduction"
MANIFEST_PATH = OUTPUT_DIR / "manifest.json"
V32_PROTOCOL_PATH = ROOT / "results/v32/protocol.json"
V32_MANIFEST_PATH = ROOT / "results/v32/manifest.json"
V32_SOURCE_COMMIT = "85beeaff62791946989b3163cd67fbaed7e7c108"
V4_BASE_COMMIT = "ea6e1d6d268a10bdafc2061c73fcb2c694be9679"
SEED_SCORE_TOLERANCE = 0.001
SMOKE_MAX_PROPOSAL_ATTEMPTS = 60


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _json_write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def _array_fingerprint(*arrays: np.ndarray) -> str:
    digest = hashlib.sha256()
    for values in arrays:
        array = np.ascontiguousarray(values)
        digest.update(str(array.dtype).encode("ascii"))
        digest.update(b"\0")
        digest.update(json.dumps(array.shape).encode("ascii"))
        digest.update(b"\0")
        digest.update(array.tobytes(order="C"))
    return digest.hexdigest()


def _prepare_manifest(protocol_sha256: str) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    copied_protocol = OUTPUT_DIR / "protocol.json"
    if copied_protocol.exists():
        if _sha256(copied_protocol) != protocol_sha256:
            raise ValueError("baseline reproduction protocol copy has changed")
    else:
        shutil.copyfile(V32_PROTOCOL_PATH, copied_protocol)

    if MANIFEST_PATH.exists():
        manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        if manifest.get("protocol", {}).get("sha256") != protocol_sha256:
            raise ValueError("baseline reproduction manifest has a different protocol")
        manifest["runs"] = []
        manifest["status"] = "in_progress"
        _json_write(MANIFEST_PATH, manifest)
        return

    _json_write(
        MANIFEST_PATH,
        {
            "schema_version": 1,
            "study_id": "v4-baseline-reproduction",
            "status": "in_progress",
            "protocol": {"path": "protocol.json", "sha256": protocol_sha256},
            "source": {
                "study_id": "v3.2-optimizer-value-study",
                "source_commit": V32_SOURCE_COMMIT,
                "v4_base_commit": V4_BASE_COMMIT,
                "v32_manifest_sha256": _sha256(V32_MANIFEST_PATH),
            },
            "runs": [],
        },
    )


def _compare_seed_evaluations(
    optimizer: str, seed: int, trace_path: Path
) -> dict[str, Any]:
    reference_path = (
        ROOT / "results/v32/runs/smoke" / optimizer / f"seed_{seed}/trace.json"
    )
    reference = read_trace(reference_path)
    reproduced = read_trace(trace_path)
    reference_rows = reference.evaluated_candidates[:20]
    reproduced_rows = reproduced.evaluated_candidates[:20]

    candidate_ids_match = [row.candidate_id for row in reference_rows] == [
        row.candidate_id for row in reproduced_rows
    ]
    equal_lengths = len(reference_rows) == len(reproduced_rows)
    accuracy_matches = equal_lengths and all(
        left.accuracy == right.accuracy
        for left, right in zip(reference_rows, reproduced_rows)
    )
    dimensions_match = equal_lengths and all(
        left.feature_dim == right.feature_dim
        for left, right in zip(reference_rows, reproduced_rows)
    )
    fitness_deltas = (
        [
            abs(left.fitness - right.fitness)
            for left, right in zip(reference_rows, reproduced_rows)
        ]
        if equal_lengths
        else []
    )
    maximum_fitness_delta = max(fitness_deltas, default=None)
    within_tolerance = maximum_fitness_delta is not None and (
        maximum_fitness_delta <= SEED_SCORE_TOLERANCE
    )
    passed = (
        len(reference_rows) == 20
        and len(reproduced_rows) == 20
        and candidate_ids_match
        and accuracy_matches
        and dimensions_match
        and within_tolerance
    )
    return {
        "reference_trace": str(reference_path.relative_to(ROOT)),
        "reference_trace_sha256": _sha256(reference_path),
        "evaluated_seed_programs": len(reproduced_rows),
        "candidate_ids_match": candidate_ids_match,
        "accuracy_matches_exactly": accuracy_matches,
        "feature_dimensions_match": dimensions_match,
        "maximum_absolute_fitness_delta": maximum_fitness_delta,
        "fitness_tolerance": SEED_SCORE_TOLERANCE,
        "passed": passed,
    }


def reproduce() -> dict[str, Any]:
    protocol = v32_runner.verify_protocol()
    v32_protocol_sha256 = protocol["protocol_sha256"]
    v32_manifest_sha256 = _sha256(V32_MANIFEST_PATH)
    _prepare_manifest(v32_protocol_sha256)

    search_data = load_mnist_search_data()
    train_500_images, train_500_labels = search_data.sample_training_data(500, seed=42)
    split_fingerprints = {
        "training_partition_search_pool": _array_fingerprint(
            search_data.train_images, search_data.train_labels
        ),
        "validation_split": _array_fingerprint(
            search_data.validation_images, search_data.validation_labels
        ),
        "training_subset_500_seed_42": _array_fingerprint(
            train_500_images, train_500_labels
        ),
    }

    v32_budget = protocol["budget"]
    seed = int(v32_budget["smoke_optimizer_seeds"][0])
    budget = SearchBudget(
        total_evaluations=int(v32_budget["smoke_total_evaluations_per_optimizer"]),
        seed_evaluations=int(v32_budget["seed_evaluations"]),
        max_proposal_attempts=SMOKE_MAX_PROPOSAL_ATTEMPTS,
    )
    run_id = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid4().hex[:8]
    run_output_root = OUTPUT_DIR / "runs" / run_id
    local_qwen = OllamaLLMClient(model="qwen3.5:35b-mlx")

    def register_v4_run(
        trace: Any,
        trace_path: Path,
        *,
        phase: str,
        manifest_path: Path,
        condition: str | None = None,
    ) -> dict[str, Any]:
        _ = (manifest_path, condition)
        manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        row = {
            "phase": "baseline_reproduction",
            "run_id": run_id,
            "optimizer": trace.optimizer,
            "optimizer_seed": trace.optimizer_seed,
            "evaluated_candidates": len(trace.evaluated_candidates),
            "requested_evaluations": trace.budget_total_evaluations,
            "complete": trace.complete,
            "trace": str(Path(trace_path).resolve().relative_to(ROOT)),
            "trace_sha256": _sha256(Path(trace_path)),
            "protocol_sha256": manifest["protocol"]["sha256"],
        }
        manifest["runs"] = [
            existing
            for existing in manifest.get("runs", [])
            if not (
                existing.get("phase") == row["phase"]
                and existing.get("optimizer") == row["optimizer"]
                and existing.get("optimizer_seed") == row["optimizer_seed"]
                and existing.get("run_id") == run_id
            )
        ] + [row]
        manifest["runs"].sort(key=lambda item: item["optimizer"])
        manifest["status"] = (
            "complete"
            if len(manifest["runs"]) == len(v32_runner.OPTIMIZERS)
            and all(item["run_id"] == run_id for item in manifest["runs"])
            and all(item["complete"] for item in manifest["runs"])
            else "in_progress"
        )
        _json_write(MANIFEST_PATH, manifest)
        return row

    original_register = v32_runner.register_run
    v32_runner.register_run = register_v4_run
    conditions = []
    try:
        for optimizer in v32_runner.OPTIMIZERS:
            trace = v32_runner.run_optimizer(
                optimizer,
                seed,
                budget=budget,
                output_root=run_output_root,
                phase="smoke",
                client=local_qwen,
            )
            trace_path = (
                run_output_root / optimizer / f"seed_{seed}/trace.json"
            )
            conditions.append(
                {
                    "optimizer": optimizer,
                    "seed": seed,
                    "evaluated_candidates": len(trace.evaluated_candidates),
                    "requested_candidates": budget.total_evaluations,
                    "proposal_attempts": trace.proposal_attempts,
                    "llm_calls": trace.llm_calls,
                    "llm_tokens": trace.llm_tokens,
                    "evaluation_runtime_ms": trace.evaluation_time_ms,
                    "total_runtime_ms": trace.total_wall_time_ms,
                    "complete": trace.complete,
                    "trace": str(trace_path.relative_to(ROOT)),
                    "trace_sha256": _sha256(trace_path),
                    "seed_reproduction": _compare_seed_evaluations(
                        optimizer, seed, trace_path
                    ),
                }
            )
    finally:
        v32_runner.register_run = original_register

    source_hashes_unchanged = (
        _sha256(V32_PROTOCOL_PATH) == v32_protocol_sha256
        and _sha256(V32_MANIFEST_PATH) == v32_manifest_sha256
    )
    v32_runner.verify_protocol()
    passed = source_hashes_unchanged and all(
        row["complete"]
        and row["evaluated_candidates"] == budget.total_evaluations
        and row["seed_reproduction"]["passed"]
        for row in conditions
    )
    summary = {
        "schema_version": 1,
        "study_id": "v4-baseline-reproduction",
        "status": "passed" if passed else "failed",
        "observed_on": datetime.now(UTC).isoformat(),
        "source": {
            "v3_2_commit": V32_SOURCE_COMMIT,
            "v4_base_commit": V4_BASE_COMMIT,
            "v3_2_protocol_sha256": v32_protocol_sha256,
            "v3_2_manifest_sha256_before": v32_manifest_sha256,
            "v3_2_manifest_sha256_after": _sha256(V32_MANIFEST_PATH),
            "v3_2_artifacts_unchanged": source_hashes_unchanged,
        },
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "llm_backend": "Ollama local",
            "llm_model": local_qwen.model,
            "official_test_access": False,
        },
        "protocol": {
            "train_pool_size": len(search_data.train_labels),
            "validation_size": len(search_data.validation_labels),
            "validation_split_seed": search_data.seed,
            "training_subset_size": 500,
            "training_subset_seed": 42,
            "official_test_partition_used": False,
            "split_fingerprints_sha256": split_fingerprints,
            "smoke_seed": seed,
            "total_evaluations_per_optimizer": budget.total_evaluations,
            "seed_evaluations": budget.seed_evaluations,
            "max_proposal_attempts": budget.max_proposal_attempts,
            "seed_fitness_absolute_tolerance": SEED_SCORE_TOLERANCE,
        },
        "run_id": run_id,
        "conditions": conditions,
    }
    _json_write(OUTPUT_DIR / "summary.json", summary)
    return summary


def main() -> None:
    summary = reproduce()
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if summary["status"] != "passed":
        raise SystemExit("V3.2 baseline reproduction failed its frozen checks")


if __name__ == "__main__":
    main()
