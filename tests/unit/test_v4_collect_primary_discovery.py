"""Integrity and lineage replay checks for the Phase 12 collector."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from bias_optimizer.dsl.ast import Expr
from bias_optimizer.dsl.types import ValueType
from bias_optimizer.v4.candidate import load_candidate_directory
from bias_optimizer.v4.candidate.context import (
    build_candidate_context,
    build_candidate_lineage_state,
)
from bias_optimizer.v4.language import (
    G0_LANGUAGE,
    InputRef,
    MacroBodyCall,
    MacroPrimitive,
    extend_macro_language,
)
from experiments.v4_collect_primary_discovery import (
    _build_lineage,
    _validated_candidate,
)


def _protocol(path: Path) -> dict:
    payload = {
        "protocol_sha256": "a" * 64,
        "primary_design": {
            "exact_cli_model_identifier": "gpt-6-luna",
            "requested_reasoning_effort": "max",
        },
        "candidate_boundary": {"codex_driver": "codex_tmux"},
        "evaluator_basis": {"training_subset_seed": 42},
    }
    path.write_text(json.dumps(payload), encoding="utf-8")
    return payload


def _row(
    tmp_path: Path,
    *,
    name: str,
    language,
    program: Expr,
    parent_state: dict | None,
    protocol_path: Path,
    protocol: dict,
) -> tuple[dict, dict]:
    directory = tmp_path / name / "candidate"
    directory.mkdir(parents=True)
    (directory / "language.json").write_text(
        json.dumps(language.to_dict()), encoding="utf-8"
    )
    (directory / "program.json").write_text(program.to_json() + "\n", encoding="utf-8")
    parent_lineage = parent_state["language_lineage"] if parent_state else []
    parent_id = parent_state["candidate_id"] if parent_state else None
    generation = parent_state["generation"] + 1 if parent_state else 0
    context = build_candidate_context(
        directory,
        parent_lineage=parent_lineage,
        parent_candidate_id=parent_id,
        generation=generation,
        guidance_hash=None if generation == 0 else "b" * 64,
        protocol_path=protocol_path,
    )
    state = build_candidate_lineage_state(directory, context=context)
    candidate = load_candidate_directory(directory, context=context)
    fitness = 0.5
    record = {
        "kind": "common_initial_program" if generation == 0 else "adaptive_proposal",
        "status": "discovery_scored",
        "candidate_id": candidate.candidate_id,
        "parent_candidate_id": parent_id,
        "generation": generation,
        "language_sha256": candidate.language_hash,
        "expanded_program_sha256": candidate.expanded_program_hash,
        "introduced_macros": list(candidate.provenance.invented_primitives),
    }
    artifact = {
        "status": "discovery_scored",
        "protocol_sha256": protocol["protocol_sha256"],
        "candidate": {
            "candidate_id": candidate.candidate_id,
            "language_sha256": candidate.language_hash,
            "parent_language_sha256": candidate.parent_language_hash,
            "parent_candidate_id": parent_id,
            "program_sha256": candidate.program_hash,
            "expanded_program_sha256": candidate.expanded_program_hash,
            "generation": generation,
        },
    }
    score = {
        "status": "discovery_scored",
        "discovery_ready": True,
        "candidate_id": candidate.candidate_id,
        "discovery_fitness": fitness,
    }
    parent = {
        "parent_candidate_id": parent_id,
        "parent_language_hash": parent_state["language_hash"] if parent_state else None,
        "generation": generation,
    }
    row = {
        "id": name,
        "files": {
            "candidate/language.json": (directory / "language.json").read_text(),
            "candidate/program.json": (directory / "program.json").read_text(),
        },
        "score": {"score": fitness},
        "candidate": artifact["candidate"],
        "evaluation": {"stage_one_fitness": fitness},
        "evaluation_context": context,
        "parent_language_lineage": parent_lineage,
        "lineage_parent": parent,
        "lineage_state": state,
        "primary_record": record,
        "evaluation_status": "discovery_scored",
        "score_record": score,
        "evaluator_artifact": artifact,
        "token_usage": {"total": {"input_tokens": 10, "output_tokens": 2}},
        "optimizer_token_usage": {"input_tokens": 10, "output_tokens": 2},
    }
    return row, state


def test_primary_lineage_replays_parent_and_macro_reuse(tmp_path: Path) -> None:
    protocol_path = tmp_path / "protocol.json"
    protocol = _protocol(protocol_path)
    g0 = extend_macro_language(G0_LANGUAGE, [])
    initial, initial_state = _row(
        tmp_path,
        name="seed-0",
        language=g0,
        program=Expr("spatial_split", (Expr("image"),), {"rows": 1, "cols": 2}),
        parent_state=None,
        protocol_path=protocol_path,
        protocol=protocol,
    )
    macro = MacroPrimitive(
        name="normalize_vector",
        description="Normalize a vector.",
        input_types=(ValueType.VECTOR,),
        output_type=ValueType.VECTOR,
        parameters={"type": "object", "properties": {}, "additionalProperties": False},
        body_ast=MacroBodyCall("normalize", (InputRef(0),)),
    )
    child_language = extend_macro_language(g0, [macro])
    child, _ = _row(
        tmp_path,
        name="child-1",
        language=child_language,
        program=Expr(
            "normalize_vector",
            (Expr("spatial_split", (Expr("image"),), {"rows": 1, "cols": 2}),),
        ),
        parent_state=initial_state,
        protocol_path=protocol_path,
        protocol=protocol,
    )
    replayed, _ = _validated_candidate(child, protocol=protocol)
    assert "normalize_vector" in replayed.provenance.used_primitives

    run = {
        "contract": {
            "seed": 1101,
            "verified_protocol_sha256": protocol["protocol_sha256"],
            "verified_contract_sha256": "c" * 64,
        },
        "contract_path": str(tmp_path / "contract.json"),
        "run_root": tmp_path / "run",
        "run_manifest_sha256": "d" * 64,
        "run_manifest": {
            "successful_candidate_evaluations": 2,
            "unique_successful_expanded_asts": 2,
        },
        "solver_rows": [initial, child],
        "optimizer_rows": [],
        "trajectory_by_entry": {},
    }
    archive = _build_lineage([run], protocol)
    primitive = archive["primitives"][0]
    assert primitive["aliases"] == ["normalize_vector"]
    assert primitive["use_run_ids"] == ["discovery-1101"]
    assert len(archive["edges"]) == 2
    g0_edge = next(edge for edge in archive["edges"] if not edge["added_macros"])
    macro_edge = next(edge for edge in archive["edges"] if edge["added_macros"])
    assert g0_edge["parent_language_hash"] == G0_LANGUAGE.sha256
    assert macro_edge["added_macros"] == ["normalize_vector"]
    assert next(
        item for item in archive["languages"] if item["language_hash"] == initial["lineage_state"]["language_hash"]
    )["kind"] == "G*"


def test_primary_lineage_rejects_a_forged_parent_snapshot(tmp_path: Path) -> None:
    protocol_path = tmp_path / "protocol.json"
    protocol = _protocol(protocol_path)
    language = extend_macro_language(G0_LANGUAGE, [])
    row, _ = _row(
        tmp_path,
        name="seed-0",
        language=language,
        program=Expr("spatial_split", (Expr("image"),), {"rows": 1, "cols": 2}),
        parent_state=None,
        protocol_path=protocol_path,
        protocol=protocol,
    )
    row["lineage_state"]["language_lineage"] = []
    with pytest.raises((IndexError, ValueError)):
        _validated_candidate(row, protocol=protocol)
