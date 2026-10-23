"""Tests for the immutable V4 base and human-designed languages."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from bias_optimizer.dsl.primitives import PRIMITIVES
from bias_optimizer.v4.language import (
    G0_LANGUAGE,
    GH_LANGUAGE,
    build_g0_language,
    build_gh_language,
)
from bias_optimizer.v4.language.base_language import (
    EXCLUDED_V3_OPERATIONS,
    V2_PRIMITIVE_NAMES,
)


def test_language_hashes_are_deterministic_and_cover_canonical_json() -> None:
    for manifest, rebuilt in (
        (G0_LANGUAGE, build_g0_language()),
        (GH_LANGUAGE, build_gh_language()),
    ):
        assert manifest.canonical_json == rebuilt.canonical_json
        assert manifest.sha256 == rebuilt.sha256
        assert manifest.sha256 == hashlib.sha256(
            manifest.canonical_json.encode("utf-8")
        ).hexdigest()
        assert json.loads(manifest.canonical_json) == manifest.to_dict()


def test_checked_in_language_manifests_match_the_canonical_definitions() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    for filename, manifest in (("g0.json", G0_LANGUAGE), ("gh.json", GH_LANGUAGE)):
        path = repo_root / "results" / "v4" / "languages" / filename
        payload = path.read_bytes()

        assert payload.decode("utf-8") == manifest.canonical_json
        assert hashlib.sha256(payload).hexdigest() == manifest.sha256
        assert (path.with_suffix(path.suffix + ".sha256")).read_text().split()[0] == (
            manifest.sha256
        )


def test_g0_is_the_pinned_v2_vocabulary_without_v3_additions() -> None:
    names = tuple(primitive.name for primitive in G0_LANGUAGE.primitives)

    assert names == V2_PRIMITIVE_NAMES
    assert set(names).isdisjoint(EXCLUDED_V3_OPERATIONS)
    assert set(G0_LANGUAGE.excluded_operations) == set(EXCLUDED_V3_OPERATIONS)
    assert G0_LANGUAGE.basis_commit.startswith("cab3e82")


def test_gh_wraps_the_complete_frozen_v3_registry() -> None:
    names = tuple(primitive.name for primitive in GH_LANGUAGE.primitives)

    assert names == tuple(sorted(PRIMITIVES))
    assert set(names) == set(PRIMITIVES)
    assert set(EXCLUDED_V3_OPERATIONS).issubset(names)
    assert GH_LANGUAGE.basis_commit.startswith("1e9f29b")


def test_manifests_record_typed_signatures_and_parameter_schemas() -> None:
    gh = {primitive.name: primitive for primitive in GH_LANGUAGE.primitives}

    assert gh["concat"].input_types == ()
    assert gh["concat"].variadic_input_types == ("Vector",)
    assert gh["concat"].minimum_args == 2
    assert gh["concat"].output_dimension_rule == "sum:input_dimensions"
    assert gh["histogram"].input_types == (("AngleSequence", "Sequence"),)
    assert gh["histogram"].output_type == "Vector"
    assert gh["histogram"].output_dimension_rule == "parameter:bins"
    assert gh["ratio"].output_dimension_rule == "same_as:first_input"
    assert gh["histogram"].to_dict()["parameter_schema"]["properties"]["bins"] == {
        "type": "integer",
        "default": 8,
        "minimum": 2,
        "maximum": 32,
    }
    assert all(
        primitive.to_dict()["parameter_schema"]["type"] == "object"
        and primitive.to_dict()["parameter_schema"]["additionalProperties"] is False
        for primitive in GH_LANGUAGE.primitives
    )


def test_building_languages_does_not_mutate_the_frozen_registry() -> None:
    registry = PRIMITIVES
    entries = tuple(PRIMITIVES.items())

    build_g0_language()
    build_gh_language()

    assert PRIMITIVES is registry
    assert tuple(PRIMITIVES.items()) == entries
    with pytest.raises(TypeError):
        PRIMITIVES["new_operation"] = PRIMITIVES["image"]  # type: ignore[index]
