"""Load data-only candidate files against evaluator-managed provenance."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from bias_optimizer.dsl.ast import Expr
from bias_optimizer.v4.candidate.provenance import (
    CandidateProvenance,
    CandidateValidationError,
)
from bias_optimizer.v4.candidate.schema import CandidateV4, load_macro_language
from bias_optimizer.v4.language.base_language import G0_LANGUAGE, LanguageManifest
from bias_optimizer.v4.language.validator import MacroLanguage


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise CandidateValidationError(f"duplicate JSON key: {key!r}")
        result[key] = value
    return result


def read_json(path: Path) -> Any:
    """Read strict JSON, rejecting duplicate object keys."""
    try:
        return json.loads(
            path.read_text(encoding="utf-8"), object_pairs_hook=_reject_duplicate_keys
        )
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise CandidateValidationError(f"cannot read JSON file {path.name!r}: {exc}") from exc


def load_language_lineage(
    snapshots: Sequence[Mapping[str, Any]],
) -> LanguageManifest | MacroLanguage:
    """Validate ordered language snapshots from G0 to the candidate's parent."""
    if not isinstance(snapshots, Sequence) or isinstance(snapshots, (str, bytes)):
        raise CandidateValidationError("parent_language_lineage must be a list")
    parent = G0_LANGUAGE
    for index, snapshot in enumerate(snapshots):
        if not isinstance(snapshot, Mapping):
            raise CandidateValidationError(
                f"parent language snapshot {index} must be an object"
            )
        try:
            parent = load_macro_language(snapshot, parent)
        except CandidateValidationError as exc:
            raise CandidateValidationError(
                f"invalid parent language snapshot {index}: {exc}"
            ) from exc
    return parent


def load_candidate_directory(
    candidate_directory: Path,
    *,
    context: Mapping[str, Any],
) -> CandidateV4:
    """Load language/program JSON plus protected, evaluator-managed context.

    Candidate directories contain only ``language.json`` and ``program.json``.
    Provenance and parent-language history come from a separate trusted context
    file owned by the evaluator/orchestrator.
    """
    expected_context = {
        "schema_version",
        "candidate_id",
        "provenance",
        "parent_language_lineage",
    }
    if not isinstance(context, Mapping) or set(context) != expected_context:
        raise CandidateValidationError("evaluation context has an invalid shape")
    if type(context["schema_version"]) is not int or context["schema_version"] != 1:
        raise CandidateValidationError("unsupported evaluation context version")
    if not isinstance(context["candidate_id"], str):
        raise CandidateValidationError("context candidate_id must be a string")
    lineage = context["parent_language_lineage"]
    if not isinstance(lineage, list):
        raise CandidateValidationError("parent_language_lineage must be a list")
    parent_language = load_language_lineage(lineage)

    directory = Path(candidate_directory).resolve(strict=True)
    if not directory.is_dir():
        raise CandidateValidationError("candidate path must be a directory")
    expected_files = {"language.json", "program.json"}
    entries = {path.name for path in directory.iterdir()}
    if entries != expected_files:
        unexpected = sorted(entries - expected_files)
        missing = sorted(expected_files - entries)
        raise CandidateValidationError(
            f"candidate directory must contain only language.json and program.json; "
            f"unexpected={unexpected}, missing={missing}"
        )
    language_path = directory / "language.json"
    program_path = directory / "program.json"
    for path in (language_path, program_path):
        if path.is_symlink() or not path.is_file():
            raise CandidateValidationError(
                f"candidate must contain a regular {path.name} file"
            )

    language_data = read_json(language_path)
    program_data = read_json(program_path)
    language = load_macro_language(language_data, parent_language)
    try:
        program = Expr.from_dict(program_data)
    except (TypeError, ValueError, KeyError) as exc:
        raise CandidateValidationError(f"invalid candidate program AST: {exc}") from exc
    provenance = CandidateProvenance.from_dict(context["provenance"])
    if language.introduced_macros != provenance.invented_primitives:
        raise CandidateValidationError(
            "introduced macros do not match evaluator-managed provenance"
        )
    return CandidateV4(
        candidate_id=context["candidate_id"],
        language=language,
        program=program,
        provenance=provenance,
    )
