"""Schema and provenance tests for V4 candidates."""

from __future__ import annotations

import copy

import pytest

from bias_optimizer.dsl.ast import Expr
from bias_optimizer.dsl.types import ValueType
from bias_optimizer.v4.candidate import (
    CandidateV4,
    CandidateValidationError,
    ModelBackendMetadata,
    TokenUsage,
    WallClockMeasurements,
)
from bias_optimizer.v4.language import (
    G0_LANGUAGE,
    InputRef,
    MacroBodyCall,
    MacroPrimitive,
    extend_macro_language,
)


def _empty_parameters() -> dict[str, object]:
    return {
        "type": "object",
        "properties": {},
        "additionalProperties": False,
    }


def _normalize_macro() -> MacroPrimitive:
    return MacroPrimitive(
        name="normalize_vector",
        description="Normalize a vector.",
        input_types=(ValueType.VECTOR,),
        output_type=ValueType.VECTOR,
        parameters=_empty_parameters(),
        body_ast=MacroBodyCall("normalize", (InputRef(0),)),
    )


def _spatial_macro() -> MacroPrimitive:
    return MacroPrimitive(
        name="two_cell_spatial",
        description="Split an image into two spatial cells.",
        input_types=(ValueType.IMAGE,),
        output_type=ValueType.VECTOR,
        parameters=_empty_parameters(),
        body_ast=MacroBodyCall(
            "spatial_split",
            (InputRef(0),),
            {"rows": 1, "cols": 2},
        ),
    )


def _candidate(
    *,
    language=None,
    program=None,
    candidate_id: str = "candidate-001",
    parent_candidate_id: str | None = None,
    invented_primitives: tuple[str, ...] = ("normalize_vector",),
    generation: int = 0,
) -> CandidateV4:
    language = language or extend_macro_language(G0_LANGUAGE, [_normalize_macro()])
    if program is None:
        image = Expr("image")
        vector = Expr("spatial_split", (image,), {"rows": 1, "cols": 2})
        program = Expr("normalize_vector", (vector,))
    return CandidateV4.create(
        candidate_id=candidate_id,
        language=language,
        program=program,
        parent_candidate_id=parent_candidate_id,
        invented_primitives=invented_primitives,
        eve_agent_id="eve-agent-7",
        guidance_hash="a" * 64,
        generation=generation,
        model_backend=ModelBackendMetadata(
            model_identifier="gpt-6-luna",
            backend="codex_tmux",
            reasoning_effort="max",
        ),
        evaluation_seed=42,
        token_usage=TokenUsage(
            input_tokens=1200,
            cached_input_tokens=300,
            output_tokens=80,
        ),
        wall_clock_ms=WallClockMeasurements(
            generation_ms=12.5,
            validation_ms=1.5,
            evaluation_ms=24.0,
            total_ms=38.0,
        ),
    )


def test_candidate_records_hashes_and_validated_provenance() -> None:
    candidate = _candidate()
    record = candidate.to_dict()

    assert record["language_hash"] == candidate.language.sha256
    assert record["parent_language_hash"] == G0_LANGUAGE.sha256
    assert record["program_hash"] == candidate.expansion.program_hash
    assert record["expanded_program_hash"] == candidate.expansion.expanded_program_hash
    assert record["provenance"]["invented_primitives"] == ["normalize_vector"]
    assert "normalize_vector" in record["provenance"]["used_primitives"]
    assert record["provenance"]["token_usage"]["input_tokens"] == 1200
    assert record["provenance"]["wall_clock_ms"]["evaluation_ms"] == 24.0
    assert candidate.program_hash != candidate.expanded_program_hash


def test_candidate_round_trips_through_canonical_json_and_schema() -> None:
    candidate = _candidate()
    restored = CandidateV4.from_dict(
        candidate.to_dict(), parent_language=G0_LANGUAGE
    )

    assert restored == candidate
    assert restored.canonical_json == candidate.canonical_json


def test_candidate_loader_reconstructs_exact_language_lineage() -> None:
    parent = extend_macro_language(G0_LANGUAGE, [_normalize_macro()])
    child = extend_macro_language(parent, [_spatial_macro()])
    program = Expr(
        "normalize_vector",
        (Expr("two_cell_spatial", (Expr("image"),)),),
    )
    candidate = _candidate(
        language=child,
        program=program,
        candidate_id="candidate-002",
        parent_candidate_id="candidate-001",
        invented_primitives=("two_cell_spatial",),
        generation=1,
    )

    restored = CandidateV4.from_dict(
        candidate.to_dict(), parent_language=parent
    )

    assert restored.language_hash == child.sha256
    assert restored.parent_language_hash == parent.sha256
    assert restored.language.introduced_macros == ("two_cell_spatial",)
    assert restored.expansion.used_macros == (
        "normalize_vector",
        "two_cell_spatial",
    )


def test_tampered_hashes_and_used_primitive_lists_are_rejected() -> None:
    candidate = _candidate()
    tampered_hash = copy.deepcopy(candidate.to_dict())
    tampered_hash["program_hash"] = "0" * 64
    with pytest.raises(CandidateValidationError, match="program_hash"):
        CandidateV4.from_dict(tampered_hash, parent_language=G0_LANGUAGE)

    tampered_usage = copy.deepcopy(candidate.to_dict())
    tampered_usage["provenance"]["used_primitives"].remove("normalize_vector")
    with pytest.raises(CandidateValidationError, match="used_primitives"):
        CandidateV4.from_dict(tampered_usage, parent_language=G0_LANGUAGE)


def test_candidate_rejects_an_unused_macro_introduced_by_its_provenance() -> None:
    language = extend_macro_language(G0_LANGUAGE, [_normalize_macro()])
    program = Expr(
        "spatial_split",
        (Expr("image"),),
        {"rows": 1, "cols": 2},
    )

    with pytest.raises(CandidateValidationError, match="does not use newly introduced"):
        _candidate(language=language, program=program)


def test_token_time_and_lineage_metadata_are_validated() -> None:
    with pytest.raises(CandidateValidationError, match="cached_input_tokens"):
        TokenUsage(input_tokens=10, cached_input_tokens=11, output_tokens=1)
    with pytest.raises(CandidateValidationError, match="finite non-negative"):
        WallClockMeasurements(evaluation_ms=-1)
    with pytest.raises(CandidateValidationError, match="generation 0"):
        _candidate(parent_candidate_id="candidate-parent")
    with pytest.raises(CandidateValidationError, match="later generations"):
        _candidate(generation=1)


def test_candidate_loader_requires_the_declared_parent_language() -> None:
    candidate = _candidate()
    tampered = copy.deepcopy(candidate.to_dict())
    tampered["language"]["parent_language_hash"] = "0" * 64

    with pytest.raises(CandidateValidationError, match="parent hash"):
        CandidateV4.from_dict(tampered, parent_language=G0_LANGUAGE)


def test_candidate_cannot_raise_protocol_macro_limits() -> None:
    candidate = _candidate()
    tampered = copy.deepcopy(candidate.to_dict())
    tampered["language"]["limits"]["max_expanded_nodes"] = 100_000

    with pytest.raises(CandidateValidationError, match="protocol limits"):
        CandidateV4.from_dict(tampered, parent_language=G0_LANGUAGE)
