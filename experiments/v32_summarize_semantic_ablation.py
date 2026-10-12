"""Summarize paired V3.2 semantic-ablation runs."""

from __future__ import annotations

import argparse
from pathlib import Path

from bias_optimizer.optimizer_bench.runner import ROOT
from bias_optimizer.optimizer_bench.semantic_ablation_stats import (
    summarize_semantic_ablation,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    summary = summarize_semantic_ablation(args.root)
    paired = summary["paired_difference"]
    print(
        f"summarized {len(summary['runs'])} runs; "
        f"{paired['paired_runs']} complete paired seeds"
    )


if __name__ == "__main__":
    main()
