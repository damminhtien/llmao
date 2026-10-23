"""Canonical manifests for the frozen base and human-designed V3 languages."""

from __future__ import annotations

import hashlib
import inspect
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from bias_optimizer.dsl.primitives import PRIMITIVES, PrimitiveDefinition

V2_DSL_COMMIT = "cab3e82fecf82326bb49690c22f9233824d55eae"
V3_DSL_COMMIT = "1e9f29bd7f21863f84340b25e6b3e193c43d1220"
EXCLUDED_V3_OPERATIONS = (
    "cross_histogram",
    "pairwise_difference",
    "path_summary",
    "spatial_condition",
)

V2_PRIMITIVE_NAMES = (
    "angles",
    "autocorrelation",
    "connected_components",
    "concat",
    "count",
    "cycle_rank",
    "degree_sequence",
    "delta",
    "delta_angle",
    "edge_lengths",
    "flatten_pixels",
    "graph",
    "histogram",
    "image",
    "moments",
    "normalize",
    "paths",
    "quantiles",
    "ratio",
    "run_length_encode",
    "sign",
    "skeletonize",
    "spatial_split",
    "threshold",
)

_NO_PARAMS = {"type": "object", "properties": {}, "additionalProperties": False}
_PARAMETER_SCHEMAS: dict[str, dict[str, Any]] = {
    "image": _NO_PARAMS,
    "threshold": {
        "type": "object",
        "properties": {
            "value": {"type": "number", "default": 0.5, "minimum": 0, "maximum": 1}
        },
        "additionalProperties": False,
    },
    "skeletonize": {
        "type": "object",
        "properties": {
            "threshold": {
                "type": "number",
                "default": 0.5,
                "minimum": 0,
                "maximum": 1,
            }
        },
        "additionalProperties": False,
    },
    "graph": _NO_PARAMS,
    "connected_components": _NO_PARAMS,
    "cycle_rank": _NO_PARAMS,
    "paths": _NO_PARAMS,
    "degree_sequence": _NO_PARAMS,
    "edge_lengths": _NO_PARAMS,
    "angles": _NO_PARAMS,
    "path_summary": {
        "type": "object",
        "properties": {
            "measure": {
                "type": "string",
                "default": "length",
                "enum": ["length", "centroid_x", "centroid_y", "is_loop", "branch_endpoints"],
            }
        },
        "additionalProperties": False,
    },
    "delta": _NO_PARAMS,
    "delta_angle": _NO_PARAMS,
    "sign": {
        "type": "object",
        "properties": {
            "epsilon": {
                "type": "number",
                "default": 0,
                "minimum": 0,
                "maximum": 3.141592653589793,
            }
        },
        "additionalProperties": False,
    },
    "run_length_encode": _NO_PARAMS,
    "histogram": {
        "type": "object",
        "properties": {
            "bins": {"type": "integer", "default": 8, "minimum": 2, "maximum": 32},
            "low": {
                "type": "number",
                "default": -3.141592653589793,
                "minimum": -128,
                "maximum": 128,
            },
            "high": {
                "type": "number",
                "default": 3.141592653589793,
                "minimum": -128,
                "maximum": 128,
            },
        },
        "x-v4-constraints": ["low < high"],
        "additionalProperties": False,
    },
    "moments": {
        "type": "object",
        "properties": {
            "orders": {
                "type": "array",
                "default": [1, 2, 3],
                "minItems": 1,
                "items": {"type": "integer", "minimum": 1, "maximum": 8},
                "maxItems": 8,
                "uniqueItems": True,
            }
        },
        "additionalProperties": False,
    },
    "quantiles": {
        "type": "object",
        "properties": {
            "quantiles": {
                "type": "array",
                "default": [0.1, 0.25, 0.5, 0.75, 0.9],
                "minItems": 1,
                "items": {"type": "number", "minimum": 0, "maximum": 1},
                "maxItems": 16,
                "x-strictly-increasing": True,
            }
        },
        "additionalProperties": False,
    },
    "autocorrelation": {
        "type": "object",
        "properties": {
            "lags": {
                "type": "array",
                "default": [1, 2, 4],
                "minItems": 1,
                "items": {"type": "integer", "minimum": 1, "maximum": 32},
                "maxItems": 16,
                "x-strictly-increasing": True,
            }
        },
        "additionalProperties": False,
    },
    "spatial_condition": {
        "type": "object",
        "properties": {
            "axis": {"type": "string", "default": "vertical", "enum": ["vertical", "horizontal"]},
            "regions": {"type": "integer", "default": 3, "minimum": 1, "maximum": 16},
            "bins": {"type": "integer", "default": 8, "minimum": 2, "maximum": 16},
            "low": {
                "type": "number",
                "default": -3.141592653589793,
                "minimum": -128,
                "maximum": 128,
            },
            "high": {
                "type": "number",
                "default": 3.141592653589793,
                "minimum": -128,
                "maximum": 128,
            },
        },
        "x-v4-constraints": ["regions * bins <= 128", "low < high"],
        "additionalProperties": False,
    },
    "cross_histogram": {
        "type": "object",
        "properties": {
            "bins_x": {"type": "integer", "default": 6, "minimum": 2, "maximum": 11},
            "bins_y": {"type": "integer", "default": 6, "minimum": 2, "maximum": 11},
            "low_x": {
                "type": "number",
                "default": 0,
                "minimum": -128,
                "maximum": 128,
            },
            "high_x": {
                "type": "number",
                "default": 1,
                "minimum": -128,
                "maximum": 128,
            },
            "low_y": {
                "type": "number",
                "default": 0,
                "minimum": -128,
                "maximum": 128,
            },
            "high_y": {
                "type": "number",
                "default": 1,
                "minimum": -128,
                "maximum": 128,
            },
        },
        "x-v4-constraints": [
            "bins_x * bins_y <= 128",
            "low_x < high_x",
            "low_y < high_y",
        ],
        "additionalProperties": False,
    },
    "normalize": _NO_PARAMS,
    "spatial_split": {
        "type": "object",
        "properties": {
            "rows": {"type": "integer", "default": 1, "minimum": 1, "maximum": 7},
            "cols": {"type": "integer", "default": 3, "minimum": 1, "maximum": 7},
        },
        "x-v4-constraints": ["rows * cols <= 64"],
        "additionalProperties": False,
    },
    "flatten_pixels": _NO_PARAMS,
    "ratio": {
        "type": "object",
        "properties": {
            "epsilon": {
                "type": "number",
                "default": 1e-6,
                "minimum": 1e-12,
                "maximum": 1,
            }
        },
        "additionalProperties": False,
    },
    "pairwise_difference": _NO_PARAMS,
    "count": _NO_PARAMS,
    "concat": _NO_PARAMS,
}

