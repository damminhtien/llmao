"""Type-directed random search over the frozen V3 discovery grammar."""

from __future__ import annotations

import random

from bias_optimizer.dsl.validator import ProgramConstraints
from bias_optimizer.novelty.descriptors import mechanism_family
from bias_optimizer.optimizer_bench.objective import ast_hash
from bias_optimizer.optimizer_bench.optimizers.base import (
    OptimizationContext,
    ProposalBatch,
)
from bias_optimizer.optimizer_bench.random_ast import SamplingFailure, sample_random_ast
from bias_optimizer.optimizer_bench.schema import CandidateEvaluation, CandidateProposal


class TypedRandomOptimizer:
    name = "typed_random"

    def __init__(self, seed: int, constraints: ProgramConstraints) -> None:
        self._rng = random.Random(seed)
        self._constraints = constraints

    def propose(self, context: OptimizationContext) -> ProposalBatch:
        attempt = context.proposal_attempt_start
        target_depth = self._rng.randint(1, self._constraints.max_depth)
        try:
            program = sample_random_ast(
                self._rng,
                constraints=self._constraints,
                target_depth=target_depth,
            )
        except SamplingFailure:
            return ProposalBatch(attempts=1, rejected_by_constraint_count=1)
        identifier = ast_hash(program)[:12]
        metadata = {
            "name": f"random_{identifier}",
            "hypothesis": "A typed random program tests whether unguided coverage reaches useful representations.",
            "mechanism": mechanism_family(program),
            "prediction": "Its held-out validation score will reveal whether the sampled structure is useful.",
            "falsification": "Reject the proposal if its fixed validation score is poor.",
            "target_depth": target_depth,
        }
        proposal = CandidateProposal(
            program=program,
            proposal_id=f"typed_random:{context.optimizer_seed}:{attempt}",
            optimizer=self.name,
            optimizer_seed=context.optimizer_seed,
            generation=context.generation,
            parent_ids=(),
            mechanism_metadata=metadata,
            proposal_attempt=attempt,
        )
        return ProposalBatch((proposal,), attempts=1, valid_proposal_count=1)

    def on_seed_evaluations(
        self,
        proposals: tuple[CandidateProposal, ...],
        evaluations: tuple[CandidateEvaluation, ...],
    ) -> None:
        return None

    def on_evaluation(
        self, proposal: CandidateProposal, evaluation: CandidateEvaluation
    ) -> None:
        return None

    def finish_generation(self) -> None:
        return None
