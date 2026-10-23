"""Discovery penalizes macro inventory without penalizing lexical descriptions."""

from __future__ import annotations

import pytest

from bias_optimizer.dsl.types import ValueType
from bias_optimizer.v4.language import (
    G0_LANGUAGE,
    InputRef,
    MacroBodyCall,
    MacroPrimitive,
    extend_macro_language,
)
from bias_optimizer.v4.objective import discovery_objective


def _macro(name, description, cols=3):
    return MacroPrimitive(
        name=name,
        description=description,
        input_types=(ValueType.IMAGE,),
        output_type=ValueType.VECTOR,
        parameters={"type": "object", "properties": {}, "additionalProperties": False},
        body_ast=MacroBodyCall("spatial_split", (InputRef(0),), {"rows": 2, "cols": cols}),
    )


def test_no_macro_cost_preserves_stage_one_score() -> None:
    language = extend_macro_language(G0_LANGUAGE, [])
    result = discovery_objective(0.87, language)
    assert result["discovery_fitness"] == result["stage_one_fitness"] == 0.87
    assert result["language_complexity"] == result["language_penalty"]["value"] == 0


def test_inventory_cost_ignores_names_and_descriptions() -> None:
    first = extend_macro_language(G0_LANGUAGE, [_macro("grid", "Grid")])
    renamed = extend_macro_language(G0_LANGUAGE, [_macro("anonymous", "Opaque " * 100)])
    assert discovery_objective(0.87, first) == discovery_objective(0.87, renamed)
    child = extend_macro_language(first, [_macro("grid_two", "Another grid", cols=4)])
    result = discovery_objective(0.87, child)
    assert result["language_complexity"] == 2
    assert result["language_penalty"]["value"] == 0.001
    assert result["stage_one_fitness"] == 0.87
    assert result["discovery_fitness"] == pytest.approx(0.869)


@pytest.mark.parametrize("score", [True, "0.87", None, float("nan"), float("inf")])
def test_objective_rejects_invalid_scores(score) -> None:
    with pytest.raises(ValueError, match="finite"):
        discovery_objective(score, extend_macro_language(G0_LANGUAGE, []))


def test_objective_requires_a_macro_language() -> None:
    with pytest.raises(TypeError, match="MacroLanguage"):
        discovery_objective(0.87, G0_LANGUAGE)
