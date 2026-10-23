"""V4 candidate scoring built on the frozen V3.2 stage-one evaluator."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from bias_optimizer.dsl.compiler import ProgramCompiler
from bias_optimizer.dsl.validator import ProgramConstraints, SearchTrack
from bias_optimizer.ml.evaluator import Evaluator
from bias_optimizer.optimizer_bench.objective import stage_one_fitness
from bias_optimizer.v4.candidate.schema import CandidateV4

_TRAINING_SEED = 42
_TRAINING_SUBSET_SIZE = 500
_VALIDATION_SIZE = 2_000


def evaluator_source_snapshot(repo_root: Path) -> dict[str, Any]:
    """Hash the evaluator entrypoint, LLMAO code, and frozen study inputs."""
    root = Path(repo_root).resolve(strict=True)
    paths = [
        *sorted((root / "src/bias_optimizer").rglob("*.py")),
        root / "experiments/v4_evaluate_candidate.py",
        root / "experiments/v4_build_candidate_context.py",
        root / "scripts/codex-v4-sandbox",
        root / "results/v4/protocol.json",
        root / "results/v4/environment.json",
        root / "results/v4/languages/g0.json",
        root / "results/v4/languages/g0.json.sha256",
        root / "results/v4/languages/gh.json",
        root / "results/v4/languages/gh.json.sha256",
        root / "pyproject.toml",
    ]
    lock_path = root / "uv.lock"
    if lock_path.is_file():
        paths.append(lock_path)

    records: list[dict[str, str]] = []
    digest = hashlib.sha256()
    for path in sorted(set(paths)):
        if not path.is_file():
            raise FileNotFoundError(f"evaluator source is missing: {path}")
        relative = path.relative_to(root).as_posix()
        content = path.read_bytes()
        source_hash = hashlib.sha256(content).hexdigest()
        records.append({"path": relative, "sha256": source_hash})
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(content)
        digest.update(b"\0")
    return {"sha256": digest.hexdigest(), "sources": records}


def validate_protocol(protocol_path: Path) -> dict[str, Any]:
    """Load and verify the fixed split and learner settings used for scoring."""
    protocol = json.loads(Path(protocol_path).read_text(encoding="utf-8"))
    basis = protocol["evaluator_basis"]
    learner = basis["learner"]
    expected = {
        "dataset": "MNIST OpenML mnist_784 v1; official 60,000-example training partition only",
        "validation_size": _VALIDATION_SIZE,
        "validation_split_seed": _TRAINING_SEED,
        "training_subset_size": _TRAINING_SUBSET_SIZE,
        "training_subset_seed": _TRAINING_SEED,
        "official_test_access": False,
    }
    for name, value in expected.items():
        if basis.get(name) != value:
            raise ValueError(f"V4 protocol evaluator setting {name!r} changed")
    expected_learner = {
        "C": 1.0,
        "classifier": "LogisticRegression",
        "max_iter": 1_000,
        "random_state": _TRAINING_SEED,
        "scaler": "StandardScaler",
        "solver": "lbfgs",
        "tol": 0.0001,
    }
    if learner != expected_learner:
        raise ValueError("V4 protocol learner settings differ from frozen V3.2")
    if protocol.get("stage_one_fitness") != (
        "accuracy_500 - 0.001*log1p(feature_dim) - "
        "0.0001*log1p(feature_runtime_ms + training_runtime_ms + inference_runtime_ms)"
    ):
        raise ValueError("V4 stage-one fitness definition has changed")
    return protocol


def evaluate_candidate(
    candidate: CandidateV4,
    evaluator: Evaluator,
    *,
    evaluator_version_sha256: str,
    protocol_status: str,
    cache_namespace: str | None = None,
) -> dict[str, Any]:
    """Evaluate one validated candidate and return score-only feedback."""
    if candidate.provenance.evaluation_seed != _TRAINING_SEED:
        raise ValueError("candidate evaluation seed must match the frozen seed 42")
    limits = candidate.language.limits
    compiler = ProgramCompiler(
        ProgramConstraints(
            track=SearchTrack.DISCOVERY,
            max_feature_dim=limits.max_feature_dim,
            max_depth=limits.max_expansion_depth,
            max_nodes=limits.max_expanded_nodes,
        )
    )
    pipeline = compiler.compile(candidate.expansion.expanded_ast)
    evaluation = evaluator.evaluate_pipeline(
        pipeline,
        cache_key=candidate.expanded_program_hash,
        cache_namespace=cache_namespace or f"mnist_v4_{candidate.language_hash}",
        train_sizes=(_TRAINING_SUBSET_SIZE,),
    )
    score = stage_one_fitness(evaluation)
    macros = candidate.language.macros
    new_macros = set(candidate.language.introduced_macros)

    return {
        "schema_version": 1,
        "status": "stage_one_only",
        "protocol_status": protocol_status,
        "discovery_ready": False,
        "evaluator_version_sha256": evaluator_version_sha256,
        "candidate": {
            "candidate_id": candidate.candidate_id,
            "language_sha256": candidate.language_hash,
            "parent_language_sha256": candidate.parent_language_hash,
            "program_sha256": candidate.program_hash,
            "expanded_program_sha256": candidate.expanded_program_hash,
            "evaluation_seed": candidate.provenance.evaluation_seed,
            "generation": candidate.provenance.generation,
        },
        "evaluation": {
            "accuracy_500": evaluation.accuracy_500,
            "feature_dimension": evaluation.feature_dim,
            "feature_runtime_ms": evaluation.feature_runtime_ms,
            "training_runtime_ms": evaluation.training_runtime_ms,
            "inference_runtime_ms": evaluation.inference_runtime_ms,
            "stage_one_fitness": score,
        },
        "complexity": {
            "program": {
                "expanded_nodes": candidate.expansion.info.node_count,
                "expanded_depth": candidate.expansion.info.depth,
            },
            "language": {
                "macro_count": len(macros),
                "introduced_macro_count": len(new_macros),
                "macro_canonical_bytes": sum(
                    len(macro.canonical_json.encode("utf-8")) for macro in macros
                ),
                "introduced_macro_canonical_bytes": sum(
                    len(macro.canonical_json.encode("utf-8"))
                    for macro in macros
                    if macro.name in new_macros
                ),
            },
            "language_penalty": {
                "status": "not_applied_pending_preregistration",
                "definition": None,
                "coefficient": None,
                "value": None,
            },
        },
        "discovery_fitness": None,
        "failure": None,
    }


def failure_artifact(
    *,
    evaluator_version_sha256: str,
    protocol_status: str | None,
    stage: str,
    error: Exception,
    candidate_id: str | None = None,
) -> dict[str, Any]:
    """Represent an invalid candidate or evaluator failure without a score."""
    return {
        "schema_version": 1,
        "status": "failed",
        "protocol_status": protocol_status,
        "discovery_ready": False,
        "evaluator_version_sha256": evaluator_version_sha256,
        "candidate": {"candidate_id": candidate_id} if candidate_id else None,
        "evaluation": None,
        "complexity": None,
        "discovery_fitness": None,
        "failure": {
            "stage": stage,
            "type": type(error).__name__,
            "message": str(error),
        },
    }
