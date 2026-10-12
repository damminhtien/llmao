"""Frozen stage-one objective and canonical candidate identity."""

from __future__ import annotations

import hashlib

from bias_optimizer.domain.evaluation import Evaluation
from bias_optimizer.domain.program import ProgramBiasSpec
from bias_optimizer.dsl.ast import Expr


def ast_hash(program: Expr) -> str:
    if not isinstance(program, Expr):
        raise TypeError("candidate identity requires an Expr")
    return hashlib.sha256(program.to_json().encode("utf-8")).hexdigest()


def stage_one_fitness(evaluation: Evaluation) -> float:
    """Reuse the V3 ranking_score exactly, requiring the 500-only stage."""
    if not isinstance(evaluation, Evaluation):
        raise TypeError("evaluation must be an Evaluation")
    if evaluation.accuracy_5000 is not None:
        raise ValueError("V3.2 primary fitness requires a 500-only evaluation")
    return evaluation.ranking_score


def candidate_bias(
    program: Expr, metadata: dict[str, object] | None = None
) -> ProgramBiasSpec:
    """Give every AST one stable evaluator/cache identity independent of proposer prose."""
    identifier = ast_hash(program)[:12]
    details = metadata or {}
    return ProgramBiasSpec(
        name=str(details.get("name", f"candidate_{identifier}")),
        hypothesis=str(
            details.get(
                "hypothesis",
                "This typed program may encode a useful structural cue for digit recognition.",
            )
        ),
        mechanism=str(details.get("mechanism", "Typed V3 representation program.")),
        program=program,
        prediction=str(
            details.get(
                "prediction",
                "It should improve validation ranking score over nearby programs.",
            )
        ),
        falsification=str(
            details.get(
                "falsification",
                "Reject it if its fixed validation ranking score does not support the prediction.",
            )
        ),
    )
