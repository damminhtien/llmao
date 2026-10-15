"""Final-protocol scoring and integrity checks for V4 discovery."""

from __future__ import annotations

import hashlib
import json

import pytest

from bias_optimizer.dsl.types import ValueType
from bias_optimizer.v4.discovery import apply_discovery_score, load_finalized_protocol
from bias_optimizer.v4.language import (
    G0_LANGUAGE,
    InputRef,
    MacroBodyCall,
    MacroPrimitive,
    extend_macro_language,
)


def _language_with_one_invented_macro():
    macro = MacroPrimitive(
        name="normalize_vector",
        description="Normalize a vector.",
        input_types=(ValueType.VECTOR,),
        output_type=ValueType.VECTOR,
        parameters={"type": "object", "properties": {}, "additionalProperties": False},
        body_ast=MacroBodyCall("normalize", (InputRef(0),)),
    )
    return extend_macro_language(G0_LANGUAGE, [macro])


def test_primary_score_adds_only_the_registered_macro_penalty() -> None:
    artifact = {
        "status": "stage_one_only",
        "candidate": {"candidate_id": "candidate-1"},
        "evaluation": {"stage_one_fitness": 0.87, "accuracy_500": 0.81},
        "complexity": {"program_nodes": 12},
    }

    scored = apply_discovery_score(
        artifact,
        _language_with_one_invented_macro(),
        protocol_sha256="a" * 64,
        parent_candidate_id="parent-1",
    )

    assert scored["status"] == "discovery_scored"
    assert scored["protocol_sha256"] == "a" * 64
    assert scored["candidate"]["parent_candidate_id"] == "parent-1"
    assert scored["candidate"]["introduced_macros"] == ["normalize_vector"]
    assert scored["evaluation"]["stage_one_fitness"] == 0.87
    assert scored["evaluation"]["language_complexity"] == 1
    assert scored["evaluation"]["language_penalty"]["value"] == 0.0005
    assert scored["discovery_fitness"] == pytest.approx(0.8695)
    assert artifact["status"] == "stage_one_only"


def test_finalized_protocol_requires_a_matching_hash(tmp_path) -> None:
    path = tmp_path / "primary_protocol.json"
    payload = {
        "status": "finalized_primary",
        "primary_discovery": {"official_test_access": False},
    }
    raw = (json.dumps(payload, sort_keys=True) + "\n").encode()
    digest = hashlib.sha256(raw).hexdigest()
    path.write_bytes(raw)
    path.with_suffix(".json.sha256").write_text(f"{digest}  {path.name}\n")

    loaded, observed = load_finalized_protocol(path, expected_sha256=digest)

    assert loaded == payload
    assert observed == digest
    with pytest.raises(ValueError, match="launch contract"):
        load_finalized_protocol(path, expected_sha256="b" * 64)


def test_finalized_protocol_rejects_test_access(tmp_path) -> None:
    path = tmp_path / "primary_protocol.json"
    path.write_text(
        json.dumps(
            {
                "status": "finalized_primary",
                "primary_discovery": {"official_test_access": True},
            }
        )
    )

    with pytest.raises(ValueError, match="official test access"):
        load_finalized_protocol(path)