# Stable descriptions of the primitive dimension resolvers. Callable reprs are
# intentionally excluded from the canonical manifest because they are unstable.
_DIMENSION_RULES = {
    "image": "dynamic",
    "threshold": "dynamic",
    "skeletonize": "dynamic",
    "graph": "dynamic",
    "connected_components": "fixed:1",
    "cycle_rank": "fixed:1",
    "paths": "dynamic",
    "degree_sequence": "dynamic",
    "edge_lengths": "dynamic",
    "angles": "dynamic",
    "path_summary": "dynamic",
    "delta": "dynamic",
    "delta_angle": "dynamic",
    "sign": "dynamic",
    "run_length_encode": "dynamic",
    "histogram": "parameter:bins",
    "moments": "parameter:len(orders)",
    "quantiles": "parameter:len(quantiles)",
    "autocorrelation": "parameter:len(lags)",
    "spatial_condition": "parameter:regions*bins",
    "cross_histogram": "parameter:bins_x*bins_y",
    "normalize": "same_as:first_input",
    "spatial_split": "parameter:rows*cols",
    "flatten_pixels": "fixed:784",
    "ratio": "same_as:first_input",
    "pairwise_difference": "same_as:first_input",
    "count": "fixed:1",
    "concat": "sum:input_dimensions",
}


@dataclass(frozen=True, slots=True)
class PrimitiveSignature:
    """Canonical, JSON-ready signature and parameter schema for one primitive."""

    name: str
    input_types: tuple[tuple[str, ...], ...]
    output_type: str
    output_dimension_rule: str
    parameters_json: str
    family: str | None
    variadic_input_types: tuple[str, ...] | None
    minimum_args: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "input_types": [list(types) for types in self.input_types],
            "output_type": self.output_type,
            "output_dimension_rule": self.output_dimension_rule,
            "parameter_schema": json.loads(self.parameters_json),
            "family": self.family,
            "variadic_input_types": (
                list(self.variadic_input_types)
                if self.variadic_input_types is not None
                else None
            ),
            "minimum_args": self.minimum_args,
        }


