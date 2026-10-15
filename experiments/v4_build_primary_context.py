"""Build evaluator-owned lineage context against the finalized V4 protocol."""

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
from bias_optimizer.v4.discovery import load_finalized_protocol


def _write_new(path: Path, payload: dict) -> None:
    path = path.resolve(strict=False)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        json.dump(payload, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("candidate_directory", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--parent-lineage", type=Path)
    parser.add_argument("--parent-candidate-id")
    parser.add_argument("--generation", type=int, default=0)
    parser.add_argument("--eve-agent-id")
    parser.add_argument("--guidance-hash")
    parser.add_argument("--lineage-state-output", type=Path, required=True)
    args = parser.parse_args()

    protocol, _ = load_finalized_protocol(args.protocol)
    _ = protocol
    lineage = read_json(args.parent_lineage) if args.parent_lineage else []
    if not isinstance(lineage, list):
        raise SystemExit("parent lineage JSON must contain a list")
    candidate = args.candidate_directory.resolve(strict=True)
    output = args.output.resolve(strict=False)
    lineage_output = args.lineage_state_output.resolve(strict=False)
    if output.parent == candidate or candidate in output.parents:
        raise SystemExit("evaluation context must remain outside the candidate directory")
    if lineage_output.parent == candidate or candidate in lineage_output.parents:
        raise SystemExit("lineage state must remain outside the candidate directory")
    context = build_candidate_context(
        candidate,
        parent_lineage=lineage,
        parent_candidate_id=args.parent_candidate_id,
        generation=args.generation,
        eve_agent_id=args.eve_agent_id,
        guidance_hash=args.guidance_hash,
        protocol_path=args.protocol,
    )
    state = build_candidate_lineage_state(candidate, context=context)
    _write_new(output, context)
    _write_new(lineage_output, state)
    print(json.dumps({"candidate_id": context["candidate_id"], "context": str(output)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
