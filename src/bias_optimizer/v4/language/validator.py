"""Validation, hashing, and expansion for G0-based typed macro languages."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from math import isfinite
from typing import Any

from bias_optimizer.dsl.ast import Expr
from bias_optimizer.dsl.primitives import PRIMITIVES
from bias_optimizer.dsl.types import TypeInfo, ValueType
from bias_optimizer.dsl.validator import (
    ProgramConstraints,
    SearchTrack,
    infer_type,
    validate_program,
)
from bias_optimizer.v4.language.base_language import G0_LANGUAGE, LanguageManifest
from bias_optimizer.v4.language.macro import (
    InputRef,
    MacroBody,
    MacroBodyCall,
    MacroPrimitive,
    MacroValidationError,
    ParameterRef,
)

_SCHEMA_KEYS = {
    "type",
    "properties",
    "additionalProperties",
}
_PROPERTY_SCHEMA_KEYS = {
    "type",
    "default",
    "enum",
    "minimum",
    "maximum",
    "exclusiveMinimum",
    "exclusiveMaximum",
    "minItems",
    "maxItems",
    "items",
    "uniqueItems",
}
_SCALAR_TYPES = {"number", "integer", "string", "boolean", "null"}


@dataclass(frozen=True, slots=True)
class MacroLimits:
    """Hard limits on language size and expanded representation ASTs."""

    max_expansion_depth: int = 6
    max_expanded_nodes: int = 127
    max_feature_dim: int = 128
    max_macros: int = 8
    max_new_macros_per_candidate: int = 1

    def __post_init__(self) -> None:
        for name in (
            "max_expansion_depth",
            "max_expanded_nodes",
            "max_feature_dim",
            "max_macros",
            "max_new_macros_per_candidate",
        ):
            value = getattr(self, name)
            if type(value) is not int or value <= 0:
                raise ValueError(f"{name} must be a positive integer")

    def to_dict(self) -> dict[str, int]:
        return {
            "max_expansion_depth": self.max_expansion_depth,
            "max_expanded_nodes": self.max_expanded_nodes,
            "max_feature_dim": self.max_feature_dim,
            "max_macros": self.max_macros,
            "max_new_macros_per_candidate": self.max_new_macros_per_candidate,
        }


@dataclass(frozen=True, slots=True)
class MacroLanguage:
    """A hashable language descended from G0 with an acyclic macro inventory."""

    parent_language_hash: str
    base_language: LanguageManifest
    macros: tuple[MacroPrimitive, ...]
    introduced_macros: tuple[str, ...]
    limits: MacroLimits

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "language": "G*",
            "parent_language_hash": self.parent_language_hash,
            "base_language_hash": self.base_language.sha256,
            "limits": self.limits.to_dict(),
            "introduced_macros": list(self.introduced_macros),
            "macros": [macro.to_dict() for macro in self.macros],
        }

    @property
    def canonical_json(self) -> str:
        return json.dumps(
            self.to_dict(), sort_keys=True, separators=(",", ":"), allow_nan=False
        )

    @property
    def sha256(self) -> str:
        return hashlib.sha256(self.canonical_json.encode("utf-8")).hexdigest()

    @property
    def macro_map(self) -> dict[str, MacroPrimitive]:
        return {macro.name: macro for macro in self.macros}


@dataclass(frozen=True, slots=True)
class CandidateExpansion:
    """Validated base-language program and provenance summaries."""

    expanded_ast: Expr
    info: TypeInfo
    program_hash: str
    expanded_program_hash: str
    used_macros: tuple[str, ...]
    used_primitives: tuple[str, ...]


def _plain(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _plain(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_plain(item) for item in value]
    return value


def _schema_properties(schema: Mapping[str, Any], macro_name: str) -> Mapping[str, Any]:
    schema = _plain(schema)
    if (
        not isinstance(schema, dict)
        or set(schema) - _SCHEMA_KEYS
        or schema.get("type") != "object"
        or schema.get("additionalProperties") is not False
    ):
        raise MacroValidationError(
            f"macro {macro_name!r} parameters need a closed object schema"
        )
    properties = schema.get("properties", {})
    if not isinstance(properties, dict):
        raise MacroValidationError("macro parameter properties must be an object")
    for name, property_schema in properties.items():
        if (
            not isinstance(name, str)
            or not name
            or not name.isascii()
            or not name.replace("_", "").isalnum()
            or name.lower() != name
        ):
            raise MacroValidationError(
                "macro parameter names must be lowercase identifiers"
            )
        if not isinstance(property_schema, dict):
            raise MacroValidationError(f"schema for parameter {name!r} must be an object")
        if set(property_schema) - _PROPERTY_SCHEMA_KEYS:
            raise MacroValidationError(f"unsupported schema keywords for parameter {name!r}")
        if "default" not in property_schema:
            raise MacroValidationError(
                f"macro parameter {name!r} needs a default for static expansion"
            )
        _validate_property_schema(property_schema, name)
        _validate_value(property_schema["default"], property_schema, name)
    return properties


def _validate_property_schema(schema: Mapping[str, Any], name: str) -> None:
    schema_type = schema.get("type")
    if schema_type not in _SCALAR_TYPES | {"array"}:
        raise MacroValidationError(f"unsupported type for macro parameter {name!r}")
    if schema_type == "array":
        item_schema = schema.get("items")
        if not isinstance(item_schema, dict):
            raise MacroValidationError(f"array parameter {name!r} needs an items schema")
        if set(item_schema) - (_PROPERTY_SCHEMA_KEYS - {"default"}):
            raise MacroValidationError(f"unsupported item schema for parameter {name!r}")
        _validate_property_schema(item_schema, f"{name}[]")
    elif "items" in schema or "minItems" in schema or "maxItems" in schema:
        raise MacroValidationError(f"array constraints require an array parameter: {name!r}")
    for key in ("minimum", "maximum", "exclusiveMinimum", "exclusiveMaximum"):
        if key in schema and (
            type(schema[key]) not in (int, float) or not isfinite(schema[key])
        ):
            raise MacroValidationError(f"{key} for parameter {name!r} must be finite")
    if schema_type not in {"number", "integer"} and any(
        key in schema
        for key in ("minimum", "maximum", "exclusiveMinimum", "exclusiveMaximum")
    ):
        raise MacroValidationError(f"numeric bounds require a numeric parameter: {name!r}")
    for key in ("minItems", "maxItems"):
        if key in schema and (type(schema[key]) is not int or schema[key] < 0):
            raise MacroValidationError(f"{key} for parameter {name!r} must be non-negative")
    if "uniqueItems" in schema and type(schema["uniqueItems"]) is not bool:
        raise MacroValidationError(f"uniqueItems for parameter {name!r} must be boolean")
    if "enum" in schema and (
        not isinstance(schema["enum"], list) or not schema["enum"]
    ):
        raise MacroValidationError(f"enum for parameter {name!r} must be non-empty")
    if "enum" in schema:
        unconstrained = {key: value for key, value in schema.items() if key != "enum"}
        for item in schema["enum"]:
            _validate_value(item, unconstrained, name)
    if (
        "minItems" in schema
        and "maxItems" in schema
        and schema["minItems"] > schema["maxItems"]
    ):
        raise MacroValidationError(f"array item bounds conflict for parameter {name!r}")
    if (
        "minimum" in schema
        and "maximum" in schema
        and schema["minimum"] > schema["maximum"]
    ):
        raise MacroValidationError(f"numeric bounds conflict for parameter {name!r}")


def _validate_value(value: Any, schema: Mapping[str, Any], name: str) -> None:
    value = _plain(value)
    schema_type = schema["type"]
    valid = {
        "number": type(value) in (int, float) and isfinite(value),
        "integer": type(value) is int,
        "string": isinstance(value, str),
        "boolean": type(value) is bool,
        "null": value is None,
        "array": isinstance(value, list),
    }[schema_type]
    if not valid:
        raise MacroValidationError(
            f"macro parameter {name!r} must have type {schema_type}"
        )
    if "enum" in schema and value not in schema["enum"]:
        raise MacroValidationError(f"macro parameter {name!r} is outside its enum")
    if schema_type in {"number", "integer"}:
        checks = (
            ("minimum", lambda number, bound: number >= bound),
            ("maximum", lambda number, bound: number <= bound),
            ("exclusiveMinimum", lambda number, bound: number > bound),
            ("exclusiveMaximum", lambda number, bound: number < bound),
        )
        for key, check in checks:
            if key in schema and not check(value, schema[key]):
                raise MacroValidationError(f"macro parameter {name!r} violates {key}")
    elif schema_type == "array":
        if "minItems" in schema and len(value) < schema["minItems"]:
            raise MacroValidationError(f"macro parameter {name!r} has too few items")
        if "maxItems" in schema and len(value) > schema["maxItems"]:
            raise MacroValidationError(f"macro parameter {name!r} has too many items")
        item_schema = schema["items"]
        for item in value:
            _validate_value(item, item_schema, f"{name}[]")
        if schema.get("uniqueItems") and len({_json(item) for item in value}) != len(value):
            raise MacroValidationError(f"macro parameter {name!r} items must be unique")


def _json(value: Any) -> str:
    return json.dumps(_plain(value), sort_keys=True, separators=(",", ":"), allow_nan=False)


def _normalize_parameters(
    macro: MacroPrimitive, supplied: Mapping[str, Any]
) -> dict[str, Any]:
    if not isinstance(supplied, Mapping):
        raise MacroValidationError(f"parameters for macro {macro.name!r} must be an object")
    properties = _schema_properties(macro.parameters, macro.name)
    unknown = set(supplied) - set(properties)
    if unknown:
        raise MacroValidationError(
            f"unknown parameters for macro {macro.name!r}: {sorted(unknown)}"
        )
    normalized: dict[str, Any] = {}
    for name, schema in properties.items():
        value = supplied[name] if name in supplied else schema["default"]
        _validate_value(value, schema, name)
        normalized[name] = _plain(value)
    return normalized


def _substitute_parameters(value: Any, values: Mapping[str, Any]) -> Any:
    if isinstance(value, ParameterRef):
        if value.name not in values:
            raise MacroValidationError(f"unbound macro parameter {value.name!r}")
        return values[value.name]
    if isinstance(value, InputRef):
        raise MacroValidationError("input references cannot appear in operation parameters")
    if isinstance(value, Mapping):
        return {
            key: _substitute_parameters(item, values) for key, item in value.items()
        }
    if isinstance(value, tuple):
        return [_substitute_parameters(item, values) for item in value]
    return value


def _body_references(body: MacroBody):
    if isinstance(body, InputRef):
        yield ("input", body.index)
        return
    yield ("op", body.op)
    for value in body.params.values():
        yield from _value_references(value)
    for argument in body.args:
        yield from _body_references(argument)


def _value_references(value: Any):
    if isinstance(value, ParameterRef):
        yield ("parameter", value.name)
    elif isinstance(value, InputRef):
        yield ("invalid_input_parameter", value.index)
    elif isinstance(value, Mapping):
        for item in value.values():
            yield from _value_references(item)
    elif isinstance(value, tuple):
        for item in value:
            yield from _value_references(item)


def _validate_references(
    macro: MacroPrimitive,
    macros: Mapping[str, MacroPrimitive],
    base_names: frozenset[str],
) -> set[str]:
    properties = _schema_properties(macro.parameters, macro.name)
    dependencies: set[str] = set()
    for kind, value in _body_references(macro.body_ast):
        if kind == "input" and value >= len(macro.input_types):
            raise MacroValidationError(
                f"macro {macro.name!r} references missing input {value}"
            )
        if kind == "parameter" and value not in properties:
            raise MacroValidationError(
                f"macro {macro.name!r} references undeclared parameter {value!r}"
            )
        if kind == "invalid_input_parameter":
            raise MacroValidationError("input references cannot appear in operation parameters")
        if kind == "op":
            if value in base_names:
                continue
            if value not in macros:
                raise MacroValidationError(
                    f"macro {macro.name!r} calls operation outside its language: {value!r}"
                )
            dependencies.add(value)
    return dependencies


def _assert_acyclic(dependencies: Mapping[str, set[str]]) -> None:
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(name: str) -> None:
        if name in visiting:
            raise MacroValidationError(f"recursive macro dependency involving {name!r}")
        if name in visited:
            return
        visiting.add(name)
        for dependency in dependencies[name]:
            visit(dependency)
        visiting.remove(name)
        visited.add(name)

    for name in dependencies:
        visit(name)


def _macro_dependency_depths(dependencies: Mapping[str, set[str]]) -> dict[str, int]:
    depths: dict[str, int] = {}

    def depth(name: str) -> int:
        if name not in depths:
            depths[name] = 1 + max(
                (depth(dependency) for dependency in dependencies[name]),
                default=0,
            )
        return depths[name]

    for name in dependencies:
        depth(name)
    return depths


def _input_info(value_type: ValueType) -> TypeInfo:
    dimension = 1 if value_type in {ValueType.VECTOR, ValueType.SCALAR} else None
    return TypeInfo(
        value_type=value_type,
        dimension=dimension,
        depth=0,
        node_count=1,
        operations=frozenset(),
    )


def _infer_body(
    body: MacroBody,
    *,
    input_infos: tuple[TypeInfo, ...],
    parameters: Mapping[str, Any],
    macros: Mapping[str, MacroPrimitive],
    base_names: frozenset[str],
    stack: tuple[str, ...],
) -> TypeInfo:
    if isinstance(body, InputRef):
        try:
            return input_infos[body.index]
        except IndexError as exc:
            raise MacroValidationError(f"macro input index {body.index} is out of range") from exc

    children = tuple(
        _infer_body(
            argument,
            input_infos=input_infos,
            parameters=parameters,
            macros=macros,
            base_names=base_names,
            stack=stack,
        )
        for argument in body.args
    )
    supplied = _substitute_parameters(body.params, parameters)
    if body.op in macros:
        target = macros[body.op]
        if body.op in stack:
            raise MacroValidationError(f"recursive macro call involving {body.op!r}")
        _check_macro_inputs(target, children)
        target_parameters = _normalize_parameters(target, supplied)
        return _infer_macro_body(
            target,
            children,
            target_parameters,
            macros,
            base_names,
            stack + (target.name,),
        )
    if body.op not in base_names:
        raise MacroValidationError(f"unknown operation {body.op!r} in macro body")
    definition = PRIMITIVES[body.op]
    try:
        definition.validate_inputs(tuple(child.value_type for child in children))
        definition.validate_params(supplied)
        dimension = definition.output_dimension(children, supplied)
    except (TypeError, ValueError) as exc:
        raise MacroValidationError(f"invalid {body.op!r} call in macro body: {exc}") from exc
    return TypeInfo(
        value_type=definition.output_type,
        dimension=dimension,
        depth=1 + max((child.depth for child in children), default=0),
        node_count=1 + sum(child.node_count for child in children),
        operations=frozenset({body.op}).union(
            *(child.operations for child in children)
        ),
    )


def _check_macro_inputs(
    macro: MacroPrimitive, inputs: Sequence[TypeInfo]
) -> None:
    if len(inputs) != len(macro.input_types):
        raise MacroValidationError(
            f"macro {macro.name!r} requires {len(macro.input_types)} arguments"
        )
    for index, (actual, expected) in enumerate(
        zip(inputs, macro.input_types, strict=True)
    ):
        if actual.value_type is not expected:
            raise MacroValidationError(
                f"macro {macro.name!r} input {index} expects {expected.value}, "
                f"got {actual.value_type.value}"
            )


def _infer_macro_body(
    macro: MacroPrimitive,
    input_infos: tuple[TypeInfo, ...],
    parameters: Mapping[str, Any],
    macros: Mapping[str, MacroPrimitive],
    base_names: frozenset[str],
    stack: tuple[str, ...],
) -> TypeInfo:
    info = _infer_body(
        macro.body_ast,
        input_infos=input_infos,
        parameters=parameters,
        macros=macros,
        base_names=base_names,
        stack=stack,
    )
    if info.value_type is not macro.output_type:
        raise MacroValidationError(
            f"macro {macro.name!r} declares {macro.output_type.value} but returns "
            f"{info.value_type.value}"
        )
    return info


def _inline_template(
    body: MacroBody,
    *,
    macro: MacroPrimitive,
    input_bindings: tuple[MacroBody, ...],
    parameters: Mapping[str, Any],
    macros: Mapping[str, MacroPrimitive],
    base_names: frozenset[str],
    stack: tuple[str, ...],
) -> MacroBody:
    if isinstance(body, InputRef):
        return input_bindings[body.index]
    arguments = tuple(
        _inline_template(
            argument,
            macro=macro,
            input_bindings=input_bindings,
            parameters=parameters,
            macros=macros,
            base_names=base_names,
            stack=stack,
        )
        for argument in body.args
    )
    supplied = _substitute_parameters(body.params, parameters)
    if body.op in base_names:
        return MacroBodyCall(body.op, arguments, supplied)
    target = macros[body.op]
    if target.name in stack:
        raise MacroValidationError(f"recursive macro call involving {target.name!r}")
    target_parameters = _template_parameters(target, supplied)
    return _inline_template(
        target.body_ast,
        macro=target,
        input_bindings=arguments,
        parameters=target_parameters,
        macros=macros,
        base_names=base_names,
        stack=stack + (target.name,),
    )


def _template_parameters(
    macro: MacroPrimitive, supplied: Mapping[str, Any]
) -> dict[str, Any]:
    properties = _schema_properties(macro.parameters, macro.name)
    unknown = set(supplied) - set(properties)
    if unknown:
        raise MacroValidationError(
            f"unknown parameters for macro {macro.name!r}: {sorted(unknown)}"
        )
    return {
        name: supplied[name] if name in supplied else schema["default"]
        for name, schema in properties.items()
    }


def _macro_behavior_hash(
    macro: MacroPrimitive,
    macros: Mapping[str, MacroPrimitive],
    base_names: frozenset[str],
) -> str:
    properties = _schema_properties(macro.parameters, macro.name)
    symbolic_parameters = {name: ParameterRef(name) for name in properties}
    expanded_body = _inline_template(
        macro.body_ast,
        macro=macro,
        input_bindings=tuple(InputRef(index) for index in range(len(macro.input_types))),
        parameters=symbolic_parameters,
        macros=macros,
        base_names=base_names,
        stack=(macro.name,),
    )
    material = {
        "input_types": [value_type.value for value_type in macro.input_types],
        "output_type": macro.output_type.value,
        "parameters": _plain(macro.parameters),
        "expanded_body_ast": expanded_body.to_dict(),
    }
    digest = hashlib.sha256(_json(material).encode("utf-8")).hexdigest()
    return digest


def extend_macro_language(
    parent: LanguageManifest | MacroLanguage,
    new_macros: Sequence[MacroPrimitive],
    *,
    limits: MacroLimits | None = None,
) -> MacroLanguage:
    """Validate and freeze an acyclic set of macros descended from G0."""
    if isinstance(parent, MacroLanguage):
        base_language = parent.base_language
        inherited = parent.macros
        parent_hash = parent.sha256
        selected_limits = limits or parent.limits
        if (
            selected_limits.max_expansion_depth > parent.limits.max_expansion_depth
            or selected_limits.max_expanded_nodes > parent.limits.max_expanded_nodes
            or selected_limits.max_feature_dim > parent.limits.max_feature_dim
            or selected_limits.max_macros > parent.limits.max_macros
            or selected_limits.max_new_macros_per_candidate
            > parent.limits.max_new_macros_per_candidate
        ):
            raise MacroValidationError("a child language cannot widen its parent limits")
    else:
        base_language = parent
        inherited = ()
        parent_hash = parent.sha256
        selected_limits = limits or MacroLimits()
    if base_language.sha256 != G0_LANGUAGE.sha256:
        raise MacroValidationError("V4 Level A macro languages must descend from G0")

    additions = tuple(new_macros)
    if not all(isinstance(macro, MacroPrimitive) for macro in additions):
        raise MacroValidationError("new language entries must be MacroPrimitive values")
    all_macros = inherited + additions
    if len(additions) > selected_limits.max_new_macros_per_candidate:
        raise MacroValidationError(
            "candidate adds "
            f"{len(additions)} macros; limit is "
            f"{selected_limits.max_new_macros_per_candidate}"
        )
    if len(all_macros) > selected_limits.max_macros:
        raise MacroValidationError(
            f"language defines {len(all_macros)} macros; "
            f"limit is {selected_limits.max_macros}"
        )
    names = [macro.name for macro in all_macros]
    if len(names) != len(set(names)):
        raise MacroValidationError("macro names must be unique across a language lineage")
    base_names = frozenset(primitive.name for primitive in base_language.primitives)
    if set(names) & base_names:
        raise MacroValidationError("macro names cannot replace base-language primitives")
    macro_map = {macro.name: macro for macro in all_macros}
    dependencies = {
        macro.name: _validate_references(macro, macro_map, base_names)
        for macro in all_macros
    }
    _assert_acyclic(dependencies)
    for macro_name, depth in _macro_dependency_depths(dependencies).items():
        if depth > selected_limits.max_expansion_depth:
            raise MacroValidationError(
                f"macro {macro_name!r} expansion chain has depth {depth}; "
                f"limit is {selected_limits.max_expansion_depth}"
            )

    for macro in all_macros:
        _schema_properties(macro.parameters, macro.name)
        parameters = _normalize_parameters(macro, {})
        inputs = tuple(_input_info(value_type) for value_type in macro.input_types)
        info = _infer_macro_body(
            macro,
            inputs,
            parameters,
            macro_map,
            base_names,
            (macro.name,),
        )
        if info.depth > selected_limits.max_expansion_depth:
            raise MacroValidationError(
                f"macro {macro.name!r} expands to depth {info.depth}; "
                f"limit is {selected_limits.max_expansion_depth}"
            )
        if info.node_count > selected_limits.max_expanded_nodes:
            raise MacroValidationError(
                f"macro {macro.name!r} expands to {info.node_count} nodes; "
                f"limit is {selected_limits.max_expanded_nodes}"
            )
        if info.dimension is not None and info.dimension > selected_limits.max_feature_dim:
            raise MacroValidationError(
                f"macro {macro.name!r} expands to {info.dimension} features; "
                f"limit is {selected_limits.max_feature_dim}"
            )

    behavior_hashes = {
        macro.name: _macro_behavior_hash(macro, macro_map, base_names)
        for macro in all_macros
    }
    seen_hashes: dict[str, str] = {}
    for macro_name, behavior_hash in behavior_hashes.items():
        prior_name = seen_hashes.get(behavior_hash)
        if prior_name is not None:
            raise MacroValidationError(
                f"macro {macro_name!r} duplicates behavior of {prior_name!r}"
            )
        seen_hashes[behavior_hash] = macro_name

    return MacroLanguage(
        parent_language_hash=parent_hash,
        base_language=base_language,
        macros=tuple(sorted(all_macros, key=lambda macro: macro.name)),
        introduced_macros=tuple(sorted(macro.name for macro in additions)),
        limits=selected_limits,
    )


def _expand_body(
    body: MacroBody,
    *,
    bindings: tuple[Expr, ...],
    parameters: Mapping[str, Any],
    language: MacroLanguage,
    used_macros: set[str],
    stack: tuple[str, ...],
) -> Expr:
    if isinstance(body, InputRef):
        try:
            return bindings[body.index]
        except IndexError as exc:
            raise MacroValidationError(f"macro input index {body.index} is out of range") from exc

    args = tuple(
        _expand_body(
            argument,
            bindings=bindings,
            parameters=parameters,
            language=language,
            used_macros=used_macros,
            stack=stack,
        )
        for argument in body.args
    )
    supplied = _substitute_parameters(body.params, parameters)
    base_names = frozenset(
        primitive.name for primitive in language.base_language.primitives
    )
    if body.op in base_names:
        return Expr(body.op, args, supplied)
    macro = language.macro_map.get(body.op)
    if macro is None:
        raise MacroValidationError(f"operation {body.op!r} is outside the macro language")
    return _expand_macro_call(
        macro,
        args,
        supplied,
        language=language,
        used_macros=used_macros,
        stack=stack,
    )


def _expand_macro_call(
    macro: MacroPrimitive,
    args: tuple[Expr, ...],
    supplied: Mapping[str, Any],
    *,
    language: MacroLanguage,
    used_macros: set[str],
    stack: tuple[str, ...],
) -> Expr:
    if macro.name in stack:
        raise MacroValidationError(f"recursive macro expansion involving {macro.name!r}")
    if len(stack) >= language.limits.max_expansion_depth:
        raise MacroValidationError(
            f"macro expansion chain exceeds depth "
            f"{language.limits.max_expansion_depth}"
        )
    try:
        input_infos = tuple(infer_type(argument) for argument in args)
    except (TypeError, ValueError) as exc:
        raise MacroValidationError(
            f"macro {macro.name!r} received an invalid input: {exc}"
        ) from exc
    _check_macro_inputs(macro, input_infos)
    parameters = _normalize_parameters(macro, supplied)
    used_macros.add(macro.name)
    expanded = _expand_body(
        macro.body_ast,
        bindings=args,
        parameters=parameters,
        language=language,
        used_macros=used_macros,
        stack=stack + (macro.name,),
    )
    try:
        info = infer_type(expanded)
    except (TypeError, ValueError) as exc:
        raise MacroValidationError(
            f"macro {macro.name!r} expands to an invalid typed AST: {exc}"
        ) from exc
    if info.value_type is not macro.output_type:
        raise MacroValidationError(
            f"macro {macro.name!r} expands to {info.value_type.value}, "
            f"expected {macro.output_type.value}"
        )
    return expanded


def _operation_names(expr: Expr) -> set[str]:
    names = {expr.op}
    for argument in expr.args:
        names.update(_operation_names(argument))
    return names


def expand_candidate(
    program: Expr,
    language: MacroLanguage,
    *,
    introduced_macros: Sequence[str] | None = None,
) -> CandidateExpansion:
    """Validate macro calls and return a bounded canonical base-language AST."""
    if not isinstance(program, Expr):
        raise TypeError("candidate program must be an Expr")
    macro_map = language.macro_map
    base_names = frozenset(
        primitive.name for primitive in language.base_language.primitives
    )
    used_macros: set[str] = set()

    def expand_expression(expr: Expr) -> Expr:
        arguments = tuple(expand_expression(argument) for argument in expr.args)
        if expr.op in base_names:
            return Expr(expr.op, arguments, expr.params)
        macro = macro_map.get(expr.op)
        if macro is None:
            raise MacroValidationError(
                f"candidate operation {expr.op!r} is outside language G*"
            )
        return _expand_macro_call(
            macro,
            arguments,
            expr.parameter_values,
            language=language,
            used_macros=used_macros,
            stack=(),
        )

    expanded = expand_expression(program)
    expanded_operations = _operation_names(expanded)
    if not expanded_operations <= base_names:
        unknown = sorted(expanded_operations - base_names)
        raise MacroValidationError(f"expanded AST contains non-G0 operations: {unknown}")
    limits = language.limits
    constraints = ProgramConstraints(
        track=SearchTrack.DISCOVERY,
        max_feature_dim=limits.max_feature_dim,
        max_depth=limits.max_expansion_depth,
        max_nodes=limits.max_expanded_nodes,
    )
    try:
        info = validate_program(expanded, constraints)
    except (TypeError, ValueError) as exc:
        raise MacroValidationError(f"expanded candidate is invalid: {exc}") from exc

    introduced = (
        set(language.introduced_macros)
        if introduced_macros is None
        else set(introduced_macros)
    )
    unknown_introduced = introduced - set(macro_map)
    if unknown_introduced:
        raise MacroValidationError(
            f"introduced macros are missing from the language: {sorted(unknown_introduced)}"
        )
    unmarked_introduced = introduced - set(language.introduced_macros)
    if unmarked_introduced:
        raise MacroValidationError(
            "candidate introduction list is not part of this language revision: "
            f"{sorted(unmarked_introduced)}"
        )
    unused = introduced - used_macros
    if unused:
        raise MacroValidationError(
            f"candidate does not use newly introduced macros: {sorted(unused)}"
        )
    return CandidateExpansion(
        expanded_ast=expanded,
        info=info,
        program_hash=hashlib.sha256(program.to_json().encode("utf-8")).hexdigest(),
        expanded_program_hash=hashlib.sha256(
            expanded.to_json().encode("utf-8")
        ).hexdigest(),
        used_macros=tuple(sorted(used_macros)),
        used_primitives=tuple(sorted(set(info.operations) | used_macros)),
    )


def macro_behavior_hash(macro: MacroPrimitive, language: MacroLanguage) -> str:
    """Return a hash of a macro's fully inlined, parameterized computation."""
    try:
        return _macro_behavior_hash(
            macro,
            language.macro_map,
            frozenset(primitive.name for primitive in language.base_language.primitives),
        )
    except KeyError as exc:
        raise MacroValidationError(f"unknown macro reference {exc.args[0]!r}") from exc
