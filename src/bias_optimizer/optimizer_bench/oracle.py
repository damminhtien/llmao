"""Evaluation boundary: optimizers submit Expr trees and receive frozen metrics."""

from __future__ import annotations

from time import perf_counter

import numpy as np

from bias_optimizer.dsl.ast import Expr
from bias_optimizer.dsl.compiler import ProgramCompiler
from bias_optimizer.dsl.validator import ProgramConstraints, SearchTrack
from bias_optimizer.ml.evaluator import ProgramEvaluator
from bias_optimizer.novelty.descriptors import describe_program
from bias_optimizer.novelty.tree_distance import structural_novelty
from bias_optimizer.optimizer_bench.objective import (
    ast_hash,
    candidate_bias,
    stage_one_fitness,
)
from bias_optimizer.optimizer_bench.schema import CandidateEvaluation


class SearchOracle:
    """Own all labels and learner state behind a proposal-only API."""

    __slots__ = ("_compiler", "_evaluation_time_ms", "_evaluator", "_memo")

    def __init__(
        self,
        *,
        evaluator: ProgramEvaluator | None = None,
        constraints: ProgramConstraints | None = None,
    ) -> None:
        self._compiler = ProgramCompiler(
            constraints
            or ProgramConstraints(
                track=SearchTrack.DISCOVERY,
                max_feature_dim=128,
                max_depth=6,
                max_nodes=127,
                forbid_raw_pixels=True,
            )
        )
        self._evaluator = evaluator or ProgramEvaluator(
            compiler=self._compiler,
            train_sizes=(500,),
        )
        self._memo: dict[str, CandidateEvaluation] = {}
        self._evaluation_time_ms = 0.0

    @property
    def evaluated_count(self) -> int:
        return len(self._memo)

    @property
    def evaluation_time_ms(self) -> float:
        return self._evaluation_time_ms

    def validate(self, program: Expr) -> None:
        self._compiler.compile(program)

    def evaluate(
        self,
        program: Expr,
        *,
        evaluation_index: int,
        previously_evaluated: tuple[Expr, ...] = (),
        metadata: dict[str, object] | None = None,
    ) -> CandidateEvaluation:
        if not isinstance(program, Expr):
            raise TypeError("SearchOracle accepts Expr programs only")
        key = ast_hash(program)
        cached = self._memo.get(key)
        if cached is not None:
            return cached
        self._compiler.compile(program)
        bias = candidate_bias(program, metadata)
        start = perf_counter()
        evaluation = self._evaluator.evaluate(bias)
        elapsed = (perf_counter() - start) * 1_000
        self._evaluation_time_ms += elapsed
        fitness = stage_one_fitness(evaluation)
        descriptor = describe_program(program)
        novelty = structural_novelty(program, previously_evaluated)
        row = CandidateEvaluation(
            candidate_id=key,
            evaluation_index=evaluation_index,
            fitness=fitness,
            accuracy=evaluation.accuracy_500,
            feature_dim=evaluation.feature_dim,
            runtime_ms=evaluation.runtime_ms,
            structural_descriptor=descriptor.cell,
            behavioral_novelty=None,
            program=program,
            metadata={
                **(metadata or {}),
                "structural_novelty": novelty,
                "feature_runtime_ms": evaluation.feature_runtime_ms,
                "training_runtime_ms": evaluation.training_runtime_ms,
                "inference_runtime_ms": evaluation.inference_runtime_ms,
                "oracle_elapsed_ms": elapsed,
            },
        )
        self._memo[key] = row
        return row


def evaluation_record(row: CandidateEvaluation):
    """Create a label-free V3-compatible record for the existing prompt builder."""
    from bias_optimizer.domain.evaluation import Evaluation
    from bias_optimizer.domain.program_search import ProgramSearchRecord

    if row.program is None:
        raise ValueError("candidate evaluation has no program AST")
    metadata: dict[str, object] = row.metadata or {}
    bias = candidate_bias(row.program, metadata)
    evaluation = Evaluation(
        accuracy_500=row.accuracy,
        accuracy_5000=None,
        feature_dim=row.feature_dim,
        feature_runtime_ms=float(metadata.get("feature_runtime_ms", row.runtime_ms)),
        training_runtime_ms=float(metadata.get("training_runtime_ms", 0.0)),
        inference_runtime_ms=float(metadata.get("inference_runtime_ms", 0.0)),
        confusion_matrix=np.zeros((10, 10), dtype=np.int64),
    )
    source, order, spatial, composition, complexity = row.structural_descriptor
    return ProgramSearchRecord(
        generation=int(metadata.get("generation", 0)),
        track=SearchTrack.DISCOVERY.value,
        bias=bias,
        evaluation=evaluation,
        source=source,
        order=order,
        spatial=spatial,
        composition=composition,
        complexity=complexity,
        novelty=float(metadata.get("structural_novelty", 0.0)),
        parent_ids=tuple(metadata.get("parent_ids", ())),
    )
