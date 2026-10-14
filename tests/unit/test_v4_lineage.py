"""Verified replay retains repeats and rejects tampered pilot evidence."""

from __future__ import annotations

import copy
import csv
import hashlib
import json
from pathlib import Path

import pytest

from bias_optimizer.dsl.ast import Expr
from bias_optimizer.dsl.types import ValueType
from bias_optimizer.v4.candidate.context import (
    build_candidate_context,
    build_candidate_lineage_state,
)
from bias_optimizer.v4.candidate.provenance import CandidateValidationError
from bias_optimizer.v4.candidate.replay import replay_pilot, verify_artifact
from bias_optimizer.v4.language import (
    G0_LANGUAGE,
    InputRef,
    MacroBodyCall,
    MacroPrimitive,
    extend_macro_language,
)
from bias_optimizer.v4.lineage import build_lineage_archive, lineage_mermaid


def _record(path: Path, root: Path) -> dict:
    content = path.read_bytes()
    return {
        "path": str(path.relative_to(root)),
        "sha256": hashlib.sha256(content).hexdigest(),
        "size_bytes": len(content),
    }


@pytest.fixture
def pilot(tmp_path: Path):
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
    environment = {
        "protocol_sha256": hashlib.sha256(protocol.read_bytes()).hexdigest(),
        "llmao_commit": "a" * 40,
        "evaluator_version_sha256": "b" * 64,
        "account_plan": "ChatGPT Plus",
    }
    seed_language = extend_macro_language(G0_LANGUAGE, [])
    macro = MacroPrimitive(
        name="normalized_grid",
        description="Normalized grid counts.",
        input_types=(ValueType.IMAGE,),
        output_type=ValueType.VECTOR,
        parameters={"type": "object", "properties": {}, "additionalProperties": False},
        body_ast=MacroBodyCall(
            "normalize",
            (MacroBodyCall("spatial_split", (InputRef(0),), {"rows": 2, "cols": 3}),),
        ),
    )
    child_language = extend_macro_language(seed_language, [macro])
    program = Expr("spatial_split", (Expr("image"),), {"rows": 2, "cols": 3})
    records, rows = [], []
    seed_state = None
    for index in range(4):
        directory = tmp_path / str(index)
        directory.mkdir()
        language = seed_language if index == 0 else child_language
        (directory / "language.json").write_text(json.dumps(language.to_dict()))
        candidate_program = (
            program if index == 0 else Expr("normalized_grid", (Expr("image"),))
        )
        (directory / "program.json").write_text(candidate_program.to_json())
        parent = {
            "generation": 0 if index == 0 else 1,
            "v4_parent_candidate_id": seed_state["candidate_id"]
            if seed_state
            else None,
            "parent_language_hash": seed_state["language_hash"] if seed_state else None,
            "eve_prefill_id": None if index == 0 else "prefill-seed",
        }
        if index == 3:
            (directory / "program.json").write_text(Expr("unknown").to_json())
            state = seed_state
            score = {"status": "failed", "score": 0.0}
            error = "unknown primitive"
        else:
            context = build_candidate_context(
                directory,
                protocol_path=protocol,
                parent_lineage=seed_state["language_lineage"] if seed_state else [],
                parent_candidate_id=seed_state["candidate_id"] if seed_state else None,
                generation=parent["generation"],
            )
            state = build_candidate_lineage_state(directory, context=context)
            score = {
                "status": "stage_one_only",
                "score": 0.5 + index / 100,
                "discovery_ready": False,
                "feature_dimension": 6,
                "candidate_id": state["candidate_id"],
                "parent_candidate_id": parent["v4_parent_candidate_id"],
                "llmao_commit": environment["llmao_commit"],
                "evaluator_version_sha256": environment["evaluator_version_sha256"],
            }
            error = None
            if index == 0:
                seed_state = state
        for name, payload in {
            "lineage_state.json": state,
            "lineage_parent.json": parent,
            "evaluation.json": {"score": score, "validation_error": error},
        }.items():
            (directory / name).write_text(json.dumps(payload))
        records.append(
            {
                "iteration": index,
                "files": {
                    path.name: _record(path, tmp_path) for path in directory.iterdir()
                },
            }
        )
        if index:
            rows.append(
                {
                    "iteration": index,
                    "solver_id": f"solver-{index}",
                    "score_json": json.dumps(score),
                }
            )
    telemetry = tmp_path / "phase2_solvers.csv"
    with telemetry.open("w", newline="") as stream:
        writer = csv.DictWriter(
            stream, fieldnames=["iteration", "solver_id", "score_json"]
        )
        writer.writeheader()
        writer.writerows(rows)
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "phase": 10,
                "environment": environment,
                "run": {
                    "run_id": "run-1",
                    "evidence_files": {"telemetry": _record(telemetry, tmp_path)},
                },
                "seed": records[0],
                "attempts": records[1:],
            }
        )
    )
    return manifest, tmp_path, protocol


