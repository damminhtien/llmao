"""Focused safety and determinism tests for V4 typed macros."""

from __future__ import annotations

import hashlib

import pytest

from bias_optimizer.dsl.ast import Expr
from bias_optimizer.dsl.types import ValueType
from bias_optimizer.v4.language import G0_LANGUAGE
from bias_optimizer.v4.language.macro import (
    InputRef,
    MacroBodyCall,
    MacroPrimitive,
    MacroValidationError,
    ParameterRef,
)
from bias_optimizer.v4.language.validator import (
    MacroLimits,
    expand_candidate,
    extend_macro_language,
    macro_behavior_hash,
)

_EMPTY_PARAMETERS = {
    "type": "object",
    "properties": {},
    "additionalProperties": False,
}


def _histogram_macro(name: str = "angle_histogram") -> MacroPrimitive:
    return MacroPrimitive(
        name=name,
        description="Build a fixed-width histogram of path angles.",
        input_types=(ValueType.ANGLE_SEQUENCE,),
        output_type=ValueType.VECTOR,
        parameters={
            "type": "object",
            "properties": {
                "bins": {
                    "type": "integer",
                    "default": 8,
                    "minimum": 2,
                    "maximum": 16,
                }
            },
            "additionalProperties": False,
        },
        body_ast=MacroBodyCall(
            "histogram",
            (InputRef(0),),
            {"bins": ParameterRef("bins")},
        ),
    )


def _normalize_macro(name: str = "normalize_vector") -> MacroPrimitive:
    return MacroPrimitive(
        name=name,
        description="Normalize a vector.",
        input_types=(ValueType.VECTOR,),
        output_type=ValueType.VECTOR,
        parameters=_EMPTY_PARAMETERS,
        body_ast=MacroBodyCall("normalize", (InputRef(0),)),
    )


def _angle_sequence_program(
    op: str,
    params: dict[str, int] | None = None,
    *,
    threshold_first: bool = True,
) -> Expr:
    image = Expr("image")
    source = Expr("threshold", (image,)) if threshold_first else image
    skeleton = Expr("skeletonize", (source,))
    graph = Expr("graph", (skeleton,))
    paths = Expr("paths", (graph,))
    angles = Expr("angles", (paths,))
    return Expr(op, (angles,), params or {})


def test_typed_macro_expands_to_a_canonical_base_ast() -> None:
    macro = _histogram_macro()
    language = extend_macro_language(G0_LANGUAGE, [macro])

    program = _angle_sequence_program("angle_histogram", {"bins": 4})
    result = expand_candidate(program, language)

    assert result.expanded_ast.op == "histogram"
    assert result.expanded_ast.args[0].op == "angles"
    assert result.expanded_ast.params == {"bins": 4}
    assert result.info.dimension == 4
    assert result.used_macros == ("angle_histogram",)
    assert "angle_histogram" in result.used_primitives
    assert "histogram" in result.used_primitives
    assert result.program_hash == hashlib.sha256(program.to_json().encode()).hexdigest()
    assert result.expanded_program_hash == hashlib.sha256(
        result.expanded_ast.to_json().encode()
    ).hexdigest()
    assert result.program_hash != result.expanded_program_hash
    assert macro.sha256 == _histogram_macro().sha256
    assert MacroPrimitive.from_dict(macro.to_dict()) == macro
    assert language.canonical_json == extend_macro_language(
        G0_LANGUAGE, [MacroPrimitive.from_dict(macro.to_dict())]
    ).canonical_json


def test_macro_parameter_overrides_are_checked_against_the_schema() -> None:
    language = extend_macro_language(G0_LANGUAGE, [_histogram_macro()])

    with pytest.raises(MacroValidationError, match="violates minimum"):
        expand_candidate(
            _angle_sequence_program("angle_histogram", {"bins": 1}), language
        )


def test_macro_input_dimensions_are_checked_after_substitution() -> None:
    ratio = MacroPrimitive(
        name="ratio_vectors",
        description="Divide equal-width vectors.",
        input_types=(ValueType.VECTOR, ValueType.VECTOR),
        output_type=ValueType.VECTOR,
        parameters=_EMPTY_PARAMETERS,
        body_ast=MacroBodyCall("ratio", (InputRef(0), InputRef(1))),
    )
    language = extend_macro_language(G0_LANGUAGE, [ratio])
    image = Expr("image")
    left = Expr("spatial_split", (image,), {"rows": 1, "cols": 2})
    right = Expr("spatial_split", (image,), {"rows": 1, "cols": 3})

    with pytest.raises(MacroValidationError, match="same dimension"):
        expand_candidate(Expr("ratio_vectors", (left, right)), language)


