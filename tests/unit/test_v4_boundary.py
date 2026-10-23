"""Data-only candidate and representation boundary checks for V4."""

from __future__ import annotations

import json

import numpy as np
import pytest

from bias_optimizer.data.mnist import MNISTSearchData
from bias_optimizer.dsl.ast import Expr
from bias_optimizer.dsl.compiler import ProgramCompilationError, ProgramCompiler
from bias_optimizer.dsl.validator import ProgramConstraints
from bias_optimizer.v4.candidate import (
    CandidateV4,
    CandidateValidationError,
    ModelBackendMetadata,
    load_candidate_directory,
)
from bias_optimizer.v4.language import G0_LANGUAGE, extend_macro_language


def _candidate() -> CandidateV4:
    return CandidateV4.create(
        candidate_id="candidate-boundary",
        language=extend_macro_language(G0_LANGUAGE, []),
        program=Expr(
            "spatial_split",
            (Expr("image"),),
            {"rows": 1, "cols": 1},
        ),
        parent_candidate_id=None,
        invented_primitives=(),
        eve_agent_id="eve-agent-1",
        guidance_hash="d" * 64,
        generation=0,
        model_backend=ModelBackendMetadata(
            model_identifier="gpt-6-luna",
            backend="codex_tmux",
            reasoning_effort="max",
        ),
        evaluation_seed=42,
    )


def _write_candidate(candidate_directory, candidate, program=None) -> dict[str, object]:
    candidate_directory.mkdir()
    (candidate_directory / "language.json").write_text(
        json.dumps(candidate.language.to_dict()), encoding="utf-8"
    )
    (candidate_directory / "program.json").write_text(
        json.dumps((program or candidate.program).to_dict()), encoding="utf-8"
    )
    return {
        "schema_version": 1,
        "candidate_id": candidate.candidate_id,
        "provenance": candidate.provenance.to_dict(),
        "parent_language_lineage": [],
    }


@pytest.mark.parametrize(
    "operation",
    ["import", "sklearn", "open_file", "network_request", "subprocess", "dynamic_import", "global_state"],
)
def test_candidate_cannot_encode_executable_or_external_operations(
    operation: str, tmp_path
) -> None:
    candidate = _candidate()
    candidate_directory = tmp_path / "candidate"
    context = _write_candidate(
        candidate_directory,
        candidate,
        Expr(operation, (Expr("image"),)),
    )

    with pytest.raises(CandidateValidationError, match=r"outside language G\*"):
        load_candidate_directory(candidate_directory, context=context)


def test_candidate_cannot_include_label_fields(tmp_path) -> None:
    candidate = _candidate()
    candidate_directory = tmp_path / "candidate"
    context = _write_candidate(candidate_directory, candidate)
    program = candidate.program.to_dict()
    program["labels"] = "attempted-label-access"
    (candidate_directory / "program.json").write_text(
        json.dumps(program), encoding="utf-8"
    )

    with pytest.raises(CandidateValidationError, match="only op, args, and params"):
        load_candidate_directory(candidate_directory, context=context)


def test_candidate_cannot_add_an_executable_filesystem_payload(tmp_path) -> None:
    candidate = _candidate()
    candidate_directory = tmp_path / "candidate"
    context = _write_candidate(candidate_directory, candidate)
    (candidate_directory / "attack.py").write_text(
        "open('data/test_labels.csv')", encoding="utf-8"
    )

    with pytest.raises(CandidateValidationError, match="candidate directory must contain only"):
        load_candidate_directory(candidate_directory, context=context)


def test_search_data_exposes_only_read_only_train_and_validation_arrays() -> None:
    train_images = np.zeros((50, 28, 28), dtype=np.float32)
    train_labels = np.tile(np.arange(10, dtype=np.int64), 5)
    validation_images = np.zeros((20, 28, 28), dtype=np.float32)
    validation_labels = np.tile(np.arange(10, dtype=np.int64), 2)
    search_data = MNISTSearchData(
        train_images=train_images,
        train_labels=train_labels,
        validation_images=validation_images,
        validation_labels=validation_labels,
    )

    assert not hasattr(search_data, "test_images")
    assert not hasattr(search_data, "test_labels")
    for array in (
        search_data.train_images,
        search_data.train_labels,
        search_data.validation_images,
        search_data.validation_labels,
    ):
        assert not array.flags.writeable


def test_raw_pixel_passthrough_is_rejected() -> None:
    raw_pixel_program = Expr("flatten_pixels", (Expr("image"),))
    with pytest.raises(CandidateValidationError, match="784 features"):
        CandidateV4.create(
            candidate_id="raw-pixels",
            language=extend_macro_language(G0_LANGUAGE, []),
            program=raw_pixel_program,
            parent_candidate_id=None,
            invented_primitives=(),
            eve_agent_id="eve-agent-1",
            guidance_hash="e" * 64,
            generation=0,
            model_backend=ModelBackendMetadata(
                model_identifier="gpt-6-luna",
                backend="codex_tmux",
                reasoning_effort="max",
            ),
            evaluation_seed=42,
        )

    with pytest.raises(ProgramCompilationError, match="raw pixels are not allowed"):
        ProgramCompiler(ProgramConstraints(max_feature_dim=1_024)).compile(
            raw_pixel_program
        )
