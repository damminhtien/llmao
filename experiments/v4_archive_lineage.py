"""Verify pilot artifacts and write a language lineage archive and graph."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from bias_optimizer.v4.candidate.replay import replay_pilot
from bias_optimizer.v4.lineage import build_lineage_archive, lineage_mermaid

try:
    from .v4_artifact_paths import resolve_v4_output_path
except ImportError:
    from v4_artifact_paths import resolve_v4_output_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, action="append", required=True)
    parser.add_argument("--artifact-root", type=Path, default=ROOT)
    parser.add_argument(
        "--protocol", type=Path, default=ROOT / "results/v4/protocol.json"
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--graph", type=Path, required=True)
    args = parser.parse_args()
    output = resolve_v4_output_path(args.output, repo_root=ROOT)
    graph = resolve_v4_output_path(args.graph, repo_root=ROOT)
    if output == graph or output.exists() or graph.exists():
        raise SystemExit("archive and graph require distinct new output paths")
    replays = [
        replay_pilot(
            path, artifact_root=args.artifact_root, protocol_path=args.protocol
        )
        for path in args.manifest
    ]
    archive = build_lineage_archive(replays)
    with output.open("x", encoding="utf-8") as stream:
        json.dump(archive, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")
    with graph.open("x", encoding="utf-8") as stream:
        stream.write(lineage_mermaid(archive))
    print(
        json.dumps(
            {
                "languages": len(archive["languages"]),
                "edges": len(archive["edges"]),
                "macro_behaviors": len(archive["primitives"]),
                "observations": len(archive["observations"]),
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
