"""Run one frozen V3.2 optimizer condition and seed."""

from __future__ import annotations

import argparse
import json

from bias_optimizer.optimizer_bench.budget import SearchBudget
from bias_optimizer.optimizer_bench.runner import (
    OPTIMIZERS,
    ROOT,
    run_optimizer,
    verify_protocol,
)


def main() -> None:
    protocol = verify_protocol()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("optimizer", choices=OPTIMIZERS)
    parser.add_argument("seed", type=int, choices=protocol["budget"]["optimizer_seeds"])
    parser.add_argument("--smoke", action="store_true")
    args = parser.parse_args()
    if args.smoke:
        budget = SearchBudget(
            total_evaluations=40, seed_evaluations=20, max_proposal_attempts=60
        )
        output_root = ROOT / "results/v32/runs/smoke"
        phase = "smoke"
    else:
        budget = SearchBudget()
        output_root = ROOT / "results/v32/runs/primary"
        phase = "primary"
    trace = run_optimizer(
        args.optimizer,
        args.seed,
        budget=budget,
        output_root=output_root,
        phase=phase,
    )
    print(
        json.dumps(
            {
                "optimizer": trace.optimizer,
                "seed": trace.optimizer_seed,
                "evaluated_candidates": len(trace.evaluated_candidates),
                "target_evaluations": trace.budget_total_evaluations,
                "complete": trace.complete,
                "termination_reason": trace.termination_reason,
                "trace": str(
                    output_root
                    / trace.optimizer
                    / f"seed_{trace.optimizer_seed}"
                    / "trace.json"
                ),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
