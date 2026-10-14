"""Canonical V4 candidate records with validated provenance and hashes."""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from bias_optimizer.dsl.ast import Expr
from bias_optimizer.v4.candidate.provenance import (
    CandidateProvenance,
    CandidateValidationError,
    ModelBackendMetadata,
    TokenUsage,
    WallClockMeasurements,
)
from bias_optimizer.v4.language.base_language import LanguageManifest
from bias_optimizer.v4.language.macro import MacroPrimitive, MacroValidationError
from bias_optimizer.v4.language.validator import (
    CandidateExpansion,
    MacroLanguage,
    MacroLimits,
    expand_candidate,
    extend_macro_language,
)

_PROTOCOL_LIMITS = MacroLimits()


@dataclass(frozen=True, slots=True)
class CandidateV4:
    """A representation, its exact macro language, and its search provenance."""

    candidate_id: str
    language: MacroLanguage
    program: Expr
    provenance: CandidateProvenance
    _expansion: CandidateExpansion = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        if not isinstance(self.candidate_id, str) or not self.candidate_id.strip():
            raise CandidateValidationError("candidate_id must be non-empty")
        if self.candidate_id.strip() != self.candidate_id:
            raise CandidateValidationError("candidate_id must not contain outer whitespace")
        if "/" in self.candidate_id or "\\" in self.candidate_id:
            raise CandidateValidationError("candidate_id cannot contain path separators")
        if not isinstance(self.language, MacroLanguage):
            raise CandidateValidationError("language must be a validated MacroLanguage")
        if self.language.limits != _PROTOCOL_LIMITS:
            raise CandidateValidationError(
                "candidate macro limits must match the V4 protocol limits"
            )
        if not isinstance(self.program, Expr):
            raise CandidateValidationError("program must be a DSL Expr")
        if not isinstance(self.provenance, CandidateProvenance):
            raise CandidateValidationError("provenance must be CandidateProvenance")
        if self.provenance.generation == 0 and self.provenance.parent_candidate_id:
            raise CandidateValidationError("generation 0 cannot have a parent candidate")
        if self.provenance.generation > 0 and not self.provenance.parent_candidate_id:
            raise CandidateValidationError("later generations need a parent candidate")
        if self.provenance.parent_candidate_id == self.candidate_id:
            raise CandidateValidationError("candidate cannot be its own parent")
        try:
            expansion = expand_candidate(
                self.program,
                self.language,
                introduced_macros=self.provenance.invented_primitives,
            )
        except MacroValidationError as exc:
            raise CandidateValidationError(f"candidate program is invalid: {exc}") from exc
        if expansion.used_primitives != self.provenance.used_primitives:
            raise CandidateValidationError(
                "used_primitives does not match the validated expanded program"
            )
        object.__setattr__(self, "_expansion", expansion)

    @property
    def language_hash(self) -> str:
        return self.language.sha256

    @property
    def parent_language_hash(self) -> str:
        return self.language.parent_language_hash

    @property
    def program_hash(self) -> str:
        return self._expansion.program_hash

    @property
    def expanded_program_hash(self) -> str:
        return self._expansion.expanded_program_hash

    @property
    def expansion(self) -> CandidateExpansion:
        return self._expansion

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "candidate_id": self.candidate_id,
            "language_hash": self.language_hash,
            "parent_language_hash": self.parent_language_hash,
            "program_hash": self.program_hash,
            "expanded_program_hash": self.expanded_program_hash,
            "language": self.language.to_dict(),
            "program": self.program.to_dict(),
            "provenance": self.provenance.to_dict(),
        }

    @property
    def canonical_json(self) -> str:
        return json.dumps(
            self.to_dict(), sort_keys=True, separators=(",", ":"), allow_nan=False
        )

    @classmethod
    def create(
        cls,
        *,
        candidate_id: str,
        language: MacroLanguage,
        program: Expr,
        parent_candidate_id: str | None,
        invented_primitives: tuple[str, ...],
        eve_agent_id: str | None,
        guidance_hash: str | None,
        generation: int,
        model_backend: ModelBackendMetadata,
        evaluation_seed: int,
        token_usage: TokenUsage | None = None,
        wall_clock_ms: WallClockMeasurements | None = None,
    ) -> CandidateV4:
        try:
            expansion = expand_candidate(
                program, language, introduced_macros=invented_primitives
            )
        except MacroValidationError as exc:
            raise CandidateValidationError(f"candidate program is invalid: {exc}") from exc
        provenance = CandidateProvenance(
            parent_candidate_id=parent_candidate_id,
            invented_primitives=invented_primitives,
            used_primitives=expansion.used_primitives,
            eve_agent_id=eve_agent_id,
            guidance_hash=guidance_hash,
            generation=generation,
            model_backend=model_backend,
            evaluation_seed=evaluation_seed,
            token_usage=token_usage,
            wall_clock_ms=wall_clock_ms or WallClockMeasurements(),
        )
        return cls(candidate_id, language, program, provenance)

    @classmethod
    def from_dict(
        cls,
        value: Mapping[str, Any],
        *,
        parent_language: LanguageManifest | MacroLanguage,
    ) -> CandidateV4:
        expected = {
            "schema_version",
            "candidate_id",
            "language_hash",
            "parent_language_hash",
            "program_hash",
            "expanded_program_hash",
            "language",
            "program",
            "provenance",
        }
        if not isinstance(value, Mapping) or set(value) != expected:
            raise CandidateValidationError("candidate record has an invalid shape")
        if type(value["schema_version"]) is not int or value["schema_version"] != 1:
            raise CandidateValidationError("unsupported CandidateV4 schema version")
        language = _load_macro_language(value["language"], parent_language)
        try:
            program = Expr.from_dict(value["program"])
        except (TypeError, ValueError, KeyError) as exc:
            raise CandidateValidationError(f"invalid candidate program AST: {exc}") from exc
        provenance = CandidateProvenance.from_dict(value["provenance"])
        candidate = cls(
            candidate_id=value["candidate_id"],
            language=language,
            program=program,
            provenance=provenance,
        )
        checks = {
            "language_hash": candidate.language_hash,
            "parent_language_hash": candidate.parent_language_hash,
            "program_hash": candidate.program_hash,
            "expanded_program_hash": candidate.expanded_program_hash,
        }
        for name, expected_value in checks.items():
            if value[name] != expected_value:
                raise CandidateValidationError(f"{name} does not match candidate contents")
        return candidate


