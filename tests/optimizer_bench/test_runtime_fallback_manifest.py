from __future__ import annotations

import json
from pathlib import Path

from bias_optimizer.optimizer_bench.artifacts import (
    finalize_primary_manifest,
    register_run,
)
from bias_optimizer.optimizer_bench.runner import verify_protocol
from bias_optimizer.optimizer_bench.schema import SearchTrace


def test_primary_runtime_fallback_records_matched_and_excluded_runs(tmp_path: Path) -> None:
    protocol = verify_protocol()
    directory = tmp_path / "results/v32"
    directory.mkdir(parents=True)
    source_protocol = Path("results/v32/protocol.json")
    (directory / "protocol.json").write_bytes(source_protocol.read_bytes())
    manifest_path = directory / "manifest.json"
    optimizers = protocol["primary_optimizers"]
    selected = (101, 202)
    runs = [
        {
            "phase": "primary",
            "optimizer": optimizer,
            "optimizer_seed": seed,
            "requested_evaluations": 200,
            "evaluated_candidates": 200,
            "complete": True,
        }
        for optimizer in optimizers
        for seed in selected
    ]
    runs.append(
        {
            "phase": "primary",
            "optimizer": "genetic_programming",
            "optimizer_seed": 303,
            "requested_evaluations": 200,
            "evaluated_candidates": 200,
            "complete": True,
        }
    )
    manifest_path.write_text(
        json.dumps(
            {
                "protocol": {"sha256": protocol["protocol_sha256"]},
                "runs": runs,
                "primary_execution": {
                    "protocol_seeds": list(protocol["budget"]["optimizer_seeds"]),
                    "matched_analysis_seeds": list(selected),
                    "runtime_fallback": True,
                },
            }
        ),
        encoding="utf-8",
    )

    status = finalize_primary_manifest(manifest_path)
    updated = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert status == "primary_finished_with_runtime_fallback"
    assert updated["primary_execution"]["matched_analysis_seeds"] == [101, 202]
    retained = next(
        row
        for row in updated["primary_execution"]["excluded_run_statuses"]
        if row["optimizer"] == "genetic_programming" and row["optimizer_seed"] == 303
    )
    assert retained["status"] == "retained_outside_matched_analysis"
    assert retained["complete"] is True
    assert retained["evaluated_candidates"] == 200


def test_semantic_conditions_are_distinct_and_preserve_primary_status(
    tmp_path: Path,
) -> None:
    protocol = verify_protocol()
    directory = tmp_path / "results/v32"
    directory.mkdir(parents=True)
    source_protocol = Path("results/v32/protocol.json")
    (directory / "protocol.json").write_bytes(source_protocol.read_bytes())
    manifest_path = directory / "manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "protocol": {"sha256": protocol["protocol_sha256"]},
                "status": "primary_finished_with_runtime_fallback",
                "runs": [],
            }
        ),
        encoding="utf-8",
    )
    trace = SearchTrace(
        optimizer="llm_iterative",
        optimizer_seed=101,
        evaluated_candidates=(),
        proposal_attempts=0,
        valid_proposal_count=0,
        invalid_count=0,
        duplicate_count=0,
        rejected_by_constraint_count=0,
        llm_calls=0,
        llm_tokens=0,
        proposal_time_ms=0.0,
        evaluation_time_ms=0.0,
        total_wall_time_ms=0.0,
        complete=False,
    )
    trace_dir = tmp_path / "results/v32/runs/semantic_ablation"
    trace_dir.mkdir(parents=True)
    items = []
    for condition in ("semantic_dsl", "anonymized_dsl"):
        trace_path = trace_dir / f"{condition}.json"
        trace_path.write_text("{}\n", encoding="utf-8")
        items.append(
            register_run(
                trace,
                trace_path,
                phase="semantic_ablation",
                condition=condition,
                manifest_path=manifest_path,
            )
        )

    updated = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert {item["condition"] for item in items} == {
        "semantic_dsl",
        "anonymized_dsl",
    }
    assert len(updated["runs"]) == 2
    assert updated["status"] == "primary_finished_with_runtime_fallback"
