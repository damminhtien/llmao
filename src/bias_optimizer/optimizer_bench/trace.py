"""Atomic trace serialization for optimizer runs."""

from __future__ import annotations

import json
from pathlib import Path

from bias_optimizer.optimizer_bench.schema import SearchTrace


def write_trace(trace: SearchTrace, path: Path) -> None:
    if not isinstance(trace, SearchTrace):
        raise TypeError("trace must be SearchTrace")
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    temporary.write_text(
        json.dumps(trace.to_dict(), ensure_ascii=False, indent=2, sort_keys=True)
        + "\n",
        encoding="utf-8",
    )
    temporary.replace(destination)


def read_trace(path: Path) -> SearchTrace:
    from bias_optimizer.dsl.ast import Expr
    from bias_optimizer.optimizer_bench.schema import CandidateEvaluation

    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    evaluations = tuple(
        CandidateEvaluation(
            candidate_id=row["candidate_id"],
            evaluation_index=row["evaluation_index"],
            fitness=row["fitness"],
            accuracy=row["accuracy"],
            feature_dim=row["feature_dim"],
            runtime_ms=row["runtime_ms"],
            structural_descriptor=tuple(row["structural_descriptor"]),
            behavioral_novelty=row["behavioral_novelty"],
            program=Expr.from_dict(row["program"]) if row["program"] else None,
            metadata=row["metadata"],
        )
        for row in payload["evaluated_candidates"]
    )
    return SearchTrace(
        optimizer=payload["optimizer"],
        optimizer_seed=payload["optimizer_seed"],
        evaluated_candidates=evaluations,
        proposal_attempts=payload["proposal_attempts"],
        valid_proposal_count=payload["valid_proposal_count"],
        invalid_count=payload["invalid_count"],
        duplicate_count=payload["duplicate_count"],
        rejected_by_constraint_count=payload["rejected_by_constraint_count"],
        llm_calls=payload["llm_calls"],
        llm_tokens=payload["llm_tokens"],
        proposal_time_ms=payload["proposal_time_ms"],
        evaluation_time_ms=payload["evaluation_time_ms"],
        total_wall_time_ms=payload["total_wall_time_ms"],
        complete=payload["complete"],
        termination_reason=payload.get("termination_reason"),
        budget_total_evaluations=payload.get("budget_total_evaluations", 200),
        budget_seed_evaluations=payload.get("budget_seed_evaluations", 20),
        budget_max_proposal_attempts=payload.get("budget_max_proposal_attempts", 540),
    )
