"""Freeze the V3.2 optimizer study protocol from immutable V2/V3/V3.1 inputs."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from bias_optimizer.domain.program_search import ProgramSearchRecord
from bias_optimizer.evaluation.protocol import load_frozen_protocol

ROOT = Path(__file__).resolve().parents[1]
V3_ARCHIVE = ROOT / "results/v3_program_search_discovery.jsonl"
V3_FINALISTS = ROOT / "results/v3_frozen_finalists.json"
V2_ARCHIVE = ROOT / "results/program_search_discovery.jsonl"
V32_DIR = ROOT / "results/v32"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _stage_one_score(evaluation: dict[str, Any]) -> float:
    runtime_ms = sum(
        float(evaluation[key])
        for key in (
            "feature_runtime_ms",
            "training_runtime_ms",
            "inference_runtime_ms",
        )
    )
    return (
        float(evaluation["accuracy_500"])
        - 0.001 * math.log1p(int(evaluation["feature_dim"]))
        - 0.0001 * math.log1p(runtime_ms)
    )


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def build_protocol() -> dict[str, Any]:
    v31_protocol, v31_manifest = load_frozen_protocol(ROOT)
    if _sha256(V3_ARCHIVE) != v31_manifest["v3_search_archive_sha256"]:
        raise ValueError("V3 search archive does not match the V3.1 freeze")

    v3_rows = _read_jsonl(V3_ARCHIVE)
    v3_records = tuple(ProgramSearchRecord.from_dict(row) for row in v3_rows)
    if len(v3_records) != 200:
        raise ValueError(f"expected 200 V3 records, found {len(v3_records)}")
    seeds = [record for record in v3_records if record.generation == 0]
    seed_asts = {record.bias.program.to_json() for record in seeds}
    if len(seeds) != 20 or len(seed_asts) != 20:
        raise ValueError("V3 archive must contain 20 unique generation-zero ASTs")

    v3_scored = sorted(
        (
            (
                _stage_one_score(record.to_dict()["evaluation"]),
                record.candidate_id,
                record,
            )
            for record in v3_records
        ),
        key=lambda item: (-item[0], item[1]),
    )
    v3_finalist_manifest = json.loads(V3_FINALISTS.read_text(encoding="utf-8"))
    finalist_ids = {
        row["candidate_id"] for row in v3_finalist_manifest.get("finalists", [])
    }
    finalist_scores = [
        score for score, candidate_id, _ in v3_scored if candidate_id in finalist_ids
    ]
    if len(finalist_scores) != 5:
        raise ValueError("expected five frozen V3 finalists in the V3 manifest")

    v2_rows = _read_jsonl(V2_ARCHIVE)
    if not v2_rows:
        raise ValueError("V2 search archive is empty")
    v2_best = max(_stage_one_score(row["evaluation"]) for row in v2_rows)

    protected_sources = v31_manifest["protected_source_files"]
    source_hashes = {
        relative: _sha256(ROOT / relative) for relative in sorted(protected_sources)
    }
    if source_hashes != protected_sources:
        raise ValueError("a protected V2/V3 file no longer matches the V3.1 freeze")

    seed_programs = [
        {
            "candidate_id": record.candidate_id,
            "ast_sha256": hashlib.sha256(
                record.bias.program.to_json().encode("utf-8")
            ).hexdigest(),
            "bias": record.bias.to_dict(),
        }
        for record in seeds
    ]
    stage_one_thresholds = {
        "v2_best": {
            "value": v2_best,
            "source_archive_sha256": _sha256(V2_ARCHIVE),
        },
        "v3_top_20_cutoff": {
            "value": v3_scored[19][0],
            "candidate_id": v3_scored[19][1],
            "source_archive_sha256": _sha256(V3_ARCHIVE),
        },
        "v3_frozen_finalist_floor": {
            "value": min(finalist_scores),
            "source_finalist_manifest_sha256": _sha256(V3_FINALISTS),
        },
    }

    return {
        "schema_version": 1,
        "study_id": "v3.2-optimizer-value-study",
        "frozen_on": datetime.now(UTC).date().isoformat(),
        "research_question": (
            "Does an LLM provide measurable value as an optimizer over structured "
            "inductive-bias program spaces, beyond conventional search methods?"
        ),
        "hypotheses": {
            "H1": "Iterative LLM search reaches strong candidate programs using fewer evaluated candidates than random search.",
            "H2": "Iterative LLM search improves over typed genetic programming under the same evaluation budget.",
            "H3": "Iterative LLM search outperforms one-shot LLM proposals with the same DSL, model, candidate budget, and initial seeds.",
            "H4_secondary_only": "Semantic DSL information contributes to LLM search quality.",
            "H5": "High search fitness does not guarantee a generally useful inductive bias.",
        },
        "claim_boundary": (
            "Under the frozen V3 typed program space and equal candidate-evaluation "
            "budget, iterative LLM-guided search reaches high-performing regions "
            "more efficiently than the tested random and genetic-programming baselines."
        ),
        "protected_inputs": {
            "v3_archive_sha256": _sha256(V3_ARCHIVE),
            "v3_finalist_manifest_sha256": _sha256(V3_FINALISTS),
            "v2_archive_sha256": _sha256(V2_ARCHIVE),
            "v31_protocol_sha256": v31_manifest["protocol"]["sha256"],
            "v31_manifest_sha256": _sha256(ROOT / "results/v31/manifest.json"),
            "v31_protocol_study_id": v31_protocol.get("study_id"),
            "protected_source_sha256": source_hashes,
        },
        "frozen_search_space": {
            "dsl_source": "src/bias_optimizer/dsl/primitives.py",
            "ast_type": "bias_optimizer.dsl.ast.Expr",
            "constraints": {
                "track": "discovery",
                "max_feature_dim": 128,
                "max_depth": 6,
                "max_nodes": 127,
                "forbid_raw_pixels": True,
                "require_vector_root": False,
                "root_types": ["Vector", "Scalar"],
            },
            "candidate_identity": "sha256 of canonical Expr.to_json() UTF-8 bytes; hypothesis metadata is excluded",
            "seed_programs": seed_programs,
            "seed_program_count": 20,
        },
        "objective": {
            "evaluator": "bias_optimizer.ml.evaluator.ProgramEvaluator",
            "train_sizes": [500],
            "fitness_property": "bias_optimizer.domain.evaluation.Evaluation.ranking_score",
            "formula": "accuracy_500 - 0.001*log1p(feature_dim) - 0.0001*log1p(runtime_ms)",
            "runtime_ms": "feature_runtime_ms + training_runtime_ms + inference_runtime_ms",
            "stage_one_only": True,
            "v31_characterization_metrics_excluded": True,
        },
        "data_and_learner": {
            "dataset": "MNIST OpenML mnist_784 v1; official 60,000-example training partition only",
            "validation_size": 2000,
            "validation_split_seed": 42,
            "training_subset_size": 500,
            "training_subset_seed": 42,
            "official_test_access": False,
            "learner": {
                "scaler": "StandardScaler",
                "classifier": "LogisticRegression",
                "C": 1.0,
                "solver": "lbfgs",
                "max_iter": 1000,
                "tol": 0.0001,
                "random_state": 42,
            },
        },
        "primary_optimizers": [
            "typed_random",
            "genetic_programming",
            "llm_one_shot",
            "llm_iterative",
        ],
        "budget": {
            "total_unique_evaluations_per_run": 200,
            "seed_evaluations": 20,
            "adaptive_new_evaluations": 180,
            "max_proposal_attempts_per_run": 540,
            "optimizer_seeds": [101, 202, 303, 404, 505],
            "smoke_optimizer_seeds": [101],
            "smoke_total_evaluations_per_optimizer": 40,
        },
        "typed_random_policy": {
            "target_depth_distribution": "uniform integer from 1 through 6",
            "root_type_distribution": "uniform over Vector and Scalar",
            "primitive_selection": "uniform over output-type-compatible primitives with a legal completion within the remaining target depth",
            "parameter_policy": "uniform over frozen, finite legal parameter presets; empty parameters use the DSL defaults",
            "canonical_duplicate_policy": "reject duplicate canonical AST hashes without evaluator calls",
        },
        "genetic_programming": {
            "initial_population": "same 20 V3 seed programs, already evaluated by the shared runner",
            "tournament_size": 3,
            "elitism": 2,
            "offspring_operator": "one operator per offspring: crossover with probability 0.5, otherwise mutation with probability 0.5",
            "mutation": "typed subtree mutation or legal parameter mutation, selected uniformly",
            "crossover": "typed subtree swap at matching ValueType sites",
            "large_hyperparameter_sweep": False,
        },
        "llm": {
            "model": "qwen3.5:35b-mlx",
            "provider": "local Ollama",
            "temperature": 0.65,
            "thinking": False,
            "num_predict": 6000,
            "timeout_seconds": 600,
            "request_seed_policy": "proposal batch index + repair-attempt index - 1, reset for each independent run",
            "proposal_batch_size": 4,
            "mechanism_family_schedule": [
                "order_sensitive",
                "spatial_relational",
                "graph_relational",
                "free_exploration",
            ],
            "one_shot_feedback": "DSL, task, constraints, model settings, fixed mechanism schedule, and the 20 seed AST examples only; no candidate scores, evaluated history, descriptor coverage, or adaptive ban list",
            "iterative_feedback": "V3 prompt format: top five MAP-Elites elites with accuracy_500, optional accuracy_5000 if present, feature dimension, descriptor, structural novelty, hypothesis and mechanism; all evaluated AST signatures; underexplored descriptor cells; generation and mechanism focus",
            "iterative_excluded_feedback": [
                "confusion matrices",
                "V3.1 characterization metrics",
                "official test data or labels",
            ],
        },
        "primary_metrics": {
            "search_curve_indices": list(range(20, 201)),
            "auc": "trapezoidal integral of best-so-far fitness against evaluated-candidate count from 20 through 200",
            "thresholds": stage_one_thresholds,
            "top_k": 5,
            "summary_statistics": ["mean", "median", "sd", "min", "max"],
            "paired_bootstrap": {
                "resamples": 10000,
                "seed": 20261010,
                "unit": "paired optimizer-seed index",
            },
        },
        "secondary_semantic_ablation": {
            "order": "after primary benchmark is frozen and complete",
            "conditions": ["semantic_dsl", "anonymized_dsl"],
            "optimizer": "llm_iterative",
            "optimizer_seeds": [101, 202, 303],
            "evaluations_per_run": 200,
            "anonymization": "Replace operator names and vision-specific lexical labels with op_01... while preserving signatures, types, parameter constraints and mathematical behavior; interpretation is lexical-semantic only.",
        },
        "winner_characterization": {
            "selection_rule": "highest primary fitness among the five frozen per-run winners in each optimizer condition",
            "metrics": [
                "linear accuracy",
                "RBF probe",
                "HOG complementarity",
                "representation dimension",
                "V3.1 robustness or counterfactual test where applicable",
            ],
            "feeds_back_into_search": False,
        },
        "interpretation_matrix": {
            "iterative_llm_gt_gp_gt_random": "semantic prior plus feedback appears useful for search efficiency",
            "gp_approx_iterative_llm_gt_random": "adaptive structured search matters, with little added LLM value",
            "one_shot_approx_iterative_llm_gt_gp_random": "pretrained semantic prior helps while empirical feedback adds little",
            "iterative_llm_gt_one_shot_approx_gp": "feedback matters without a unique LLM advantage",
            "all_approx_equal": "search space may be easy or the LLM may be unnecessary",
            "random_gt_llm": "LLM prior may bias search toward familiar but suboptimal regions",
        },
    }


def freeze_protocol(*, refreeze: bool = False) -> str:
    V32_DIR.mkdir(parents=True, exist_ok=True)
    protocol_path = V32_DIR / "protocol.json"
    if protocol_path.exists() and not refreeze:
        raise FileExistsError(
            "protocol is already frozen; use --refreeze only for a smoke-discovered implementation bug"
        )
    protocol = build_protocol()
    encoded = json.dumps(protocol, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    temporary = protocol_path.with_suffix(".json.tmp")
    temporary.write_text(encoded, encoding="utf-8")
    temporary.replace(protocol_path)
    digest = _sha256(protocol_path)
    (V32_DIR / "protocol.sha256").write_text(
        f"{digest}  protocol.json\n", encoding="ascii"
    )
    manifest = {
        "schema_version": 1,
        "study_id": "v3.2-optimizer-value-study",
        "protocol": {"path": "results/v32/protocol.json", "sha256": digest},
        "protected_inputs": protocol["protected_inputs"],
        "runs": [],
        "status": "protocol_frozen",
    }
    manifest_path = V32_DIR / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return digest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--refreeze",
        action="store_true",
        help="replace the protocol only after a smoke-discovered implementation bug",
    )
    args = parser.parse_args()
    print(f"Frozen protocol SHA-256: {freeze_protocol(refreeze=args.refreeze)}")


if __name__ == "__main__":
    main()
