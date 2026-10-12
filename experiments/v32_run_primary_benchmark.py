"""Run the frozen V3.2 primary benchmark for selected protocol seeds."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from bias_optimizer.optimizer_bench.artifacts import finalize_primary_manifest
from bias_optimizer.optimizer_bench.runner import (
    OPTIMIZERS,
    ROOT,
    run_optimizer,
    verify_protocol,
)


def _finished_runs(manifest_path: Path) -> dict[tuple[str, int], bool]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    return {
        (row["optimizer"], row["optimizer_seed"]): bool(row["complete"])
        for row in manifest.get("runs", [])
        if row.get("phase") == "primary"
        and row.get("requested_evaluations") == 200
        and row.get("trace")
    }


def _freeze_execution_scope(
    manifest_path: Path, protocol_seeds: tuple[int, ...], selected_seeds: tuple[int, ...]
) -> None:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["primary_execution"] = {
        "protocol_seeds": list(protocol_seeds),
        "matched_analysis_seeds": list(selected_seeds),
        "runtime_fallback": len(selected_seeds) < len(protocol_seeds),
        "runtime_fallback_reason": (
            "Local qwen3.5:35b-mlx proposal throughput made the full five-seed run "
            f"prohibitive; the matched seed subset {selected_seeds} is used."
            if len(selected_seeds) < len(protocol_seeds)
            else None
        ),
    }
    temporary = manifest_path.with_suffix(".json.tmp")
    temporary.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(manifest_path)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--seeds",
        type=int,
        nargs="+",
        help="protocol optimizer seeds to execute (defaults to all five)",
    )
    args = parser.parse_args()
    protocol = verify_protocol()
    protocol_seeds = tuple(int(seed) for seed in protocol["budget"]["optimizer_seeds"])
    selected_seeds = tuple(args.seeds) if args.seeds else protocol_seeds
    if not selected_seeds or len(set(selected_seeds)) != len(selected_seeds):
        parser.error("--seeds must contain distinct protocol seed values")
    if any(seed not in protocol_seeds for seed in selected_seeds):
        parser.error(f"--seeds must be selected from {protocol_seeds}")
    manifest_path = ROOT / "results/v32/manifest.json"
    _freeze_execution_scope(manifest_path, protocol_seeds, selected_seeds)
    finished = _finished_runs(manifest_path)
    results = []
    for optimizer in OPTIMIZERS:
        for seed in selected_seeds:
            if (optimizer, seed) in finished:
                results.append(
                    {
                        "optimizer": optimizer,
                        "seed": seed,
                        "status": (
                            "already_complete"
                            if finished[(optimizer, seed)]
                            else "already_incomplete"
                        ),
                    }
                )
                continue
            trace = run_optimizer(
                optimizer,
                seed,
                output_root=ROOT / "results/v32/runs/primary",
                phase="primary",
            )
            results.append(
                {
                    "optimizer": optimizer,
                    "seed": seed,
                    "status": "complete" if trace.complete else "incomplete",
                    "evaluated_candidates": len(trace.evaluated_candidates),
                    "proposal_attempts": trace.proposal_attempts,
                    "termination_reason": trace.termination_reason,
                }
            )
    finalize_primary_manifest(manifest_path)
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
