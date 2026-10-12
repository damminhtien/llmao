"""Unique-evaluation and proposal-attempt limits for optimizer runs."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SearchBudget:
    total_evaluations: int = 200
    seed_evaluations: int = 20
    max_proposal_attempts: int = 540

    def __post_init__(self) -> None:
        for name in ("total_evaluations", "seed_evaluations", "max_proposal_attempts"):
            value = getattr(self, name)
            if type(value) is not int or value <= 0:
                raise ValueError(f"{name} must be a positive integer")
        if self.seed_evaluations >= self.total_evaluations:
            raise ValueError("seed_evaluations must be smaller than total_evaluations")
        if self.max_proposal_attempts < self.new_evaluations:
            raise ValueError(
                "proposal-attempt limit cannot be below new-evaluation count"
            )

    @property
    def new_evaluations(self) -> int:
        return self.total_evaluations - self.seed_evaluations
