"""Check candidate structure without reading data or evaluating accuracy."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from bias_optimizer.v4.candidate.check import check_candidate_directory
from bias_optimizer.v4.candidate.loader import read_json
from bias_optimizer.v4.candidate.provenance import CandidateValidationError


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("candidate_directory", type=Path)
    parser.add_argument("--parent-state", type=Path)
    parser.add_argument("--protocol", type=Path)
    args = parser.parse_args()
    try:
        parent = read_json(args.parent_state) if args.parent_state else None
        result = check_candidate_directory(
            args.candidate_directory,
            parent_state=parent,
            protocol_path=args.protocol,
        )
    except CandidateValidationError as exc:
        result = {"status": "invalid", "validation_error": str(exc)}
    print(json.dumps(result, sort_keys=True, allow_nan=False))
    return 0 if result["status"] == "valid" else 1


if __name__ == "__main__":
    raise SystemExit(main())