def test_nested_macro_expansion_tracks_all_reused_macros() -> None:
    histogram = _histogram_macro()
    normalized = MacroPrimitive(
        name="normalized_angle_histogram",
        description="Normalize an angle histogram.",
        input_types=(ValueType.ANGLE_SEQUENCE,),
        output_type=ValueType.VECTOR,
        parameters={
            "type": "object",
            "properties": {
                "bins": {
                    "type": "integer",
                    "default": 8,
                    "minimum": 2,
                    "maximum": 16,
                }
            },
            "additionalProperties": False,
        },
        body_ast=MacroBodyCall(
            "normalize",
            (
                MacroBodyCall(
                    "angle_histogram",
                    (InputRef(0),),
                    {"bins": ParameterRef("bins")},
                ),
            ),
        ),
    )
    parent_language = extend_macro_language(G0_LANGUAGE, [histogram])
    language = extend_macro_language(parent_language, [normalized])
    assert language.parent_language_hash == parent_language.sha256
    assert language.introduced_macros == ("normalized_angle_histogram",)

    result = expand_candidate(
        _angle_sequence_program(
            "normalized_angle_histogram", threshold_first=False
        ),
        language,
    )

    assert result.expanded_ast.op == "normalize"
    assert result.expanded_ast.args[0].op == "histogram"
    assert result.used_macros == (
        "angle_histogram",
        "normalized_angle_histogram",
    )
    assert macro_behavior_hash(histogram, language) != macro_behavior_hash(
        normalized, language
    )


def test_macro_body_type_mismatch_is_rejected() -> None:
    wrong_signature = MacroPrimitive(
        name="invalid_histogram",
        description="This macro declares the wrong input type.",
        input_types=(ValueType.VECTOR,),
        output_type=ValueType.VECTOR,
        parameters=_histogram_macro().parameters,
        body_ast=MacroBodyCall(
            "histogram",
            (InputRef(0),),
            {"bins": ParameterRef("bins")},
        ),
    )

    with pytest.raises(
        MacroValidationError,
        match="argument 0 must have type AngleSequence, Sequence",
    ):
        extend_macro_language(G0_LANGUAGE, [wrong_signature])


def test_recursive_and_cyclic_macro_dependencies_are_rejected() -> None:
    recursive = MacroPrimitive(
        name="recursive_macro",
        description="Calls itself.",
        input_types=(ValueType.ANGLE_SEQUENCE,),
        output_type=ValueType.VECTOR,
        parameters=_EMPTY_PARAMETERS,
        body_ast=MacroBodyCall("recursive_macro", (InputRef(0),)),
    )
    left = MacroPrimitive(
        name="left_macro",
        description="Calls the right macro.",
        input_types=(ValueType.ANGLE_SEQUENCE,),
        output_type=ValueType.VECTOR,
        parameters=_EMPTY_PARAMETERS,
        body_ast=MacroBodyCall("right_macro", (InputRef(0),)),
    )
    right = MacroPrimitive(
        name="right_macro",
        description="Calls the left macro.",
        input_types=(ValueType.ANGLE_SEQUENCE,),
        output_type=ValueType.VECTOR,
        parameters=_EMPTY_PARAMETERS,
        body_ast=MacroBodyCall("left_macro", (InputRef(0),)),
    )

    with pytest.raises(MacroValidationError, match="recursive macro dependency"):
        extend_macro_language(G0_LANGUAGE, [recursive])
    with pytest.raises(MacroValidationError, match="recursive macro dependency"):
        extend_macro_language(G0_LANGUAGE, [left, right])


def test_expansion_depth_and_node_caps_are_enforced() -> None:
    language = extend_macro_language(
        G0_LANGUAGE,
        [_histogram_macro()],
        limits=MacroLimits(max_expansion_depth=5),
    )
    with pytest.raises(MacroValidationError, match="depth 6"):
        expand_candidate(_angle_sequence_program("angle_histogram"), language)

    concatenation = MacroPrimitive(
        name="concatenate_vectors",
        description="Concatenate two vectors.",
        input_types=(ValueType.VECTOR, ValueType.VECTOR),
        output_type=ValueType.VECTOR,
        parameters=_EMPTY_PARAMETERS,
        body_ast=MacroBodyCall("concat", (InputRef(0), InputRef(1))),
    )
    with pytest.raises(MacroValidationError, match="3 nodes; limit is 2"):
        extend_macro_language(
            G0_LANGUAGE,
            [concatenation],
            limits=MacroLimits(max_expanded_nodes=2),
        )


