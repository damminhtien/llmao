"""Generate the V3.2 primary statistics and search-curve figure."""

from __future__ import annotations

from v32_generate_report import summarize_primary_artifacts

from bias_optimizer.optimizer_bench.runner import ROOT


def main() -> None:
    summary = summarize_primary_artifacts(ROOT)
    print(
        f"summarized {summary['complete_runs']}/{summary['run_count']} complete primary runs"
    )


if __name__ == "__main__":
    main()
