"""Data-free candidate checks preserve the evaluator's structural boundary."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from bias_optimizer.dsl.ast import Expr
from bias_optimizer.v4.candidate.check import (
    check_candidate_directory,
    validate_lineage_state,
)
from bias_optimizer.v4.candidate.context import (
    build_candidate_context,
    build_candidate_lineage_state,
)
from bias_optimizer.v4.candidate.provenance import CandidateValidationError
from bias_optimizer.v4.language import G0_LANGUAGE, extend_macro_language


@pytest.fixture
def candidate_files(tmp_path: Path) -> tuple[Path, Path]:
    directory = tmp_path / "candidate"
    directory.mkdir()
    language = extend_macro_language(G0_LANGUAGE, [])
    program = Expr("spatial_split", (Expr("image"),), {"rows": 2, "cols": 3})
    (directory / "language.json").write_text(json.dumps(language.to_dict()))
    (directory / "program.json").write_text(program.to_json())
    protocol = tmp_path / "protocol.json"
    protocol.write_text(
        json.dumps(
            {
                "primary_design": {
                    "exact_cli_model_identifier": "gpt-6-luna",
                    "requested_reasoning_effort": "max",
                },
                "candidate_boundary": {"codex_driver": "codex_tmux"},
                "evaluator_basis": {"training_subset_seed": 42},
            }
        )
    )
    return directory, protocol


def test_check_is_read_only_and_reports_expanded_structure(candidate_files) -> None:
    directory, protocol = candidate_files
    before = {path.name: path.read_bytes() for path in directory.iterdir()}
    result = check_candidate_directory(directory, protocol_path=protocol)
    assert result["status"] == "valid"
    assert result["expanded_depth"] == 1
    assert result["expanded_node_count"] == 2
    assert result["feature_dimension"] == 6
    assert result["used_macros"] == []
    assert "score" not in result
    assert before == {path.name: path.read_bytes() for path in directory.iterdir()}


def test_check_accepts_an_evaluator_lineage_parent(candidate_files) -> None:
    directory, protocol = candidate_files
    context = build_candidate_context(directory, protocol_path=protocol)
    state = build_candidate_lineage_state(directory, context=context)
    parent = extend_macro_language(G0_LANGUAGE, [])
    child = extend_macro_language(parent, [])

    assert state["language_hash"] == parent.sha256
    assert child.parent_language_hash == state["language_hash"]
    wrong_parent = child.to_dict()
    wrong_parent["parent_language_hash"] = parent.parent_language_hash
    (directory / "language.json").write_text(json.dumps(wrong_parent))
    invalid = check_candidate_directory(
        directory, parent_state=state, protocol_path=protocol
    )
    assert invalid["status"] == "invalid"
    assert "parent hash does not match" in invalid["validation_error"]

    (directory / "language.json").write_text(json.dumps(child.to_dict()))
    result = check_candidate_directory(
        directory, parent_state=state, protocol_path=protocol
    )
    assert result["status"] == "valid"
    assert result["language_hash"] != parent.sha256


@pytest.mark.parametrize(
    "field,value",
    [
        ("schema_version", True),
        ("generation", True),
        ("generation", -1),
        ("candidate_id", "bad/path"),
        ("language_hash", "0" * 64),
        ("language_lineage", []),
    ],
)
def test_check_rejects_tampered_parent_state(candidate_files, field, value) -> None:
    directory, protocol = candidate_files
    context = build_candidate_context(directory, protocol_path=protocol)
    state = copy.deepcopy(build_candidate_lineage_state(directory, context=context))
    state[field] = value
    with pytest.raises(CandidateValidationError):
        validate_lineage_state(state)
    assert (
        check_candidate_directory(
            directory,
            parent_state=state,
            protocol_path=protocol,
        )["status"]
        == "invalid"
    )


def test_check_rejects_extra_files_and_symlinks(candidate_files, tmp_path) -> None:
    directory, protocol = candidate_files
    (directory / "repair.py").write_text("pass\n")
    assert (
        check_candidate_directory(directory, protocol_path=protocol)["status"]
        == "invalid"
    )
    (directory / "repair.py").unlink()
    program = directory / "program.json"
    outside = tmp_path / "outside.json"
    program.rename(outside)
    program.symlink_to(outside)
    assert (
        check_candidate_directory(directory, protocol_path=protocol)["status"]
        == "invalid"
    )


def test_check_rejects_invalid_ast_without_repair(candidate_files) -> None:
    directory, protocol = candidate_files
    path = directory / "program.json"
    path.write_text('{"op": "not_a_primitive", "args": [], "params": {}}')
    original = path.read_bytes()
    assert (
        check_candidate_directory(directory, protocol_path=protocol)["status"]
        == "invalid"
    )
    assert path.read_bytes() == original
