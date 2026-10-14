"""Strict, JSON-ready metadata for V4 candidates."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Any

_SHA256 = re.compile(r"[0-9a-f]{64}\Z")


class CandidateValidationError(ValueError):
    """A candidate or its provenance violates the V4 schema."""


def _text(value: Any, name: str, *, optional: bool = False) -> str | None:
    if value is None and optional:
        return None
    if not isinstance(value, str) or not value.strip() or value.strip() != value:
        raise CandidateValidationError(f"{name} must be a non-empty trimmed string")
    return value


def _names(values: tuple[str, ...] | list[str], name: str) -> tuple[str, ...]:
    if not isinstance(values, (tuple, list)) or not all(
        isinstance(value, str)
        and value.isascii()
        and value.replace("_", "").isalnum()
        and value.lower() == value
        for value in values
    ):
        raise CandidateValidationError(f"{name} must contain lowercase identifiers")
    if len(values) != len(set(values)):
        raise CandidateValidationError(f"{name} must not contain duplicates")
    return tuple(sorted(values))


def _non_negative_int(value: Any, name: str) -> int:
    if type(value) is not int or value < 0:
        raise CandidateValidationError(f"{name} must be a non-negative integer")
    return value


def _identifier_text(value: Any, name: str, *, optional: bool = False) -> str | None:
    text = _text(value, name, optional=optional)
    if text is not None and ("/" in text or "\\" in text):
        raise CandidateValidationError(f"{name} cannot contain path separators")
    return text


@dataclass(frozen=True, slots=True)
class ModelBackendMetadata:
    model_identifier: str
    backend: str
    reasoning_effort: str | None = None

    def __post_init__(self) -> None:
        _text(self.model_identifier, "model_identifier")
        _text(self.backend, "backend")
        _text(self.reasoning_effort, "reasoning_effort", optional=True)

    def to_dict(self) -> dict[str, str | None]:
        return {
            "model_identifier": self.model_identifier,
            "backend": self.backend,
            "reasoning_effort": self.reasoning_effort,
        }

    @classmethod
    def from_dict(cls, value: Any) -> ModelBackendMetadata:
        expected = {"model_identifier", "backend", "reasoning_effort"}
        if not isinstance(value, dict) or set(value) != expected:
            raise CandidateValidationError("model_backend metadata has an invalid shape")
        return cls(**value)


@dataclass(frozen=True, slots=True)
class TokenUsage:
    input_tokens: int
    cached_input_tokens: int
    output_tokens: int

    def __post_init__(self) -> None:
        for name in ("input_tokens", "cached_input_tokens", "output_tokens"):
            _non_negative_int(getattr(self, name), name)
        if self.cached_input_tokens > self.input_tokens:
            raise CandidateValidationError("cached_input_tokens cannot exceed input_tokens")

    def to_dict(self) -> dict[str, int]:
        return {
            "input_tokens": self.input_tokens,
            "cached_input_tokens": self.cached_input_tokens,
            "output_tokens": self.output_tokens,
        }

    @classmethod
    def from_dict(cls, value: Any) -> TokenUsage:
        expected = {"input_tokens", "cached_input_tokens", "output_tokens"}
        if not isinstance(value, dict) or set(value) != expected:
            raise CandidateValidationError("token_usage has an invalid shape")
        return cls(**value)


@dataclass(frozen=True, slots=True)
class WallClockMeasurements:
    generation_ms: float | None = None
    validation_ms: float | None = None
    evaluation_ms: float | None = None
    total_ms: float | None = None

    def __post_init__(self) -> None:
        for name in ("generation_ms", "validation_ms", "evaluation_ms", "total_ms"):
            value = getattr(self, name)
            if value is not None and (
                type(value) not in (int, float) or not math.isfinite(value) or value < 0
            ):
                raise CandidateValidationError(
                    f"{name} must be a finite non-negative number or null"
                )

    def to_dict(self) -> dict[str, float | None]:
        return {
            "generation_ms": self.generation_ms,
            "validation_ms": self.validation_ms,
            "evaluation_ms": self.evaluation_ms,
            "total_ms": self.total_ms,
        }

    @classmethod
    def from_dict(cls, value: Any) -> WallClockMeasurements:
        expected = {"generation_ms", "validation_ms", "evaluation_ms", "total_ms"}
        if not isinstance(value, dict) or set(value) != expected:
            raise CandidateValidationError("wall_clock_ms has an invalid shape")
        return cls(**value)


@dataclass(frozen=True, slots=True)
class CandidateProvenance:
    parent_candidate_id: str | None
    invented_primitives: tuple[str, ...]
    used_primitives: tuple[str, ...]
    eve_agent_id: str | None
    guidance_hash: str | None
    generation: int
    model_backend: ModelBackendMetadata
    evaluation_seed: int
    token_usage: TokenUsage | None
    wall_clock_ms: WallClockMeasurements

    def __post_init__(self) -> None:
        _identifier_text(self.parent_candidate_id, "parent_candidate_id", optional=True)
        _identifier_text(self.eve_agent_id, "eve_agent_id", optional=True)
        if self.guidance_hash is not None and (
            not isinstance(self.guidance_hash, str)
            or not _SHA256.fullmatch(self.guidance_hash)
        ):
            raise CandidateValidationError(
                "guidance_hash must be a lowercase SHA-256 digest"
            )
        object.__setattr__(
            self,
            "invented_primitives",
            _names(self.invented_primitives, "invented_primitives"),
        )
        object.__setattr__(
            self,
            "used_primitives",
            _names(self.used_primitives, "used_primitives"),
        )
        _non_negative_int(self.generation, "generation")
        _non_negative_int(self.evaluation_seed, "evaluation_seed")
        if not isinstance(self.model_backend, ModelBackendMetadata):
            raise CandidateValidationError("model_backend must be ModelBackendMetadata")
        if self.token_usage is not None and not isinstance(self.token_usage, TokenUsage):
            raise CandidateValidationError("token_usage must be TokenUsage or null")
        if not isinstance(self.wall_clock_ms, WallClockMeasurements):
            raise CandidateValidationError(
                "wall_clock_ms must be WallClockMeasurements"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "parent_candidate_id": self.parent_candidate_id,
            "invented_primitives": list(self.invented_primitives),
            "used_primitives": list(self.used_primitives),
            "eve_agent_id": self.eve_agent_id,
            "guidance_hash": self.guidance_hash,
            "generation": self.generation,
            "model_backend": self.model_backend.to_dict(),
            "evaluation_seed": self.evaluation_seed,
            "token_usage": self.token_usage.to_dict() if self.token_usage else None,
            "wall_clock_ms": self.wall_clock_ms.to_dict(),
        }

    @classmethod
    def from_dict(cls, value: Any) -> CandidateProvenance:
        expected = {
            "parent_candidate_id",
            "invented_primitives",
            "used_primitives",
            "eve_agent_id",
            "guidance_hash",
            "generation",
            "model_backend",
            "evaluation_seed",
            "token_usage",
            "wall_clock_ms",
        }
        if not isinstance(value, dict) or set(value) != expected:
            raise CandidateValidationError("candidate provenance has an invalid shape")
        for name in ("invented_primitives", "used_primitives"):
            if not isinstance(value[name], list):
                raise CandidateValidationError(f"{name} must be a list")
        return cls(
            parent_candidate_id=value["parent_candidate_id"],
            invented_primitives=tuple(value["invented_primitives"]),
            used_primitives=tuple(value["used_primitives"]),
            eve_agent_id=value["eve_agent_id"],
            guidance_hash=value["guidance_hash"],
            generation=value["generation"],
            model_backend=ModelBackendMetadata.from_dict(value["model_backend"]),
            evaluation_seed=value["evaluation_seed"],
            token_usage=(
                TokenUsage.from_dict(value["token_usage"])
                if value["token_usage"] is not None
                else None
            ),
            wall_clock_ms=WallClockMeasurements.from_dict(value["wall_clock_ms"]),
        )
