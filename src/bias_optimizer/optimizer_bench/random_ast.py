"""Typed random AST sampling from the existing V3 primitive registry."""

from __future__ import annotations

import random
from math import pi

from bias_optimizer.dsl.ast import Expr
from bias_optimizer.dsl.compiler import ProgramCompiler
from bias_optimizer.dsl.primitives import PRIMITIVES, PrimitiveDefinition
from bias_optimizer.dsl.types import ValueType
from bias_optimizer.dsl.validator import ProgramConstraints, infer_type


class SamplingFailure(ValueError):
    """A sampled request could not produce a program within frozen constraints."""


_PARAMETER_PRESETS: dict[str, tuple[dict[str, object], ...]] = {
    "threshold": tuple({"value": value} for value in (0.3, 0.4, 0.5, 0.6, 0.7)),
    "skeletonize": tuple({"threshold": value} for value in (0.3, 0.4, 0.5, 0.6, 0.7)),
    "sign": tuple({"epsilon": value} for value in (0.0, 0.05, 0.1, pi / 4)),
    "histogram": tuple(
        {"bins": bins, "low": low, "high": high}
        for bins in (4, 6, 8, 12, 16, 32)
        for low, high in ((-pi, pi), (0.0, 16.0), (-8.0, 8.0))
    ),
    "moments": tuple(
        {"orders": list(orders)}
        for orders in ((1,), (1, 2), (1, 2, 3), (2, 4), (1, 3, 5))
    ),
    "quantiles": tuple(
        {"quantiles": list(values)}
        for values in ((0.25, 0.5, 0.75), (0.1, 0.5, 0.9), (0.5,))
    ),
    "autocorrelation": tuple(
        {"lags": list(values)} for values in ((1,), (1, 2), (1, 2, 4), (2, 4, 8))
    ),
    "spatial_condition": tuple(
        {
            "axis": axis,
            "regions": regions,
            "bins": bins,
            "low": -pi,
            "high": pi,
        }
        for axis in ("vertical", "horizontal")
        for regions, bins in ((2, 4), (3, 6), (3, 8), (4, 4))
    ),
    "cross_histogram": tuple(
        {
            "bins_x": x,
            "bins_y": y,
            "low_x": 0.0,
            "high_x": 1.0,
            "low_y": 0.0,
            "high_y": 1.0,
        }
        for x, y in ((2, 2), (3, 3), (4, 4), (6, 6), (8, 8))
    ),
    "path_summary": tuple(
        {"measure": measure}
        for measure in (
            "length",
            "centroid_x",
            "centroid_y",
            "is_loop",
            "branch_endpoints",
        )
    ),
    "spatial_split": tuple(
        {"rows": rows, "cols": cols}
        for rows, cols in ((1, 2), (1, 3), (2, 2), (2, 3), (3, 3), (4, 4))
    ),
    "ratio": tuple({"epsilon": value} for value in (1e-6, 1e-4, 1e-2)),
}


def parameter_presets(op: str) -> tuple[dict[str, object], ...]:
    return _PARAMETER_PRESETS.get(op, ({},))


def _possible(
    value_type: ValueType,
    remaining_depth: int,
    *,
    constraints: ProgramConstraints,
    memo: dict[tuple[ValueType, int], bool],
) -> bool:
    key = (value_type, remaining_depth)
    if key in memo:
        return memo[key]
    if value_type is ValueType.IMAGE:
        memo[key] = True
        return True
    if remaining_depth <= 0:
        memo[key] = False
        return False
    for op, definition in PRIMITIVES.items():
        if op == "flatten_pixels" and (
            constraints.track.value == "discovery" or constraints.forbid_raw_pixels
        ):
            continue
        if definition.output_type is not value_type:
            continue
        if _definition_completes(
            definition,
            remaining_depth - 1,
            constraints=constraints,
            memo=memo,
        ):
            memo[key] = True
            return True
    memo[key] = False
    return False


