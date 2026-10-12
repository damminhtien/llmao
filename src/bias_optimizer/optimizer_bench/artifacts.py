"""Protocol-bound run manifest and trace artifact helpers."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

from bias_optimizer.optimizer_bench.schema import SearchTrace


def finalize_primary_manifest(manifest_path: Path) -> str:
    from bias_optimizer.optimizer_bench.runner import sha256, verify_protocol

    verify_protocol()
    manifest_path = Path(manifest_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest["protocol"]["sha256"] != sha256(manifest_path.parent / "protocol.json"):
        raise ValueError("cannot finalize a manifest against a changed protocol")
    workspace_root = manifest_path.parent.parent.parent
    for item in manifest.get("runs", []):
        if item.get("phase") != "primary" or not item.get("trace"):
            continue
        trace_path = workspace_root / item["trace"]
        trace_payload = json.loads(trace_path.read_text(encoding="utf-8"))
        evaluations = trace_payload.get("evaluated_candidates", [])
        elapsed_values = [
            row.get("metadata", {}).get("oracle_elapsed_ms")
            for row in evaluations
            if isinstance(row.get("metadata"), dict)
        ]
        if len(elapsed_values) != len(evaluations) or not all(
            isinstance(value, (int, float)) and math.isfinite(value)
            for value in elapsed_values
        ):
            raise ValueError(f"missing oracle timing data in {item['trace']}")
        measured_evaluation_time = float(sum(elapsed_values))
        if not math.isclose(
            trace_payload.get("evaluation_time_ms", 0.0),
            measured_evaluation_time,
            rel_tol=0.0,
            abs_tol=1e-9,
        ):
            trace_payload["evaluation_time_ms"] = measured_evaluation_time
            temporary_trace = trace_path.with_suffix(trace_path.suffix + ".tmp")
            temporary_trace.write_text(
                json.dumps(trace_payload, ensure_ascii=False, indent=2, sort_keys=True)
                + "\n",
                encoding="utf-8",
            )
            temporary_trace.replace(trace_path)
            item["trace_sha256"] = sha256(trace_path)
    protocol = verify_protocol()
    execution = manifest.get("primary_execution", {})
    protocol_seeds = tuple(
        int(seed) for seed in protocol["budget"]["optimizer_seeds"]
    )
    selected_seeds = tuple(
        int(seed)
        for seed in execution.get("matched_analysis_seeds", protocol_seeds)
    )
    optimizers = tuple(protocol["primary_optimizers"])
    primary = [
        row for row in manifest.get("runs", []) if row.get("phase") == "primary"
    ]
    included = [
        row
        for row in primary
        if int(row["optimizer_seed"]) in selected_seeds
        and row["optimizer"] in optimizers
    ]
    expected_keys = {
        (optimizer, seed) for optimizer in optimizers for seed in selected_seeds
    }
    included_by_key = {
        (row["optimizer"], int(row["optimizer_seed"])): row for row in included
    }
    primary_keys = {
        (row["optimizer"], int(row["optimizer_seed"])) for row in primary
    }
    manifest["primary_execution"] = {
        **execution,
        "protocol_seeds": list(protocol_seeds),
        "matched_analysis_seeds": list(selected_seeds),
        "excluded_run_statuses": [
            {
                "optimizer": optimizer,
                "optimizer_seed": seed,
                "status": (
                    "retained_outside_matched_analysis"
                    if (optimizer, seed) in primary_keys
                    else "not_run_under_runtime_fallback"
                ),
                "evaluated_candidates": next(
                    (
                        int(row["evaluated_candidates"])
                        for row in primary
                        if row["optimizer"] == optimizer
                        and int(row["optimizer_seed"]) == seed
                    ),
                    0,
                ),
                "complete": next(
                    (
                        bool(row["complete"])
                        for row in primary
                        if row["optimizer"] == optimizer
                        and int(row["optimizer_seed"]) == seed
                    ),
                    False,
                ),
            }
            for optimizer in optimizers
            for seed in protocol_seeds
            if seed not in selected_seeds
        ],
    }
    if not expected_keys.issubset(included_by_key):
        status = (
            "primary_in_progress"
            if primary
            else manifest.get("status", "protocol_frozen")
        )
    elif len(selected_seeds) < len(protocol_seeds):
        status = "primary_finished_with_runtime_fallback"
    elif all(
        included_by_key[key]["complete"]
        and included_by_key[key]["evaluated_candidates"] == 200
        for key in expected_keys
    ):
        status = "primary_complete"
    else:
        status = "primary_finished_with_incomplete_runs"
    manifest["status"] = status
    temporary = manifest_path.with_suffix(".json.tmp")
    temporary.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(manifest_path)
    return status


def register_run(
    trace: SearchTrace,
    trace_path: Path,
    *,
    phase: str,
    manifest_path: Path,
    condition: str | None = None,
) -> dict[str, Any]:
    from bias_optimizer.optimizer_bench.runner import sha256, verify_protocol

    verify_protocol()
    if phase not in {"smoke", "primary", "semantic_ablation", "characterization"}:
        raise ValueError("phase is not a supported V3.2 artifact phase")
    if phase == "semantic_ablation":
        if condition not in {"semantic_dsl", "anonymized_dsl"}:
            raise ValueError("semantic-ablation runs require a supported condition")
    elif condition is not None:
        raise ValueError("condition is only valid for semantic-ablation runs")
    manifest_path = Path(manifest_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest["protocol"]["sha256"] != sha256(manifest_path.parent / "protocol.json"):
        raise ValueError("cannot register a run against a changed protocol")
    relative = (
        Path(trace_path)
        .resolve()
        .relative_to(manifest_path.parent.parent.parent.resolve())
    )
    item = {
        "phase": phase,
        "optimizer": trace.optimizer,
        "optimizer_seed": trace.optimizer_seed,
        "evaluated_candidates": len(trace.evaluated_candidates),
        "requested_evaluations": trace.budget_total_evaluations,
        "complete": trace.complete,
        "trace": str(relative),
        "trace_sha256": sha256(Path(trace_path)),
        "protocol_sha256": manifest["protocol"]["sha256"],
    }
    if condition is not None:
        item["condition"] = condition
    runs = [
        row
        for row in manifest.get("runs", [])
        if not (
            row.get("phase") == phase
            and row.get("optimizer") == trace.optimizer
            and row.get("optimizer_seed") == trace.optimizer_seed
            and row.get("requested_evaluations") == trace.budget_total_evaluations
            and row.get("condition") == condition
        )
    ]
    runs.append(item)
    runs.sort(
        key=lambda row: (
            row["phase"],
            row["optimizer"],
            row.get("condition", ""),
            row["optimizer_seed"],
        )
    )
    manifest["runs"] = runs
    if phase in {"primary", "smoke"}:
        primary = [row for row in runs if row["phase"] == "primary"]
        if len(primary) == 20 and all(
            row["complete"] and row["evaluated_candidates"] == 200 for row in primary
        ):
            manifest["status"] = "primary_complete"
        elif len(primary) == 20:
            manifest["status"] = "primary_finished_with_incomplete_runs"
        elif primary:
            manifest["status"] = "primary_in_progress"
        elif any(row["phase"] == "smoke" for row in runs):
            manifest["status"] = "smoke_complete"
    temporary = manifest_path.with_suffix(".json.tmp")
    temporary.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(manifest_path)
    return item
