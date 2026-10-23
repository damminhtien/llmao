"""Replay historical structural validation without modifying pilot artifacts."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from bias_optimizer.v4.candidate.replay import replay_pilot


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--artifact-root", type=Path, default=ROOT)
    parser.add_argument(
        "--protocol", type=Path, default=ROOT / "results/v4/protocol.json"
    )
    args = parser.parse_args()
    try:
        from .v4_artifact_paths import resolve_v4_output_path
    except ImportError:
        from v4_artifact_paths import resolve_v4_output_path

    output = resolve_v4_output_path(args.output, repo_root=ROOT)
    report = replay_pilot(
        args.manifest,
        artifact_root=args.artifact_root,
        protocol_path=args.protocol,
    )
    with output.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")
    print(
        json.dumps(
            {
                key: value
                for key, value in report.items()
                if key
                not in {
                    "observations",
                    "expanded_representation_observations",
                }
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