def test_macro_call_depth_is_limited_even_when_aliases_add_no_ast_nodes() -> None:
    identity = MacroPrimitive(
        name="angle_identity",
        description="Return the angle sequence unchanged.",
        input_types=(ValueType.ANGLE_SEQUENCE,),
        output_type=ValueType.ANGLE_SEQUENCE,
        parameters=_EMPTY_PARAMETERS,
        body_ast=InputRef(0),
    )
    alias_one = MacroPrimitive(
        name="angle_identity_one",
        description="Alias the angle identity macro.",
        input_types=(ValueType.ANGLE_SEQUENCE,),
        output_type=ValueType.ANGLE_SEQUENCE,
        parameters=_EMPTY_PARAMETERS,
        body_ast=MacroBodyCall("angle_identity", (InputRef(0),)),
    )
    alias_two = MacroPrimitive(
        name="angle_identity_two",
        description="Add a second alias layer.",
        input_types=(ValueType.ANGLE_SEQUENCE,),
        output_type=ValueType.ANGLE_SEQUENCE,
        parameters=_EMPTY_PARAMETERS,
        body_ast=MacroBodyCall("angle_identity_one", (InputRef(0),)),
    )

    with pytest.raises(MacroValidationError, match="expansion chain has depth 3"):
        extend_macro_language(
            G0_LANGUAGE,
            [identity, alias_one, alias_two],
            limits=MacroLimits(max_expansion_depth=2),
        )


def test_output_dimension_cap_is_enforced() -> None:
    spatial = MacroPrimitive(
        name="four_cell_spatial",
        description="Split the image into four cells.",
        input_types=(ValueType.IMAGE,),
        output_type=ValueType.VECTOR,
        parameters=_EMPTY_PARAMETERS,
        body_ast=MacroBodyCall(
            "spatial_split",
            (InputRef(0),),
            {"rows": 2, "cols": 2},
        ),
    )

    with pytest.raises(MacroValidationError, match="4 features; limit is 3"):
        extend_macro_language(
            G0_LANGUAGE,
            [spatial],
            limits=MacroLimits(max_feature_dim=3),
        )


def test_duplicate_macro_behavior_is_deduplicated_by_expanded_ast() -> None:
    first = MacroPrimitive(
        name="normalize_vector",
        description="Normalize a vector.",
        input_types=(ValueType.VECTOR,),
        output_type=ValueType.VECTOR,
        parameters=_EMPTY_PARAMETERS,
        body_ast=MacroBodyCall("normalize", (InputRef(0),)),
    )
    duplicate = MacroPrimitive(
        name="vector_normalizer",
        description="A second name for the same computation.",
        input_types=(ValueType.VECTOR,),
        output_type=ValueType.VECTOR,
        parameters=_EMPTY_PARAMETERS,
        body_ast=MacroBodyCall("normalize", (InputRef(0),)),
    )

    with pytest.raises(MacroValidationError, match="duplicates behavior"):
        extend_macro_language(G0_LANGUAGE, [first, duplicate])


def test_new_macro_must_be_used_by_its_introducing_candidate() -> None:
    language = extend_macro_language(G0_LANGUAGE, [_normalize_macro()])
    base_program = Expr(
        "spatial_split",
        (Expr("image"),),
        {"rows": 1, "cols": 2},
    )

    with pytest.raises(MacroValidationError, match="does not use newly introduced"):
        expand_candidate(base_program, language)

    introduced_program = Expr("normalize_vector", (base_program,))
    result = expand_candidate(introduced_program, language)
    assert result.used_macros == ("normalize_vector",)

    parent = extend_macro_language(G0_LANGUAGE, [_normalize_macro()])
    threshold = MacroPrimitive(
        name="image_threshold",
        description="Threshold an image.",
        input_types=(ValueType.IMAGE,),
        output_type=ValueType.BINARY_IMAGE,
        parameters=_EMPTY_PARAMETERS,
        body_ast=MacroBodyCall("threshold", (InputRef(0),)),
    )
    child = extend_macro_language(parent, [threshold])
    with pytest.raises(MacroValidationError, match="not part of this language revision"):
        expand_candidate(
            introduced_program,
            child,
            introduced_macros=("normalize_vector",),
        )


def test_macros_cannot_use_excluded_human_language_operations() -> None:
    excluded = MacroPrimitive(
        name="human_pairwise_difference",
        description="Attempts to call an operation excluded from G0.",
        input_types=(ValueType.VECTOR, ValueType.VECTOR),
        output_type=ValueType.VECTOR,
        parameters=_EMPTY_PARAMETERS,
        body_ast=MacroBodyCall("pairwise_difference", (InputRef(0), InputRef(1))),
    )

    with pytest.raises(MacroValidationError, match="outside its language"):
        extend_macro_language(G0_LANGUAGE, [excluded])
