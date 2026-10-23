"""Export the common V4 starting ASTs from the frozen V3.2 Git protocol."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from bias_optimizer.dsl.ast import Expr
from bias_optimizer.v4.language import G0_LANGUAGE, GH_LANGUAGE, expand_candidate
from bias_optimizer.v4.language.validator import extend_macro_language

SOURCE_COMMIT = "85beeaff62791946989b3163cd67fbaed7e7c108"
SOURCE_PATH = "results/v32/protocol.json"


def build_manifest(protocol_bytes: bytes) -> dict:
    """Validate ASTs without loading examples, fitting learners, or reading scores."""
    protocol = json.loads(protocol_bytes)
    seeds = protocol["frozen_search_space"]["seed_programs"]
    if len(seeds) != 20:
        raise ValueError("common starting set requires exactly twenty programs")
    language = extend_macro_language(G0_LANGUAGE, [])
    human_signatures = {
        primitive.name: primitive.to_dict() for primitive in GH_LANGUAGE.primitives
    }
    for primitive in G0_LANGUAGE.primitives:
        if human_signatures.get(primitive.name) != primitive.to_dict():
            raise ValueError("G0 and GH must have identical shared primitive contracts")
    programs = []
    seen = set()
    for index, seed in enumerate(seeds):
        program = Expr.from_dict(seed["bias"]["program"])
        digest = hashlib.sha256(program.to_json().encode()).hexdigest()
        if digest != seed["ast_sha256"]:
            raise ValueError("historical seed identity differs from its canonical AST")
        if digest in seen:
            raise ValueError("common starting programs must have distinct ASTs")
        seen.add(digest)
        expansion = expand_candidate(program, language)
        if not set(expansion.used_primitives) <= human_signatures.keys():
            raise ValueError("common starting program is unavailable in GH")
        programs.append(
            {
                "index": index,
                "historical_candidate_id": seed["candidate_id"],
                "ast_sha256": digest,
                "program": program.to_dict(),
                "feature_dimension": expansion.info.dimension,
                "expanded_depth": expansion.info.depth,
                "expanded_nodes": expansion.info.node_count,
                "used_primitives": list(expansion.used_primitives),
            }
        )
    return {
        "schema_version": 1,
        "purpose": "common initial ASTs for fresh V4 searches; no scores or history",
        "source": {
            "commit": SOURCE_COMMIT,
            "path": SOURCE_PATH,
            "sha256": hashlib.sha256(protocol_bytes).hexdigest(),
        },
        "language_sha256": {"G0": G0_LANGUAGE.sha256, "GH": GH_LANGUAGE.sha256},
        "limits": language.limits.to_dict(),
        "program_count": len(programs),
        "order": "original V3.2 protocol order",
        "programs": programs,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    try:
        from .v4_artifact_paths import resolve_repository_output_path
    except ImportError:
        from v4_artifact_paths import resolve_repository_output_path

    output = resolve_repository_output_path(args.output, repo_root=ROOT)
    if output != ROOT / "configs/v4/V4_INITIAL_PROGRAMS.json":
        raise ValueError("V4 initial programs must use the canonical repository path")
    digest_path = output.with_suffix(".sha256")
    if output.exists() or digest_path.exists():
        raise FileExistsError("initial-program manifest and digest must be new files")
    source = subprocess.check_output(
        ["git", "show", f"{SOURCE_COMMIT}:{SOURCE_PATH}"], cwd=ROOT
    )
    manifest = build_manifest(source)
    content = (
        json.dumps(manifest, indent=2, sort_keys=True, allow_nan=False) + "\n"
    ).encode()
    digest = hashlib.sha256(content).hexdigest()
    with output.open("xb") as stream:
        stream.write(content)
    with digest_path.open("x") as stream:
        stream.write(digest + "\n")
    print(
        json.dumps({"program_count": 20, "sha256": digest, "output": str(output)})
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