def _load_macro_language(
    value: Any,
    parent_language: LanguageManifest | MacroLanguage,
) -> MacroLanguage:
    expected = {
        "schema_version",
        "language",
        "parent_language_hash",
        "base_language_hash",
        "limits",
        "introduced_macros",
        "macros",
    }
    if not isinstance(value, Mapping) or set(value) != expected:
        raise CandidateValidationError("candidate language has an invalid shape")
    if not isinstance(parent_language, (LanguageManifest, MacroLanguage)):
        raise CandidateValidationError("parent_language has an invalid type")
    if (
        type(value["schema_version"]) is not int
        or value["schema_version"] != 1
        or value["language"] != "G*"
    ):
        raise CandidateValidationError("candidate language has an unsupported version")
    base_language = (
        parent_language.base_language
        if isinstance(parent_language, MacroLanguage)
        else parent_language
    )
    if value["base_language_hash"] != base_language.sha256:
        raise CandidateValidationError("candidate language has a different base language")
    if value["parent_language_hash"] != parent_language.sha256:
        raise CandidateValidationError("candidate language parent hash does not match")

    limits_value = value["limits"]
    if not isinstance(limits_value, Mapping) or set(limits_value) != {
        "max_expansion_depth",
        "max_expanded_nodes",
        "max_feature_dim",
    }:
        raise CandidateValidationError("candidate language limits have an invalid shape")
    try:
        limits = MacroLimits(**limits_value)
    except (TypeError, ValueError) as exc:
        raise CandidateValidationError(f"invalid candidate macro limits: {exc}") from exc
    if limits != _PROTOCOL_LIMITS:
        raise CandidateValidationError(
            "candidate macro limits differ from the V4 protocol limits"
        )

    introduced = value["introduced_macros"]
    serialized_macros = value["macros"]
    if not isinstance(introduced, list) or not all(
        isinstance(name, str) for name in introduced
    ):
        raise CandidateValidationError("introduced_macros must be a list of names")
    if not isinstance(serialized_macros, list):
        raise CandidateValidationError("candidate macros must be a list")
    try:
        macros = tuple(MacroPrimitive.from_dict(macro) for macro in serialized_macros)
    except (TypeError, ValueError, KeyError) as exc:
        raise CandidateValidationError(f"invalid macro definition: {exc}") from exc

    inherited_macros = (
        parent_language.macros if isinstance(parent_language, MacroLanguage) else ()
    )
    inherited = {macro.name: macro for macro in inherited_macros}
    supplied = {macro.name: macro for macro in macros}
    introduced_names = set(introduced)
    if len(introduced_names) != len(introduced):
        raise CandidateValidationError("introduced_macros contains duplicates")
    if introduced_names & set(inherited):
        raise CandidateValidationError("candidate reintroduces an inherited macro")
    if set(supplied) != set(inherited) | introduced_names:
        raise CandidateValidationError("candidate language macro inventory is inconsistent")
    for name, macro in inherited.items():
        if supplied[name].to_dict() != macro.to_dict():
            raise CandidateValidationError(f"candidate modified inherited macro {name!r}")
    additions = tuple(supplied[name] for name in introduced)
    try:
        language = extend_macro_language(parent_language, additions, limits=limits)
    except MacroValidationError as exc:
        raise CandidateValidationError(f"candidate language is invalid: {exc}") from exc
    if language.to_dict() != dict(value):
        raise CandidateValidationError("candidate language is not canonically represented")
    return language
