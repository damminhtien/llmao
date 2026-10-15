"""Build evaluator-managed provenance for a data-only V4 candidate directory."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from bias_optimizer.v4.candidate.context import (
    build_candidate_context,
    build_candidate_lineage_state,
)
from bias_optimizer.v4.candidate.loader import read_json


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("candidate_directory", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--parent-lineage", type=Path)
    parser.add_argument("--parent-candidate-id")
    parser.add_argument("--generation", type=int, default=0)
    parser.add_argument("--eve-agent-id")
    parser.add_argument("--guidance-hash")
    parser.add_argument("--protocol", type=Path)
    parser.add_argument("--lineage-state-output", type=Path)
    return parser


def main() -> int:
    args = _parser().parse_args()
    lineage = read_json(args.parent_lineage) if args.parent_lineage else []
    if not isinstance(lineage, list):
        raise SystemExit("parent lineage JSON must contain a list")
    context = build_candidate_context(
        args.candidate_directory,
        parent_lineage=lineage,
        parent_candidate_id=args.parent_candidate_id,
        generation=args.generation,
        eve_agent_id=args.eve_agent_id,
        guidance_hash=args.guidance_hash,
        protocol_path=args.protocol,
    )
    output = args.output.resolve(strict=False)
    if output.is_relative_to(args.candidate_directory.resolve(strict=True)):
        raise SystemExit(
            "evaluation context output must be outside the candidate directory"
        )
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8") as stream:
        json.dump(context, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")
    if args.lineage_state_output:
        state_output = args.lineage_state_output.resolve(strict=False)
        if state_output.is_relative_to(args.candidate_directory.resolve(strict=True)):
            raise SystemExit(
                "lineage state output must be outside the candidate directory"
            )
        state_output.parent.mkdir(parents=True, exist_ok=True)
        state = build_candidate_lineage_state(args.candidate_directory, context=context)
        with state_output.open("x", encoding="utf-8") as stream:
            json.dump(state, stream, indent=2, sort_keys=True, allow_nan=False)
            stream.write("\n")
    print(json.dumps({"candidate_id": context["candidate_id"], "context": str(output)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
