"""Run the required four-condition, one-seed, 40-candidate smoke benchmark."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from bias_optimizer.optimizer_bench.budget import SearchBudget
from bias_optimizer.optimizer_bench.runner import (
    OPTIMIZERS,
    ROOT,
    run_optimizer,
    sha256,
    verify_protocol,
)
from bias_optimizer.optimizer_bench.schema import SearchTrace
from bias_optimizer.optimizer_bench.trace import read_trace


def _verify_existing(seed: int) -> list[dict[str, object]]:
    manifest_path = ROOT / "results/v32/manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    rows = {
        row["optimizer"]: row
        for row in manifest.get("runs", [])
        if row.get("phase") == "smoke" and row.get("optimizer_seed") == seed
    }
    results = []
    for optimizer in OPTIMIZERS:
        row = rows.get(optimizer)
        if row is None:
            raise ValueError(f"missing smoke run for {optimizer}, seed {seed}")
        trace_path = ROOT / row["trace"]
        if sha256(trace_path) != row["trace_sha256"]:
            raise ValueError(f"smoke trace hash mismatch: {row['trace']}")
        trace = read_trace(trace_path)
        serialized = json.loads(trace_path.read_text(encoding="utf-8"))
        if trace.to_dict() != serialized:
            raise ValueError(f"smoke trace round trip mismatch: {row['trace']}")
        if (
            trace.optimizer != optimizer
            or trace.optimizer_seed != seed
            or not trace.complete
            or len(trace.evaluated_candidates) != 40
        ):
            raise ValueError(f"smoke trace failed its budget check: {row['trace']}")
        results.append(
            {
                "optimizer": optimizer,
                "seed": seed,
                "evaluated_candidates": len(trace.evaluated_candidates),
                "complete": trace.complete,
                "trace_round_trip_verified": True,
            }
        )
    return results


def _trace_round_trip_matches(trace: SearchTrace, trace_path: Path) -> bool:
    loaded = read_trace(trace_path)
    serialized = json.loads(trace_path.read_text(encoding="utf-8"))
    return loaded.to_dict() == serialized == trace.to_dict()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--verify-existing",
        action="store_true",
        help="verify saved smoke traces without running inference again",
    )
    args = parser.parse_args()
    protocol = verify_protocol()
    seed = protocol["budget"]["smoke_optimizer_seeds"][0]
    if args.verify_existing:
        summary = _verify_existing(seed)
        print(json.dumps(summary, indent=2))
        return
    budget = SearchBudget(
        total_evaluations=40, seed_evaluations=20, max_proposal_attempts=60
    )
    traces = []
    for optimizer in OPTIMIZERS:
        traces.append(
            run_optimizer(
                optimizer,
                seed,
                budget=budget,
                output_root=ROOT / "results/v32/runs/smoke",
                phase="smoke",
            )
        )
    summary = [
        {
            "optimizer": trace.optimizer,
            "seed": trace.optimizer_seed,
            "evaluated_candidates": len(trace.evaluated_candidates),
            "target_evaluations": trace.budget_total_evaluations,
            "complete": trace.complete,
            "trace_round_trip_verified": _trace_round_trip_matches(
                trace,
                ROOT
                / "results/v32/runs/smoke"
                / trace.optimizer
                / f"seed_{seed}"
                / "trace.json",
            ),
        }
        for trace in traces
    ]
    print(json.dumps(summary, indent=2))
    if any(
        not row["complete"]
        or row["evaluated_candidates"] != 40
        or not row["trace_round_trip_verified"]
        for row in summary
    ):
        raise SystemExit(
            "V3.2 smoke benchmark did not complete all 40 evaluations per optimizer"
        )


if __name__ == "__main__":
    main()
