"""Small, deterministic selection helpers for typed genetic programming."""

from __future__ import annotations

import random

from bias_optimizer.optimizer_bench.schema import CandidateEvaluation


def tournament(
    population: tuple[CandidateEvaluation, ...], rng: random.Random, size: int = 3
) -> CandidateEvaluation:
    if not population:
        raise ValueError("tournament population cannot be empty")
    if type(size) is not int or size <= 0:
        raise ValueError("tournament size must be positive")
    contestants = rng.sample(population, k=min(size, len(population)))
    return min(contestants, key=lambda row: (-row.fitness, row.candidate_id))


def best_unique(
    population: tuple[CandidateEvaluation, ...], count: int
) -> tuple[CandidateEvaluation, ...]:
    if type(count) is not int or count <= 0:
        raise ValueError("count must be positive")
    best: dict[str, CandidateEvaluation] = {}
    for row in population:
        best.setdefault(row.candidate_id, row)
    return tuple(
        sorted(best.values(), key=lambda row: (-row.fitness, row.candidate_id))[:count]
    )
