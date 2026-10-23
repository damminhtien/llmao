"""Immutable, data-only definitions for typed V4 macros."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from math import isfinite
from types import MappingProxyType
from typing import Any

from bias_optimizer.dsl.types import ValueType


class MacroValidationError(ValueError):
    """A macro definition or use violates the V4 language contract."""


@dataclass(frozen=True, slots=True)
class InputRef:
    """Reference one typed input to a macro body."""

    index: int

    def __post_init__(self) -> None:
        if type(self.index) is not int or self.index < 0:
            raise MacroValidationError("macro input references need a non-negative index")

    def to_dict(self) -> dict[str, int]:
        return {"input": self.index}


@dataclass(frozen=True, slots=True)
class ParameterRef:
    """Reference a declared macro parameter inside a body operation."""

    name: str

    def __post_init__(self) -> None:
        if not _is_identifier(self.name):
            raise MacroValidationError("macro parameter references need a valid name")

    def to_dict(self) -> dict[str, str]:
        return {"parameter": self.name}


def _is_identifier(value: object) -> bool:
    return (
        isinstance(value, str)
        and bool(value)
        and value.isascii()
        and value.replace("_", "").isalnum()
        and value.lower() == value
    )


def _freeze_template(value: Any) -> Any:
    if isinstance(value, (InputRef, ParameterRef)):
        return value
    if isinstance(value, Mapping):
        if not all(isinstance(key, str) for key in value):
            raise MacroValidationError("macro parameter keys must be strings")
        return MappingProxyType(
            {key: _freeze_template(item) for key, item in value.items()}
        )
    if isinstance(value, (list, tuple)):
        return tuple(_freeze_template(item) for item in value)
    if value is None or type(value) in (str, int, bool):
        return value
    if type(value) is float and isfinite(value):
        return value
    raise MacroValidationError(
        f"macro values must be finite JSON data or parameter references, got {type(value).__name__}"
    )


def _freeze_json(value: Any) -> Any:
    if isinstance(value, Mapping):
        if not all(isinstance(key, str) for key in value):
            raise MacroValidationError("macro schema keys must be strings")
        return MappingProxyType({key: _freeze_json(item) for key, item in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(_freeze_json(item) for item in value)
    if value is None or type(value) in (str, int, bool):
        return value
    if type(value) is float and isfinite(value):
        return value
    raise MacroValidationError("macro schemas must contain finite JSON values")


def _thaw(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _thaw(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw(item) for item in value]
    if isinstance(value, (InputRef, ParameterRef, MacroBodyCall)):
        return value.to_dict()
    return value


@dataclass(frozen=True, slots=True)
class MacroBodyCall:
    """A pure call in a macro template; operations are resolved by the validator."""

    op: str
    args: tuple[MacroBody, ...] = ()
    params: Mapping[str, MacroValue] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not _is_identifier(self.op):
            raise MacroValidationError("macro body operations need lowercase identifiers")
        args = tuple(self.args)
        if not all(isinstance(arg, (InputRef, MacroBodyCall)) for arg in args):
            raise MacroValidationError("macro body arguments must be input refs or calls")
        if not isinstance(self.params, Mapping):
            raise MacroValidationError("macro call parameters must be an object")
        frozen_params = _freeze_template(self.params)
        object.__setattr__(self, "args", args)
        object.__setattr__(self, "params", frozen_params)

    def to_dict(self) -> dict[str, Any]:
        return {
            "op": self.op,
            "args": [argument.to_dict() for argument in self.args],
            "params": _thaw(self.params),
        }


type MacroValue = Any
type MacroBody = InputRef | MacroBodyCall


def _parse_body(value: Mapping[str, Any], budget: list[int], depth: int) -> MacroBody:
    if depth > 128:
        raise MacroValidationError("macro body nesting exceeds 128")
    budget[0] += 1
    if budget[0] > 127:
        raise MacroValidationError("macro body exceeds the 127-node parser limit")
    if not isinstance(value, Mapping):
        raise MacroValidationError("macro body nodes must be objects")
    if set(value) == {"input"}:
        return InputRef(value["input"])
    if set(value) == {"parameter"}:
        return ParameterRef(value["parameter"])
    if set(value) - {"op", "args", "params"} or "op" not in value:
        raise MacroValidationError("macro body calls may contain only op, args, and params")
    args = value.get("args", [])
    params = value.get("params", {})
    if not isinstance(args, list) or not isinstance(params, Mapping):
        raise MacroValidationError("macro body args must be a list and params an object")
    parsed_args = tuple(_parse_body(argument, budget, depth + 1) for argument in args)
    parsed_params = _parse_template_value(params, [0], depth + 1)
    return MacroBodyCall(value["op"], parsed_args, parsed_params)


def _parse_template_value(value: Any, budget: list[int], depth: int) -> Any:
    if depth > 128:
        raise MacroValidationError("macro value nesting exceeds 128")
    budget[0] += 1
    if budget[0] > 127:
        raise MacroValidationError("macro body exceeds the 127-node parser limit")
    if isinstance(value, Mapping):
        if set(value) == {"input"}:
            return InputRef(value["input"])
        if set(value) == {"parameter"}:
            return ParameterRef(value["parameter"])
        return {
            key: _parse_template_value(item, budget, depth + 1)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_parse_template_value(item, budget, depth + 1) for item in value]
    return value


@dataclass(frozen=True, slots=True)
class MacroPrimitive:
    """A typed macro expressed only with input references and allow-listed calls."""

    name: str
    description: str
    input_types: tuple[ValueType, ...]
    output_type: ValueType
    parameters: Mapping[str, Any]
    body_ast: MacroBody

    def __post_init__(self) -> None:
        if not _is_identifier(self.name):
            raise MacroValidationError("macro names must be lowercase identifiers")
        if not isinstance(self.description, str) or not self.description.strip():
            raise MacroValidationError("macro description must be non-empty")
        if not isinstance(self.body_ast, (InputRef, MacroBodyCall)):
            raise MacroValidationError("macro body_ast must be a data-only macro AST")
        try:
            input_types = tuple(ValueType(value_type) for value_type in self.input_types)
            output_type = ValueType(self.output_type)
        except (TypeError, ValueError) as exc:
            raise MacroValidationError("macro signatures must use known ValueTypes") from exc
        if not isinstance(self.parameters, Mapping):
            raise MacroValidationError("macro parameters must be an object schema")
        frozen_parameters = _freeze_json(self.parameters)
        object.__setattr__(self, "input_types", input_types)
        object.__setattr__(self, "output_type", output_type)
        object.__setattr__(self, "parameters", frozen_parameters)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "input_types": [value_type.value for value_type in self.input_types],
            "output_type": self.output_type.value,
            "parameters": _thaw(self.parameters),
            "body_ast": self.body_ast.to_dict(),
        }

    @property
    def canonical_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"), allow_nan=False)

    @property
    def sha256(self) -> str:
        return hashlib.sha256(self.canonical_json.encode("utf-8")).hexdigest()

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> MacroPrimitive:
        expected = {
            "name",
            "description",
            "input_types",
            "output_type",
            "parameters",
            "body_ast",
        }
        if not isinstance(value, Mapping) or set(value) != expected:
            raise MacroValidationError("macro definition has an invalid shape")
        if not isinstance(value["input_types"], list):
            raise MacroValidationError("macro input_types must be a list")
        body = _parse_body(value["body_ast"], [0], 0)
        return cls(
            name=value["name"],
            description=value["description"],
            input_types=tuple(value["input_types"]),
            output_type=value["output_type"],
            parameters=value["parameters"],
            body_ast=body,
        )
