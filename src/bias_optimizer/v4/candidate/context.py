"""Build trusted provenance context for data-only V4 candidate files."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from bias_optimizer.dsl.ast import Expr
from bias_optimizer.v4.candidate.loader import load_language_lineage, read_json
from bias_optimizer.v4.candidate.provenance import ModelBackendMetadata
from bias_optimizer.v4.candidate.schema import CandidateV4, load_macro_language

ROOT = Path(__file__).resolve().parents[4]


def build_candidate_context(
    candidate_directory: Path,
    *,
    parent_lineage: list[dict[str, Any]] | None = None,
    parent_candidate_id: str | None = None,
    generation: int = 0,
    eve_agent_id: str | None = None,
    guidance_hash: str | None = None,
    protocol_path: Path | None = None,
) -> dict[str, Any]:
    """Validate candidate JSON and attach metadata controlled by the evaluator."""
    if type(generation) is not int or generation < 0:
        raise ValueError("generation must be a non-negative integer")
    directory = Path(candidate_directory).resolve(strict=True)
    if not directory.is_dir():
        raise ValueError("candidate path must be a directory")
    expected_files = {"language.json", "program.json"}
    if {path.name for path in directory.iterdir()} != expected_files:
        raise ValueError(
            "candidate directory must contain only language.json and program.json"
        )
    for path in (directory / "language.json", directory / "program.json"):
        if path.is_symlink() or not path.is_file():
            raise ValueError(f"candidate must contain a regular {path.name} file")

    lineage = parent_lineage or []
    parent_language = load_language_lineage(lineage)
    language = load_macro_language(
        read_json(directory / "language.json"), parent_language
    )
    program = Expr.from_dict(read_json(directory / "program.json"))
    protocol_file = protocol_path or ROOT / "results/v4/protocol.json"
    protocol = json.loads(protocol_file.read_text(encoding="utf-8"))
    model = protocol["primary_design"]["exact_cli_model_identifier"]
    reasoning = protocol["primary_design"]["requested_reasoning_effort"]
    backend = protocol["candidate_boundary"]["codex_driver"]
    seed = protocol["evaluator_basis"]["training_subset_seed"]

    identity = hashlib.sha256(
        f"{language.sha256}\0{program.to_json()}".encode()
    ).hexdigest()
    candidate = CandidateV4.create(
        candidate_id=f"candidate-{identity[:20]}",
        language=language,
        program=program,
        parent_candidate_id=parent_candidate_id,
        invented_primitives=language.introduced_macros,
        eve_agent_id=eve_agent_id,
        guidance_hash=guidance_hash,
        generation=generation,
        model_backend=ModelBackendMetadata(
            model_identifier=model,
            backend=backend,
            reasoning_effort=reasoning,
        ),
        evaluation_seed=seed,
    )
    return {
        "schema_version": 1,
        "candidate_id": candidate.candidate_id,
        "provenance": candidate.provenance.to_dict(),
        "parent_language_lineage": lineage,
    }


def build_candidate_lineage_state(
    candidate_directory: Path,
    *,
    context: dict[str, Any],
) -> dict[str, Any]:
    """Return evaluator-owned lineage state for a validated candidate context."""
    expected = {
        "schema_version",
        "candidate_id",
        "provenance",
        "parent_language_lineage",
    }
    if not isinstance(context, dict) or set(context) != expected:
        raise ValueError("evaluation context has an invalid shape")
    if type(context["schema_version"]) is not int or context["schema_version"] != 1:
        raise ValueError("unsupported evaluation context version")
    provenance = context["provenance"]
    lineage = context["parent_language_lineage"]
    if not isinstance(provenance, dict) or not isinstance(lineage, list):
        raise TypeError("evaluation context lineage is invalid")
    if (
        not isinstance(context["candidate_id"], str)
        or not context["candidate_id"]
        or type(provenance.get("generation")) is not int
    ):
        raise TypeError("evaluation context identity is invalid")

    directory = Path(candidate_directory).resolve(strict=True)
    if {path.name for path in directory.iterdir()} != {"language.json", "program.json"}:
        raise ValueError(
            "candidate directory must contain only language.json and program.json"
        )
    parent_language = load_language_lineage(lineage)
    language = load_macro_language(
        read_json(directory / "language.json"), parent_language
    )
    return {
        "schema_version": 1,
        "candidate_id": context["candidate_id"],
        "generation": provenance["generation"],
        "language_hash": language.sha256,
        "language_lineage": [*lineage, language.to_dict()],
    }
