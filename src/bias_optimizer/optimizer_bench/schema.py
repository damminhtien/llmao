"""Immutable records shared by all V3.2 optimizer implementations."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Any

from bias_optimizer.dsl.ast import Expr

DescriptorCell = tuple[str, str, str, str, str]


@dataclass(frozen=True, slots=True)
class CandidateProposal:
    program: Expr
    proposal_id: str
    optimizer: str
    optimizer_seed: int
    generation: int | None
    parent_ids: tuple[str, ...]
    mechanism_metadata: dict[str, object] | None
    proposal_attempt: int

    def __post_init__(self) -> None:
        if not isinstance(self.program, Expr):
            raise TypeError("program must be an Expr")
        for name in ("proposal_id", "optimizer"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be a non-empty string")
        if type(self.optimizer_seed) is not int or self.optimizer_seed < 0:
            raise ValueError("optimizer_seed must be a non-negative integer")
        if self.generation is not None and (
            type(self.generation) is not int or self.generation < 0
        ):
            raise ValueError("generation must be a non-negative integer or None")
        parents = tuple(self.parent_ids)
        if not all(isinstance(parent, str) and parent for parent in parents):
            raise ValueError("parent_ids must contain non-empty strings")
        object.__setattr__(self, "parent_ids", parents)
        if self.mechanism_metadata is not None:
            if not isinstance(self.mechanism_metadata, dict):
                raise TypeError("mechanism_metadata must be a dict or None")
            object.__setattr__(
                self, "mechanism_metadata", dict(self.mechanism_metadata)
            )
        if type(self.proposal_attempt) is not int or self.proposal_attempt <= 0:
            raise ValueError("proposal_attempt must be a positive integer")

    @property
    def candidate_id(self) -> str:
        from bias_optimizer.optimizer_bench.objective import ast_hash

        return ast_hash(self.program)

    def to_dict(self) -> dict[str, Any]:
        return {
            "program": self.program.to_dict(),
            "proposal_id": self.proposal_id,
            "candidate_id": self.candidate_id,
            "optimizer": self.optimizer,
            "optimizer_seed": self.optimizer_seed,
            "generation": self.generation,
            "parent_ids": list(self.parent_ids),
            "mechanism_metadata": self.mechanism_metadata,
            "proposal_attempt": self.proposal_attempt,
        }


@dataclass(frozen=True, slots=True)
class CandidateEvaluation:
    candidate_id: str
    evaluation_index: int
    fitness: float
    accuracy: float
    feature_dim: int
    runtime_ms: float
    structural_descriptor: DescriptorCell
    behavioral_novelty: float | None = None
    program: Expr | None = None
    metadata: dict[str, object] | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.candidate_id, str) or len(self.candidate_id) != 64:
            raise ValueError("candidate_id must be a SHA-256 hex digest")
        if type(self.evaluation_index) is not int or self.evaluation_index <= 0:
            raise ValueError("evaluation_index must be a positive integer")
        if not isfinite(self.fitness):
            raise ValueError("fitness must be finite")
        for name in ("accuracy", "runtime_ms"):
            value = getattr(self, name)
            if not isfinite(value) or value < 0:
                raise ValueError(f"{name} must be finite and non-negative")
        if self.accuracy > 1:
            raise ValueError("accuracy must be at most 1")
        if type(self.feature_dim) is not int or self.feature_dim <= 0:
            raise ValueError("feature_dim must be a positive integer")
        descriptor = tuple(self.structural_descriptor)
        if len(descriptor) != 5 or not all(
            isinstance(axis, str) for axis in descriptor
        ):
            raise ValueError("structural_descriptor must contain five strings")
        object.__setattr__(self, "structural_descriptor", descriptor)
        if self.behavioral_novelty is not None and (
            not isfinite(self.behavioral_novelty)
            or not 0 <= self.behavioral_novelty <= 1
        ):
            raise ValueError("behavioral_novelty must be in [0, 1] or None")
        if self.program is not None and not isinstance(self.program, Expr):
            raise TypeError("program must be an Expr or None")
        if self.metadata is not None:
            if not isinstance(self.metadata, dict):
                raise TypeError("metadata must be a dict or None")
            object.__setattr__(self, "metadata", dict(self.metadata))

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "evaluation_index": self.evaluation_index,
            "fitness": self.fitness,
            "accuracy": self.accuracy,
            "feature_dim": self.feature_dim,
            "runtime_ms": self.runtime_ms,
            "structural_descriptor": list(self.structural_descriptor),
            "behavioral_novelty": self.behavioral_novelty,
            "program": self.program.to_dict() if self.program is not None else None,
            "metadata": self.metadata,
        }


@dataclass(frozen=True, slots=True)
class SearchTrace:
    optimizer: str
    optimizer_seed: int
    evaluated_candidates: tuple[CandidateEvaluation, ...]
    proposal_attempts: int
    valid_proposal_count: int
    invalid_count: int
    duplicate_count: int
    rejected_by_constraint_count: int
    llm_calls: int
    llm_tokens: int
    proposal_time_ms: float
    evaluation_time_ms: float
    total_wall_time_ms: float
    complete: bool
    termination_reason: str | None = None
    budget_total_evaluations: int = 200
    budget_seed_evaluations: int = 20
    budget_max_proposal_attempts: int = 540

    def __post_init__(self) -> None:
        if not isinstance(self.optimizer, str) or not self.optimizer:
            raise ValueError("optimizer must be non-empty")
        if type(self.optimizer_seed) is not int or self.optimizer_seed < 0:
            raise ValueError("optimizer_seed must be non-negative")
        evaluations = tuple(self.evaluated_candidates)
        if not all(isinstance(row, CandidateEvaluation) for row in evaluations):
            raise TypeError("evaluated_candidates must contain CandidateEvaluation")
        if len({row.candidate_id for row in evaluations}) != len(evaluations):
            raise ValueError("evaluated_candidates must have unique candidate IDs")
        object.__setattr__(self, "evaluated_candidates", evaluations)
        for name in (
            "proposal_attempts",
            "valid_proposal_count",
            "invalid_count",
            "duplicate_count",
            "rejected_by_constraint_count",
            "llm_calls",
            "llm_tokens",
        ):
            if type(getattr(self, name)) is not int or getattr(self, name) < 0:
                raise ValueError(f"{name} must be a non-negative integer")
        for name in ("proposal_time_ms", "evaluation_time_ms", "total_wall_time_ms"):
            value = getattr(self, name)
            if not isfinite(value) or value < 0:
                raise ValueError(f"{name} must be finite and non-negative")
        if type(self.complete) is not bool:
            raise TypeError("complete must be a boolean")
        if self.termination_reason is not None and (
            not isinstance(self.termination_reason, str) or not self.termination_reason
        ):
            raise ValueError("termination_reason must be a non-empty string or None")
        for name in (
            "budget_total_evaluations",
            "budget_seed_evaluations",
            "budget_max_proposal_attempts",
        ):
            if type(getattr(self, name)) is not int or getattr(self, name) <= 0:
                raise ValueError(f"{name} must be a positive integer")

    def to_dict(self) -> dict[str, Any]:
        return {
            "optimizer": self.optimizer,
            "optimizer_seed": self.optimizer_seed,
            "evaluated_candidates": [
                row.to_dict() for row in self.evaluated_candidates
            ],
            "proposal_attempts": self.proposal_attempts,
            "valid_proposal_count": self.valid_proposal_count,
            "invalid_count": self.invalid_count,
            "duplicate_count": self.duplicate_count,
            "rejected_by_constraint_count": self.rejected_by_constraint_count,
            "llm_calls": self.llm_calls,
            "llm_tokens": self.llm_tokens,
            "proposal_time_ms": self.proposal_time_ms,
            "evaluation_time_ms": self.evaluation_time_ms,
            "total_wall_time_ms": self.total_wall_time_ms,
            "complete": self.complete,
            "termination_reason": self.termination_reason,
            "budget_total_evaluations": self.budget_total_evaluations,
            "budget_seed_evaluations": self.budget_seed_evaluations,
            "budget_max_proposal_attempts": self.budget_max_proposal_attempts,
        }
