"""Read-only structural feedback for candidate authors; no dataset access."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from bias_optimizer.v4.candidate.context import build_candidate_context
from bias_optimizer.v4.candidate.loader import (
    load_candidate_directory,
    load_language_lineage,
)
from bias_optimizer.v4.candidate.provenance import CandidateValidationError


def validate_lineage_state(state: Mapping[str, Any]) -> None:
    """Check the evaluator-owned parent snapshot before using its provenance."""
    expected = {
        "schema_version",
        "candidate_id",
        "generation",
        "language_hash",
        "language_lineage",
    }
    if not isinstance(state, Mapping) or set(state) != expected:
        raise CandidateValidationError("lineage state has an invalid shape")
    if type(state["schema_version"]) is not int or state["schema_version"] != 1:
        raise CandidateValidationError("unsupported lineage state version")
    generation = state["generation"]
    if type(generation) is not int or generation < 0:
        raise CandidateValidationError("lineage generation must be non-negative")
    identity = state["candidate_id"]
    if not isinstance(identity, str) or not identity or identity.strip() != identity:
        raise CandidateValidationError("lineage candidate identity is invalid")
    if "/" in identity or "\\" in identity:
        raise CandidateValidationError(
            "lineage candidate identity contains a separator"
        )
    lineage = state["language_lineage"]
    if not isinstance(lineage, list) or len(lineage) != generation + 1:
        raise CandidateValidationError("lineage length does not match generation")
    language = load_language_lineage(lineage)
    if language.sha256 != state["language_hash"]:
        raise CandidateValidationError("lineage hash does not match snapshots")


def check_candidate_directory(
    directory: Path,
    *,
    parent_state: Mapping[str, Any] | None = None,
    protocol_path: Path | None = None,
) -> dict[str, Any]:
    """Return structural identities and limits, or a validation error.

    This invokes the same candidate validation as the evaluator. It neither
    writes repairs nor computes features, trains a learner, or reads examples.
    Parent state must come from the evaluator; this check does not authenticate
    an author-supplied state as an accepted ancestor.
    """
    try:
        if parent_state is not None:
            validate_lineage_state(parent_state)
        context = build_candidate_context(
            directory,
            parent_lineage=(parent_state["language_lineage"] if parent_state else []),
            parent_candidate_id=(
                parent_state["candidate_id"] if parent_state else None
            ),
            generation=(parent_state["generation"] + 1 if parent_state else 0),
            protocol_path=protocol_path,
        )
        candidate = load_candidate_directory(directory, context=context)
    except (ValueError, TypeError, KeyError, OSError) as exc:
        return {"status": "invalid", "validation_error": str(exc)}
    expansion = candidate.expansion
    used = set(expansion.used_macros)
    inherited = set(candidate.language.macro_map) - set(
        candidate.language.introduced_macros
    )
    return {
        "status": "valid",
        "candidate_id": candidate.candidate_id,
        "language_hash": candidate.language_hash,
        "program_hash": candidate.program_hash,
        "expanded_program_hash": candidate.expanded_program_hash,
        "expanded_depth": expansion.info.depth,
        "expanded_node_count": expansion.info.node_count,
        "feature_dimension": expansion.info.dimension,
        "introduced_macros": list(candidate.language.introduced_macros),
        "used_macros": list(expansion.used_macros),
        "unused_inherited_macros": sorted(inherited - used),
        "canonical_macro_order": sorted(candidate.language.macro_map),
    }