def test_replay_and_archive_preserve_repeat_measurements(pilot) -> None:
    manifest, root, protocol = pilot
    replay = replay_pilot(manifest, artifact_root=root, protocol_path=protocol)
    assert (replay["valid_proposals"], replay["invalid_proposals"]) == (2, 1)
    assert replay["unique_valid_expanded_representations"] == 1
    archive = build_lineage_archive([replay])
    assert len(archive["observations"]) == 4
    assert len(archive["languages"]) == 3
    assert len(archive["edges"]) == 2
    repeated = next(
        group for group in archive["candidate_observations"].values() if len(group) == 2
    )
    assert repeated == ["run-1:1", "run-1:2"]
    assert [
        item["original_evaluation"]["score"]["score"]
        for item in archive["observations"][1:3]
    ] == [0.51, 0.52]
    assert archive["source_runs"][0]["independent_search_id"] is None
    primitive = archive["primitives"][0]
    assert primitive["independent_search_reuse_established"] is None
    assert primitive["observed_solver_entry_ids"] == ["solver-1", "solver-2"]
    assert len(primitive["birth_events"]) == 1
    assert primitive["birth_events"][0]["generation"] == 1
    assert len(primitive["score_observations"]) == 2
    assert lineage_mermaid(archive).count(" --> ") == 2
    with pytest.raises(CandidateValidationError, match="same run"):
        build_lineage_archive([replay, replay])


def test_independence_requires_declared_search_ids(pilot) -> None:
    manifest, root, protocol = pilot
    first = replay_pilot(manifest, artifact_root=root, protocol_path=protocol)
    second = copy.deepcopy(first)
    second["run_id"] = "run-2"
    for observation in second["observations"]:
        observation["observation_id"] = observation["observation_id"].replace(
            "run-1:", "run-2:"
        )
    unknown = build_lineage_archive([first, second])
    assert unknown["primitives"][0]["independent_search_reuse_established"] is None
    declared = build_lineage_archive(
        [first, second],
        independent_search_ids={
            "run-1": "search-seed-1",
            "run-2": "search-seed-2",
        },
    )
    assert declared["primitives"][0]["independent_search_reuse_established"] is True


def test_replay_rejects_modified_candidate_bytes(pilot) -> None:
    manifest, root, protocol = pilot
    (root / "1" / "program.json").write_text("{}")
    with pytest.raises(CandidateValidationError, match="mismatch"):
        replay_pilot(manifest, artifact_root=root, protocol_path=protocol)


def test_replay_rejects_changed_protocol(pilot) -> None:
    manifest, root, protocol = pilot
    protocol.write_text(protocol.read_text() + "\n")
    with pytest.raises(CandidateValidationError, match="protocol differs"):
        replay_pilot(manifest, artifact_root=root, protocol_path=protocol)


def test_artifact_rejects_escape_and_symlink(tmp_path) -> None:
    path = tmp_path / "file.json"
    path.write_text("{}")
    record = _record(path, tmp_path)
    escaped = copy.deepcopy(record)
    escaped["path"] = "../file.json"
    with pytest.raises(CandidateValidationError, match="inside"):
        verify_artifact(escaped, tmp_path)
    linked = tmp_path / "link.json"
    linked.symlink_to(path)
    record["path"] = "link.json"
    with pytest.raises(CandidateValidationError, match="symlinks"):
        verify_artifact(record, tmp_path)


def test_replay_rejects_forged_parent_even_with_new_file_digest(pilot) -> None:
    manifest, root, protocol = pilot
    path = root / "3" / "lineage_state.json"
    state = json.loads(path.read_text())
    state["candidate_id"] = "forged-parent"
    path.write_text(json.dumps(state))
    data = json.loads(manifest.read_text())
    data["attempts"][2]["files"]["lineage_state.json"] = _record(path, root)
    manifest.write_text(json.dumps(data))
    with pytest.raises(CandidateValidationError, match="previously accepted"):
        replay_pilot(manifest, artifact_root=root, protocol_path=protocol)
