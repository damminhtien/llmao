"""Tests for V4 candidate loading and score-only evaluation artifacts."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

from bias_optimizer.domain.evaluation import Evaluation
from bias_optimizer.dsl.ast import Expr
from bias_optimizer.dsl.types import ValueType
from bias_optimizer.v4.candidate import (
    CandidateV4,
    ModelBackendMetadata,
    load_candidate_directory,
    load_language_lineage,
)
from bias_optimizer.v4.candidate.context import (
    build_candidate_context,
    build_candidate_lineage_state,
)
from bias_optimizer.v4.evaluator import (
    evaluate_candidate,
    evaluator_source_snapshot,
    failure_artifact,
    validate_protocol,
)
from bias_optimizer.v4.language import (
    G0_LANGUAGE,
    InputRef,
    MacroBodyCall,
    MacroPrimitive,
    extend_macro_language,
)


def _candidate() -> CandidateV4:
    macro = MacroPrimitive(
        name="normalize_vector",
        description="Normalize a vector.",
        input_types=(ValueType.VECTOR,),
        output_type=ValueType.VECTOR,
        parameters={
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        },
        body_ast=MacroBodyCall("normalize", (InputRef(0),)),
    )
    language = extend_macro_language(G0_LANGUAGE, [macro])
    program = Expr(
        "normalize_vector",
        (Expr("spatial_split", (Expr("image"),), {"rows": 1, "cols": 2}),),
    )
    return CandidateV4.create(
        candidate_id="candidate-001",
        language=language,
        program=program,
        parent_candidate_id=None,
        invented_primitives=("normalize_vector",),
        eve_agent_id="eve-agent-1",
        guidance_hash="a" * 64,
        generation=0,
        model_backend=ModelBackendMetadata(
            model_identifier="gpt-6-luna",
            backend="codex_tmux",
            reasoning_effort="max",
        ),
        evaluation_seed=42,
    )


def _context(candidate: CandidateV4) -> dict[str, object]:
    return {
        "schema_version": 1,
        "candidate_id": candidate.candidate_id,
        "provenance": candidate.provenance.to_dict(),
        "parent_language_lineage": [],
    }


def test_candidate_directory_loads_data_only_files_and_external_context(
    tmp_path,
) -> None:
    candidate = _candidate()
    candidate_directory = tmp_path / "candidate"
    candidate_directory.mkdir()
    (candidate_directory / "language.json").write_text(
        json.dumps(candidate.language.to_dict()), encoding="utf-8"
    )
    (candidate_directory / "program.json").write_text(
        json.dumps(candidate.program.to_dict()), encoding="utf-8"
    )

    loaded = load_candidate_directory(
        candidate_directory,
        context=_context(candidate),
    )

    assert loaded.canonical_json == candidate.canonical_json
    assert loaded.expanded_program_hash == candidate.expanded_program_hash


def test_context_builder_derives_provenance_from_candidate_and_protocol(
    tmp_path,
) -> None:
    candidate = _candidate()
    candidate_directory = tmp_path / "candidate"
    candidate_directory.mkdir()
    (candidate_directory / "language.json").write_text(
        json.dumps(candidate.language.to_dict()), encoding="utf-8"
    )
    (candidate_directory / "program.json").write_text(
        json.dumps(candidate.program.to_dict()), encoding="utf-8"
    )

    context = build_candidate_context(candidate_directory)

    assert context["provenance"]["model_backend"] == {
        "model_identifier": "gpt-6-luna",
        "backend": "codex_tmux",
        "reasoning_effort": "max",
    }
    assert context["provenance"]["used_primitives"] == list(
        candidate.provenance.used_primitives
    )
    assert context["parent_language_lineage"] == []


def test_context_builder_requires_trusted_parent_language_lineage(tmp_path) -> None:
    candidate = _candidate()
    child = extend_macro_language(candidate.language, [])
    candidate_directory = tmp_path / "candidate"
    candidate_directory.mkdir()
    (candidate_directory / "language.json").write_text(
        json.dumps(child.to_dict()), encoding="utf-8"
    )
    (candidate_directory / "program.json").write_text(
        json.dumps(candidate.program.to_dict()), encoding="utf-8"
    )

    with pytest.raises(ValueError, match="parent hash does not match"):
        build_candidate_context(candidate_directory)
    context = build_candidate_context(
        candidate_directory,
        parent_lineage=[candidate.language.to_dict()],
        parent_candidate_id=candidate.candidate_id,
        generation=1,
    )

    assert context["provenance"]["generation"] == 1
    assert context["provenance"]["parent_candidate_id"] == candidate.candidate_id


def test_lineage_state_records_validated_language_hash_and_snapshots(tmp_path) -> None:
    candidate = _candidate()
    candidate_directory = tmp_path / "candidate"
    candidate_directory.mkdir()
    (candidate_directory / "language.json").write_text(
        json.dumps(candidate.language.to_dict()), encoding="utf-8"
    )
    (candidate_directory / "program.json").write_text(
        json.dumps(candidate.program.to_dict()), encoding="utf-8"
    )

    context = build_candidate_context(candidate_directory)
    state = build_candidate_lineage_state(candidate_directory, context=context)

    assert state["candidate_id"] == context["candidate_id"]
    assert state["generation"] == 0
    assert state["language_hash"] == candidate.language.sha256
    assert state["language_lineage"] == [candidate.language.to_dict()]


class _FakeEvaluator:
    def evaluate_pipeline(self, pipeline, **kwargs) -> Evaluation:
        assert pipeline.feature_dim == 2
        assert kwargs["train_sizes"] == (500,)
        assert kwargs["cache_namespace"].startswith("mnist_v4_")
        return Evaluation(
            accuracy_500=0.81,
            accuracy_5000=None,
            feature_dim=2,
            feature_runtime_ms=12.0,
            training_runtime_ms=4.0,
            inference_runtime_ms=2.0,
            confusion_matrix=np.zeros((10, 10), dtype=np.int64),
        )


def test_evaluation_returns_stage_one_score_without_validation_data() -> None:
    candidate = _candidate()
    artifact = evaluate_candidate(
        candidate,
        _FakeEvaluator(),
        evaluator_version_sha256="b" * 64,
        protocol_status="draft_before_discovery",
    )

    assert artifact["status"] == "stage_one_only"
    assert artifact["discovery_ready"] is False
    assert artifact["evaluation"]["stage_one_fitness"] > 0.8
    assert artifact["complexity"]["language_penalty"]["value"] is None
    assert artifact["discovery_fitness"] is None
    serialized = json.dumps(artifact)
    assert "confusion_matrix" not in serialized
    assert "validation_labels" not in serialized
    assert "predictions" not in serialized


def test_evaluator_failure_artifact_is_structured_and_unscored() -> None:
    artifact = failure_artifact(
        evaluator_version_sha256="c" * 64,
        protocol_status="draft_before_discovery",
        stage="candidate_validation",
        error=ValueError("invalid candidate program"),
        candidate_id="candidate-001",
    )

    assert artifact["status"] == "failed"
    assert artifact["evaluation"] is None
    assert artifact["discovery_fitness"] is None
    assert artifact["failure"] == {
        "stage": "candidate_validation",
        "type": "ValueError",
        "message": "invalid candidate program",
    }


def test_evaluator_source_snapshot_covers_frozen_inputs() -> None:
    snapshot = evaluator_source_snapshot(Path(__file__).resolve().parents[2])
    source_paths = {source["path"] for source in snapshot["sources"]}

    assert len(snapshot["sha256"]) == 64
    assert "experiments/v4_evaluate_candidate.py" in source_paths
    assert "experiments/v4_build_candidate_context.py" in source_paths
    assert "results/v4/protocol.json" in source_paths
    assert "results/v4/languages/g0.json.sha256" in source_paths


def test_protocol_still_matches_the_frozen_stage_one_evaluator() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    protocol = validate_protocol(repo_root / "results/v4/protocol.json")

    assert protocol["evaluator_basis"]["validation_size"] == 2_000
    assert protocol["evaluator_basis"]["training_subset_size"] == 500


def test_parent_language_lineage_is_rebuilt_from_g0() -> None:
    candidate = _candidate()
    restored_parent = load_language_lineage([candidate.language.to_dict()])

    assert restored_parent.sha256 == candidate.language.sha256


def test_cli_writes_structured_validation_failure_outside_candidate_directory(
    tmp_path,
) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    candidate_directory = tmp_path / "candidate"
    candidate_directory.mkdir()
    context_path = tmp_path / "run_context.json"
    context_path.write_text("{}", encoding="utf-8")
    artifact_path = tmp_path / "score.json"
    log_path = tmp_path / "evaluator.log"

    completed = subprocess.run(
        [
            sys.executable,
            str(repo_root / "experiments/v4_evaluate_candidate.py"),
            str(candidate_directory),
            "--context",
            str(context_path),
            "--output",
            str(artifact_path),
            "--log",
            str(log_path),
        ],
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 1
    assert artifact_path.parent == candidate_directory.parent
    assert log_path.parent == candidate_directory.parent
    artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
    assert artifact["status"] == "failed"
    assert artifact["failure"]["stage"] == "candidate_validation"
    assert artifact["failure"]["type"] == "CandidateValidationError"
    assert "evaluator_version_sha256" in artifact
    assert "Traceback" in log_path.read_text(encoding="utf-8")
