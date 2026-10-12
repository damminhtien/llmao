"""Shared proposal-only interface used by the benchmark runner."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from bias_optimizer.dsl.ast import Expr
from bias_optimizer.dsl.validator import ProgramConstraints
from bias_optimizer.optimizer_bench.schema import CandidateEvaluation, CandidateProposal


@dataclass(frozen=True, slots=True)
class ProposalBatch:
    proposals: tuple[CandidateProposal, ...] = ()
    attempts: int = 0
    valid_proposal_count: int = 0
    invalid_count: int = 0
    duplicate_count: int = 0
    rejected_by_constraint_count: int = 0
    llm_calls: int = 0
    llm_tokens: int = 0

    def __post_init__(self) -> None:
        object.__setattr__(self, "proposals", tuple(self.proposals))
        for name in (
            "attempts",
            "valid_proposal_count",
            "invalid_count",
            "duplicate_count",
            "rejected_by_constraint_count",
            "llm_calls",
            "llm_tokens",
        ):
            if type(getattr(self, name)) is not int or getattr(self, name) < 0:
                raise ValueError(f"{name} must be a non-negative integer")


@dataclass(frozen=True, slots=True)
class OptimizationContext:
    optimizer: str
    optimizer_seed: int
    generation: int
    proposal_attempt_start: int
    remaining_attempts: int
    batch_size: int
    constraints: ProgramConstraints
    seed_programs: tuple[Expr, ...]
    evaluated: tuple[CandidateEvaluation, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "seed_programs", tuple(self.seed_programs))
        object.__setattr__(self, "evaluated", tuple(self.evaluated))
        if self.batch_size <= 0 or self.remaining_attempts <= 0:
            raise ValueError(
                "proposal batch size and remaining attempts must be positive"
            )


class Optimizer(Protocol):
    name: str

    def propose(self, context: OptimizationContext) -> ProposalBatch: ...

    def on_seed_evaluations(
        self,
        proposals: tuple[CandidateProposal, ...],
        evaluations: tuple[CandidateEvaluation, ...],
    ) -> None: ...

    def on_evaluation(
        self, proposal: CandidateProposal, evaluation: CandidateEvaluation
    ) -> None: ...

    def finish_generation(self) -> None: ...
