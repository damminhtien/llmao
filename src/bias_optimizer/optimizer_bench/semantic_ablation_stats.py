"""Summaries for the paired V3.2 semantic-ablation traces."""

from __future__ import annotations

import json
import statistics
from pathlib import Path
from typing import Any

from bias_optimizer.optimizer_bench.runner import sha256, verify_protocol
from bias_optimizer.optimizer_bench.statistics import _paired_bootstrap
from bias_optimizer.optimizer_bench.trace import read_trace


def _distribution(values: list[float]) -> dict[str, float | int | None]:
    if not values:
        return {
            "n": 0,
            "mean": None,
            "median": None,
            "sd": None,
            "min": None,
            "max": None,
        }
    return {
        "n": len(values),
        "mean": float(statistics.mean(values)),
        "median": float(statistics.median(values)),
        "sd": float(statistics.stdev(values)) if len(values) > 1 else 0.0,
        "min": float(min(values)),
        "max": float(max(values)),
    }


def summarize_semantic_ablation(root: Path) -> dict[str, Any]:
    root = Path(root)
    parent = verify_protocol(root)
    semantic_path = root / "results/v32/semantic_ablation_protocol.json"
    semantic_protocol = json.loads(semantic_path.read_text(encoding="utf-8"))
    semantic_hash = semantic_protocol["protocol_sha256"]
    payload = dict(semantic_protocol)
    payload.pop("protocol_sha256")
    actual_hash = sha256_bytes(
        (json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode()
    )
    checksum = (semantic_path.parent / "semantic_ablation_protocol.sha256").read_text(
        encoding="ascii"
    ).strip()
    if actual_hash != semantic_hash or checksum != f"{semantic_hash}  semantic_ablation_protocol.json":
        raise ValueError("semantic-ablation summary refused a changed protocol")
    if semantic_protocol["parent_protocol_sha256"] != parent["protocol_sha256"]:
        raise ValueError("semantic-ablation protocol does not match V3.2 primary")

    manifest = json.loads((root / "results/v32/manifest.json").read_text(encoding="utf-8"))
    rows = [
        row
        for row in manifest.get("runs", [])
        if row.get("phase") == "semantic_ablation"
        and row.get("optimizer") == "llm_iterative"
    ]
    expected = {
        (condition, int(seed))
        for condition in semantic_protocol["conditions"]
        for seed in semantic_protocol["optimizer_seeds"]
    }
    row_by_key = {
        (row.get("condition"), int(row["optimizer_seed"])): row for row in rows
    }
    if set(row_by_key) != expected:
        raise ValueError(
            f"expected {len(expected)} semantic-ablation traces, found {len(row_by_key)}"
        )

    runs: list[dict[str, Any]] = []
    best_by_condition: dict[str, dict[int, float]] = {}
    incomplete_by_condition: dict[str, dict[int, float]] = {}
    conditions: dict[str, Any] = {}
    for condition in semantic_protocol["conditions"]:
        best_by_condition[condition] = {}
        incomplete_by_condition[condition] = {}
        for seed in semantic_protocol["optimizer_seeds"]:
            item = row_by_key[(condition, int(seed))]
            path = root / item["trace"]
            if sha256(path) != item["trace_sha256"]:
                raise ValueError(f"semantic-ablation trace hash mismatch: {item['trace']}")
            trace = read_trace(path)
            if len(trace.evaluated_candidates) != int(item["evaluated_candidates"]):
                raise ValueError(f"trace count mismatch: {item['trace']}")
            if trace.complete != bool(item["complete"]):
                raise ValueError(f"trace completion status mismatch: {item['trace']}")
            if (
                trace.budget_total_evaluations
                != int(semantic_protocol["total_unique_evaluations_per_run"])
                or trace.budget_seed_evaluations
                != int(semantic_protocol["shared_seed_program_count"])
                or trace.proposal_attempts
                > int(parent["budget"]["max_proposal_attempts_per_run"])
            ):
                raise ValueError(f"trace violated the frozen secondary budget: {item['trace']}")
            scores = [row.fitness for row in trace.evaluated_candidates]
            last_best = max(scores, default=None)
            if trace.complete and last_best is not None:
                best_by_condition[condition][int(seed)] = float(last_best)
            elif last_best is not None:
                incomplete_by_condition[condition][int(seed)] = float(last_best)
            runs.append(
                {
                    "condition": condition,
                    "optimizer_seed": int(seed),
                    "complete": trace.complete,
                    "evaluated_candidates": len(trace.evaluated_candidates),
                    "final_best_fitness": (
                        float(last_best) if trace.complete and last_best is not None else None
                    ),
                    "last_observed_best_fitness": (
                        float(last_best) if not trace.complete else None
                    ),
                    "proposal_attempts": trace.proposal_attempts,
                    "invalid_count": trace.invalid_count,
                    "duplicate_count": trace.duplicate_count,
                    "llm_calls": trace.llm_calls,
                    "llm_tokens": trace.llm_tokens,
                    "total_wall_time_ms": trace.total_wall_time_ms,
                }
            )
        values = list(best_by_condition[condition].values())
        conditions[condition] = {
            "final_best_fitness": _distribution(values),
            "per_seed": {str(seed): value for seed, value in best_by_condition[condition].items()},
            "incomplete_per_seed": {
                str(seed): value
                for seed, value in incomplete_by_condition[condition].items()
            },
            "complete_run_count": len(values),
        }

    semantic = best_by_condition["semantic_dsl"]
    anonymized = best_by_condition["anonymized_dsl"]
    paired = _paired_bootstrap(
        semantic,
        anonymized,
        seed=int(parent["primary_metrics"]["paired_bootstrap"]["seed"]),
        resamples=int(parent["primary_metrics"]["paired_bootstrap"]["resamples"]),
    )
    shared = set(semantic) & set(anonymized)
    paired["semantic_wins"] = sum(semantic[seed] > anonymized[seed] for seed in shared)
    paired["paired_runs"] = len(shared)
    interrupted_attempts = []
    partial_attempt_root = root / "results/v32/runs/semantic_ablation/partial_attempts"
    if partial_attempt_root.is_dir():
        for metadata_path in sorted(partial_attempt_root.glob("*/attempt_metadata.json")):
            interrupted_attempts.append(
                json.loads(metadata_path.read_text(encoding="utf-8"))
            )
    result = {
        "schema_version": 1,
        "protocol_sha256": semantic_hash,
        "parent_protocol_sha256": parent["protocol_sha256"],
        "optimizer": "llm_iterative",
        "optimizer_seeds": semantic_protocol["optimizer_seeds"],
        "conditions": conditions,
        "paired_difference": paired,
        "runs": runs,
        "interrupted_attempts": interrupted_attempts,
        "interpretation": "lexical-semantic ablation only; does not remove all pretrained knowledge",
    }
    output = root / "results/v32/summary/semantic_ablation.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return result


def sha256_bytes(value: bytes) -> str:
    import hashlib

    return hashlib.sha256(value).hexdigest()