@dataclass(frozen=True, slots=True)
class LanguageManifest:
    """Immutable language definition with a canonical SHA-256 identity."""

    name: str
    basis_commit: str
    excluded_operations: tuple[str, ...]
    primitive_source_sha256: str
    primitives: tuple[PrimitiveSignature, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "language": self.name,
            "basis_commit": self.basis_commit,
            "excluded_operations": list(self.excluded_operations),
            "primitive_source_sha256": self.primitive_source_sha256,
            "primitives": [primitive.to_dict() for primitive in self.primitives],
        }

    @property
    def canonical_json(self) -> str:
        return json.dumps(
            self.to_dict(), sort_keys=True, separators=(",", ":"), allow_nan=False
        )

    @property
    def sha256(self) -> str:
        return hashlib.sha256(self.canonical_json.encode("utf-8")).hexdigest()


def _primitive_source_sha256() -> str:
    source = inspect.getsourcefile(PrimitiveDefinition)
    if source is None:
        raise RuntimeError("cannot resolve the frozen primitive source file")
    return hashlib.sha256(Path(source).read_bytes()).hexdigest()


def _signature(name: str, definition: PrimitiveDefinition) -> PrimitiveSignature:
    schema = _PARAMETER_SCHEMAS.get(name)
    if schema is None:
        raise ValueError(f"missing V4 parameter schema for primitive {name!r}")
    return PrimitiveSignature(
        name=name,
        input_types=tuple(
            tuple(sorted(value_type.value for value_type in accepted))
            for accepted in definition.input_types
        ),
        output_type=definition.output_type.value,
        output_dimension_rule=_DIMENSION_RULES[name],
        parameters_json=json.dumps(
            schema, sort_keys=True, separators=(",", ":"), allow_nan=False
        ),
        family=definition.family,
        variadic_input_types=(
            tuple(sorted(value_type.value for value_type in definition.variadic_input))
            if definition.variadic_input is not None
            else None
        ),
        minimum_args=definition.minimum_args,
    )


def _build_language(
    *,
    name: str,
    basis_commit: str,
    primitive_names: tuple[str, ...],
    excluded_operations: tuple[str, ...] = (),
) -> LanguageManifest:
    if len(primitive_names) != len(set(primitive_names)):
        raise RuntimeError("language primitive names must be unique")
    unknown = set(primitive_names) - set(PRIMITIVES)
    if unknown:
        raise RuntimeError(f"language contains unknown primitives: {sorted(unknown)}")
    if set(_PARAMETER_SCHEMAS) != set(PRIMITIVES):
        raise RuntimeError("V4 parameter schemas do not cover the primitive registry")
    if set(_DIMENSION_RULES) != set(PRIMITIVES):
        raise RuntimeError("V4 dimension rules do not cover the primitive registry")
    return LanguageManifest(
        name=name,
        basis_commit=basis_commit,
        excluded_operations=excluded_operations,
        primitive_source_sha256=_primitive_source_sha256(),
        primitives=tuple(
            _signature(operation, PRIMITIVES[operation])
            for operation in primitive_names
        ),
    )


def build_g0_language() -> LanguageManifest:
    """Build the V2-level vocabulary without mutating the V3 registry."""
    expected_registry = set(V2_PRIMITIVE_NAMES) | set(EXCLUDED_V3_OPERATIONS)
    if set(PRIMITIVES) != expected_registry:
        raise RuntimeError("current primitive registry differs from the pinned V2/V3 set")
    return _build_language(
        name="G0",
        basis_commit=V2_DSL_COMMIT,
        primitive_names=V2_PRIMITIVE_NAMES,
        excluded_operations=EXCLUDED_V3_OPERATIONS,
    )


def build_gh_language() -> LanguageManifest:
    """Build the complete frozen human-designed V3 vocabulary."""
    primitive_names = tuple(sorted(PRIMITIVES))
    return _build_language(
        name="GH",
        basis_commit=V3_DSL_COMMIT,
        primitive_names=primitive_names,
    )


G0_LANGUAGE = build_g0_language()
GH_LANGUAGE = build_gh_language()
