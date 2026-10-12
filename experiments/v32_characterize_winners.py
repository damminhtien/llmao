"""Freeze V3.2 winner artifacts and run the reduced post-search V3.1 panel."""

from __future__ import annotations

import argparse
from pathlib import Path

from bias_optimizer.optimizer_bench.runner import ROOT
from bias_optimizer.optimizer_bench.winner_characterization import (
    characterize_winners,
    freeze_characterization_protocol,
    freeze_winners,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--freeze-winners", action="store_true")
    group.add_argument("--freeze-protocol", action="store_true")
    group.add_argument("--run", action="store_true")
    args = parser.parse_args()
    if args.freeze_winners:
        print(freeze_winners(args.root))
    elif args.freeze_protocol:
        print(freeze_characterization_protocol(args.root))
    else:
        print(characterize_winners(args.root))


if __name__ == "__main__":
    main()
