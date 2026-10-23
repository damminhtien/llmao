"""Discovery-only vocabulary cost fixed by the V4 primary design."""

from __future__ import annotations

import math

from bias_optimizer.v4.language.validator import MacroLanguage

LANGUAGE_PENALTY_COEFFICIENT = 0.0005
LANGUAGE_COMPLEXITY_DEFINITION = (
    "number of invented macros in the complete language inventory"
)


def discovery_objective(stage_one_fitness: float, language: MacroLanguage) -> dict:
    """Return score components without changing fixed-language stage-one fitness.

    Call only from a discovery evaluator bound to a finalized protocol. This
    helper performs no data access, model fitting, or primary launch approval.
    """
    if type(stage_one_fitness) not in (int, float) or not math.isfinite(
        stage_one_fitness
    ):
        raise ValueError("stage-one fitness must be a finite number")
    if not isinstance(language, MacroLanguage):
        raise TypeError("discovery language must be a validated MacroLanguage")
    complexity = len(language.macros)
    penalty = LANGUAGE_PENALTY_COEFFICIENT * complexity
    return {
        "stage_one_fitness": float(stage_one_fitness),
        "language_complexity": complexity,
        "language_penalty": {
            "definition": LANGUAGE_COMPLEXITY_DEFINITION,
            "coefficient": LANGUAGE_PENALTY_COEFFICIENT,
            "value": penalty,
        },
        "discovery_fitness": float(stage_one_fitness) - penalty,
    }
