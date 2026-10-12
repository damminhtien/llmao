"""Typed genetic programming with a fixed 20-member population."""

from __future__ import annotations

import random

from bias_optimizer.dsl.validator import ProgramConstraints
from bias_optimizer.novelty.descriptors import mechanism_family
from bias_optimizer.optimizer_bench.mutations import typed_crossover, typed_mutation
from bias_optimizer.optimizer_bench.objective import ast_hash
from bias_optimizer.optimizer_bench.optimizers.base import (
    OptimizationContext,
    ProposalBatch,
)
from bias_optimizer.optimizer_bench.random_ast import SamplingFailure
from bias_optimizer.optimizer_bench.schema import CandidateEvaluation, CandidateProposal
from bias_optimizer.optimizer_bench.selection import best_unique, tournament


class GeneticProgrammingOptimizer:
    name = "genetic_programming"

    def __init__(self, seed: int, constraints: ProgramConstraints) -> None:
        self._rng = random.Random(seed)
        self._constraints = constraints
        self._population: tuple[CandidateEvaluation, ...] = ()
        self._generation_children: list[CandidateEvaluation] = []

    def propose(self, context: OptimizationContext) -> ProposalBatch:
        attempt = context.proposal_attempt_start
        population = self._population or context.evaluated[-20:]
        if not population:
            raise RuntimeError("genetic programming requires evaluated seed programs")
        try:
            if self._rng.random() < 0.5:
                first = tournament(population, self._rng, size=3)
                second = tournament(population, self._rng, size=3)
                if first.program is None or second.program is None:
                    raise SamplingFailure("GP parent is missing its AST")
                offspring = typed_crossover(
                    first.program,
                    second.program,
                    self._rng,
                    constraints=self._constraints,
                )
                parents = (first, second)
                operation = "typed_subtree_crossover"
            else:
                parent = tournament(population, self._rng, size=3)
                if parent.program is None:
                    raise SamplingFailure("GP parent is missing its AST")
                offspring = typed_mutation(
                    parent.program,
                    self._rng,
                    constraints=self._constraints,
                )
                parents = (parent,)
                operation = "typed_mutation"
        except SamplingFailure:
            return ProposalBatch(attempts=1, rejected_by_constraint_count=1)

        identifier = ast_hash(offspring)[:12]
        metadata = {
            "name": f"gp_{identifier}",
            "hypothesis": "Typed recombination or mutation may improve a representation under the fixed objective.",
            "mechanism": mechanism_family(offspring),
            "prediction": "Selection should retain offspring with higher fixed validation fitness.",
            "falsification": "Reject the program if its score does not improve the selected population region.",
            "operator": operation,
            "parent_ids": [row.candidate_id for row in parents],
        }
        proposal = CandidateProposal(
            program=offspring,
            proposal_id=f"genetic_programming:{context.optimizer_seed}:{attempt}",
            optimizer=self.name,
            optimizer_seed=context.optimizer_seed,
            generation=context.generation,
            parent_ids=tuple(row.candidate_id for row in parents),
            mechanism_metadata=metadata,
            proposal_attempt=attempt,
        )
        return ProposalBatch((proposal,), attempts=1, valid_proposal_count=1)

    def on_seed_evaluations(
        self,
        proposals: tuple[CandidateProposal, ...],
        evaluations: tuple[CandidateEvaluation, ...],
    ) -> None:
        self._population = best_unique(evaluations, 20)

    def on_evaluation(
        self, proposal: CandidateProposal, evaluation: CandidateEvaluation
    ) -> None:
        self._generation_children.append(evaluation)

    def finish_generation(self) -> None:
        if not self._generation_children:
            return
        elites = best_unique(self._population, 2)
        children = best_unique(tuple(self._generation_children), 18)
        self._population = (*elites, *children)
        self._generation_children.clear()