def _definition_completes(
    definition: PrimitiveDefinition,
    child_depth: int,
    *,
    constraints: ProgramConstraints,
    memo: dict[tuple[ValueType, int], bool],
) -> bool:
    if definition.variadic_input is not None:
        return any(
            _possible(item, child_depth, constraints=constraints, memo=memo)
            for item in definition.variadic_input
        )
    return all(
        any(
            _possible(item, child_depth, constraints=constraints, memo=memo)
            for item in accepted
        )
        for accepted in definition.input_types
    )


def _build(
    value_type: ValueType,
    remaining_depth: int,
    *,
    rng: random.Random,
    constraints: ProgramConstraints,
    memo: dict[tuple[ValueType, int], bool],
) -> Expr:
    if value_type is ValueType.IMAGE:
        return Expr("image")
    choices = [
        (op, definition)
        for op, definition in PRIMITIVES.items()
        if definition.output_type is value_type
        and not (
            op == "flatten_pixels"
            and (
                constraints.track.value == "discovery" or constraints.forbid_raw_pixels
            )
        )
        and remaining_depth > 0
        and _definition_completes(
            definition,
            remaining_depth - 1,
            constraints=constraints,
            memo=memo,
        )
    ]
    if not choices:
        raise SamplingFailure(
            f"no {value_type.value} expression fits depth {remaining_depth}"
        )
    op, definition = rng.choice(choices)
    if definition.variadic_input is not None:
        child_count = rng.choice((2, 3))
        accepted_types = [definition.variadic_input] * child_count
    else:
        accepted_types = list(definition.input_types)
    args = []
    for accepted in accepted_types:
        child_types = [
            item
            for item in sorted(accepted, key=lambda item: item.value)
            if _possible(
                item,
                remaining_depth - 1,
                constraints=constraints,
                memo=memo,
            )
        ]
        if not child_types:
            raise SamplingFailure(f"no legal child type for {op}")
        args.append(
            _build(
                rng.choice(child_types),
                remaining_depth - 1,
                rng=rng,
                constraints=constraints,
                memo=memo,
            )
        )
    params = rng.choice(parameter_presets(op))
    return Expr(op, tuple(args), params)


def sample_random_ast(
    rng: random.Random,
    *,
    constraints: ProgramConstraints,
    target_depth: int | None = None,
) -> Expr:
    """Sample a type-directed AST and return only programs accepted by V3 validation."""
    if not isinstance(rng, random.Random):
        raise TypeError("rng must be random.Random")
    if not isinstance(constraints, ProgramConstraints):
        raise TypeError("constraints must be ProgramConstraints")
    depth = target_depth if target_depth is not None else rng.randint(1, 6)
    if type(depth) is not int or not 1 <= depth <= constraints.max_depth:
        raise ValueError("target_depth must be between one and the frozen maximum")
    root_type = rng.choice((ValueType.VECTOR, ValueType.SCALAR))
    memo: dict[tuple[ValueType, int], bool] = {}
    program = _build(
        root_type,
        depth,
        rng=rng,
        constraints=constraints,
        memo=memo,
    )
    try:
        ProgramCompiler(constraints).compile(program)
    except (TypeError, ValueError) as exc:
        raise SamplingFailure(str(exc)) from exc
    return program


def sample_typed_subtree(
    rng: random.Random,
    value_type: ValueType,
    *,
    constraints: ProgramConstraints,
    target_depth: int,
) -> Expr:
    """Build a subtree with a requested output type for typed GP variation."""
    if not isinstance(value_type, ValueType):
        raise TypeError("value_type must be a ValueType")
    if type(target_depth) is not int or not 0 <= target_depth <= constraints.max_depth:
        raise ValueError("target_depth must be within the frozen depth limit")
    program = _build(
        value_type,
        target_depth,
        rng=rng,
        constraints=constraints,
        memo={},
    )
    try:
        actual_type = infer_type(program).value_type
    except (TypeError, ValueError) as exc:
        raise SamplingFailure(str(exc)) from exc
    if actual_type is not value_type:
        raise SamplingFailure("typed subtree generator returned the wrong type")
    return program
