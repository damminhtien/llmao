"""Freeze V3.2 search winners and characterize them with frozen V3.1 methods."""

from __future__ import annotations

import hashlib
import json
import statistics
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.metrics import accuracy_score

from bias_optimizer.data.mnist import (
    MNISTDataConfig,
    load_mnist_final_data,
    load_mnist_search_data,
)
from bias_optimizer.dsl.ast import Expr
from bias_optimizer.dsl.compiler import ProgramCompiler
from bias_optimizer.dsl.validator import ProgramConstraints, SearchTrack
from bias_optimizer.evaluation.artifacts import read_jsonl
from bias_optimizer.evaluation.complementarity import paired_complementarity
from bias_optimizer.evaluation.feature_cache import FeatureMatrixCache
from bias_optimizer.evaluation.protocol import (
    EvaluationDataset,
    load_frozen_protocol,
)
from bias_optimizer.evaluation.representations import (
    ProgramRepresentation,
    RepresentationDefinition,
    build_concatenated_representation,
    build_frozen_registry,
)
from bias_optimizer.evaluation.robustness import TRANSFORMATIONS, transform_images
from bias_optimizer.evaluation.runner import EvaluationRunner
from bias_optimizer.evaluation.schema import EvaluationResult
from bias_optimizer.novelty.behavior import (
    behavioral_novelty,
    pairwise_distance_profile,
)
from bias_optimizer.optimizer_bench.objective import ast_hash
from bias_optimizer.optimizer_bench.runner import ROOT, sha256, verify_protocol
from bias_optimizer.optimizer_bench.trace import read_trace

_WINNER_FILE = Path("results/v32/summary/frozen_winners.json")
_WINNER_HASH_FILE = Path("results/v32/summary/frozen_winners.sha256")
_CHAR_PROTOCOL_FILE = Path("results/v32/characterization_protocol.json")
_CHAR_PROTOCOL_HASH_FILE = Path("results/v32/characterization_protocol.sha256")


def _write_hashed_json(path: Path, payload: dict[str, Any], hash_path: Path) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = (json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode()
    digest = hashlib.sha256(encoded).hexdigest()
    path.write_bytes(encoded)
    hash_path.write_text(f"{digest}  {path.name}\n", encoding="ascii")
    return digest


def _read_hashed_json(path: Path, hash_path: Path) -> tuple[dict[str, Any], str]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    digest = sha256(path)
    expected = hash_path.read_text(encoding="ascii").strip()
    if expected != f"{digest}  {path.name}":
        raise ValueError(f"frozen artifact hash mismatch: {path}")
    return payload, digest


def freeze_winners(root: Path = ROOT) -> Path:
    root = Path(root)
    protocol = verify_protocol(root)
    if not (root / "results/v32/summary/semantic_ablation.json").is_file():
        raise ValueError("freeze winners only after the semantic-ablation summary is saved")
    manifest_path = root / "results/v32/manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    execution = manifest.get("primary_execution", {})
    seeds = tuple(
        int(seed)
        for seed in execution.get(
            "matched_analysis_seeds", protocol["budget"]["optimizer_seeds"]
        )
    )
    optimizers = tuple(protocol["primary_optimizers"])
    run_rows = {
        (row["optimizer"], int(row["optimizer_seed"])): row
        for row in manifest.get("runs", [])
        if row.get("phase") == "primary"
        and row.get("optimizer") in optimizers
        and int(row["optimizer_seed"]) in seeds
    }
    expected = {(name, seed) for name in optimizers for seed in seeds}
    if set(run_rows) != expected:
        raise ValueError("cannot freeze winners until every matched primary run is recorded")

    per_run = []
    representatives: dict[str, dict[str, Any]] = {}
    for optimizer in optimizers:
        optimizer_winners = []
        for seed in seeds:
            item = run_rows[(optimizer, seed)]
            trace_path = root / item["trace"]
            if sha256(trace_path) != item["trace_sha256"]:
                raise ValueError(f"primary trace hash mismatch: {item['trace']}")
            trace = read_trace(trace_path)
            if not trace.evaluated_candidates:
                raise ValueError(f"primary run has no candidates: {item['trace']}")
            row = max(
                trace.evaluated_candidates,
                key=lambda candidate: (
                    candidate.fitness,
                    -candidate.evaluation_index,
                    candidate.candidate_id,
                ),
            )
            if row.program is None or ast_hash(row.program) != row.candidate_id:
                raise ValueError("frozen per-run winner has an invalid canonical AST hash")
            winner = {
                "optimizer": optimizer,
                "optimizer_seed": seed,
                "run_complete": trace.complete,
                "evaluated_candidates": len(trace.evaluated_candidates),
                "candidate_id": row.candidate_id,
                "primary_fitness": row.fitness,
                "feature_dim": row.feature_dim,
                "program": row.program.to_dict(),
                "trace": item["trace"],
                "trace_sha256": item["trace_sha256"],
            }
            per_run.append(winner)
            optimizer_winners.append(winner)
        representatives[optimizer] = max(
            optimizer_winners,
            key=lambda winner: (
                winner["primary_fitness"],
                -winner["optimizer_seed"],
                winner["candidate_id"],
            ),
        )

    payload = {
        "schema_version": 1,
        "primary_protocol_sha256": protocol["protocol_sha256"],
        "protocol_seed_ids": protocol["budget"]["optimizer_seeds"],
        "matched_analysis_seed_ids": list(seeds),
        "selection_rule": "highest primary fitness among matched per-run winners; incomplete runs use the best observed candidate and retain their incomplete status",
        "per_run_winners": per_run,
        "representative_winners": representatives,
    }
    path = root / _WINNER_FILE
    _write_hashed_json(path, payload, root / _WINNER_HASH_FILE)
    return path


def freeze_characterization_protocol(root: Path = ROOT) -> Path:
    root = Path(root)
    primary = verify_protocol(root)
    winners, winner_hash = _read_hashed_json(
        root / _WINNER_FILE, root / _WINNER_HASH_FILE
    )
    v31, v31_manifest = load_frozen_protocol(root)
    core = v31["phases"]["A_core"]
    comp = v31["phases"]["B_complementarity"]
    robust = v31["phases"]["C_mechanism_robustness"]
    transformation = "translate_x_+2"
    transform_index = TRANSFORMATIONS.index(transformation)
    payload = {
        "schema_version": 1,
        "study_id": "v3.2-winner-characterization",
        "primary_protocol_sha256": primary["protocol_sha256"],
        "v31_protocol_sha256": v31_manifest["protocol"]["sha256"],
        "frozen_winners_sha256": winner_hash,
        "matched_analysis_seed_ids": winners["matched_analysis_seed_ids"],
        "panels": {
            "linear_accuracy": {
                "dataset": "mnist_validation",
                "probe": "linear_logreg",
                "train_size": 500,
                "seeds": core["seeds"],
            },
            "rbf_probe": {
                "dataset": "mnist_validation",
                "probe": "rbf_svm",
                "train_size": 500,
                "seeds": core["seeds"],
            },
            "hog_complementarity": {
                "dataset": "mnist_validation",
                "anchor": "hog",
                "probe": "linear_logreg",
                "train_size": 500,
                "seeds": comp["seeds"],
                "metric": "paired accuracy(hog + winner) - accuracy(hog)",
            },
            "robustness": {
                "dataset": "mnist_official_test_post_search",
                "probe": robust["probe"],
                "train_size": robust["train_size"],
                "seeds": robust["seeds"],
                "test_sample_size": robust["test_sample_size"],
                "test_sample_seed": robust["test_sample_seed"],
                "transformation": transformation,
                "transformation_seed": 20_261_010 + transform_index,
            },
            "behavioral_novelty": {
                "dataset": "mnist_validation",
                "probe_image_count": 128,
                "sampling_seed": 20_261_010,
                "labels_read": False,
                "metric": "normalized pairwise-distance-profile novelty against earlier candidates within each run",
                "adaptive_candidates_only_in_mean": True,
            },
        },
        "winner_rule": winners["selection_rule"],
        "feedback_to_search": False,
    }
    path = root / _CHAR_PROTOCOL_FILE
    _write_hashed_json(path, payload, root / _CHAR_PROTOCOL_HASH_FILE)
    return path


def _definition(name: str, program: Expr) -> RepresentationDefinition:
    constraints = ProgramConstraints(
        track=SearchTrack.DISCOVERY,
        max_feature_dim=128,
        max_depth=6,
        max_nodes=127,
        forbid_raw_pixels=True,
        require_vector_root=False,
    )
    compiler = ProgramCompiler(constraints)
    pipeline = compiler.compile(program)
    digest = ast_hash(program)
    version = f"v32:{digest}"
    return RepresentationDefinition(
        name=name,
        dimension=pipeline.feature_dim,
        version=version,
        role="v32_optimizer_winner",
        factory=lambda: ProgramRepresentation(name, compiler.compile(program), version),
    )


def _mean_sd(values: list[float]) -> dict[str, float | int]:
    return {
        "n": len(values),
        "mean": float(statistics.mean(values)),
        "sd": float(statistics.stdev(values)) if len(values) > 1 else 0.0,
    }


def _behavioral_diversity(root: Path, winners: dict[str, Any], probe_images: np.ndarray) -> dict[str, Any]:
    manifest = json.loads((root / "results/v32/manifest.json").read_text(encoding="utf-8"))
    seeds = set(winners["matched_analysis_seed_ids"])
    traces = [
        row
        for row in manifest.get("runs", [])
        if row.get("phase") == "primary"
        and int(row["optimizer_seed"]) in seeds
        and row.get("optimizer") in winners["representative_winners"]
    ]
    cache: dict[str, np.ndarray] = {}
    result: dict[str, Any] = {}
    for optimizer in sorted(winners["representative_winners"]):
        adaptive_novelty: list[float] = []
        structural_novelty: list[float] = []
        run_cell_counts: list[int] = []
        all_cells: set[tuple[int, ...]] = set()
        candidate_count = 0
        incomplete_runs = 0
        for item in traces:
            if item["optimizer"] != optimizer:
                continue
            if not item["complete"]:
                incomplete_runs += 1
            trace = read_trace(root / item["trace"])
            run_cells: set[tuple[int, ...]] = set()
            archive: dict[str, np.ndarray] = {}
            for row in trace.evaluated_candidates:
                candidate_count += 1
                run_cells.add(tuple(row.structural_descriptor))
                if (
                    row.metadata
                    and isinstance(row.metadata.get("structural_novelty"), (int, float))
                    and row.evaluation_index > 20
                ):
                    structural_novelty.append(float(row.metadata["structural_novelty"]))
                if row.program is None:
                    continue
                profile = cache.get(row.candidate_id)
                if profile is None:
                    rep = _definition("behavior_probe", row.program).create()
                    rep.fit(probe_images)
                    features = rep.transform(probe_images)
                    profile = pairwise_distance_profile(features)
                    cache[row.candidate_id] = profile
                novelty, _, _ = behavioral_novelty(
                    profile, archive, candidate_id=row.candidate_id
                )
                archive[row.candidate_id] = profile
                if row.evaluation_index > 20:
                    adaptive_novelty.append(novelty)
            run_cell_counts.append(len(run_cells))
            all_cells.update(run_cells)
        result[optimizer] = {
            "behavioral_novelty_mean": (
                float(statistics.mean(adaptive_novelty)) if adaptive_novelty else None
            ),
            "adaptive_candidate_count": len(adaptive_novelty),
            "structural_novelty_mean": (
                float(statistics.mean(structural_novelty)) if structural_novelty else None
            ),
            "descriptor_cell_coverage_mean": (
                float(statistics.mean(run_cell_counts)) if run_cell_counts else None
            ),
            "descriptor_cell_coverage_union": len(all_cells),
            "candidate_count": candidate_count,
            "incomplete_run_count": incomplete_runs,
        }
    return result


def characterize_winners(root: Path = ROOT) -> Path:
    root = Path(root)
    parent = verify_protocol(root)
    _, v31_manifest = load_frozen_protocol(root)
    winners, winner_hash = _read_hashed_json(
        root / _WINNER_FILE, root / _WINNER_HASH_FILE
    )
    char_protocol, char_hash = _read_hashed_json(
        root / _CHAR_PROTOCOL_FILE, root / _CHAR_PROTOCOL_HASH_FILE
    )
    if winners["primary_protocol_sha256"] != parent["protocol_sha256"]:
        raise ValueError("winner freeze does not match the primary V3.2 protocol")
    if char_protocol["frozen_winners_sha256"] != winner_hash:
        raise ValueError("characterization protocol does not match frozen winners")
    if char_protocol["v31_protocol_sha256"] != v31_manifest["protocol"]["sha256"]:
        raise ValueError("characterization protocol does not match frozen V3.1")

    search_data = load_mnist_search_data(MNISTDataConfig(data_dir=root / "data/mnist"))
    search_dataset = EvaluationDataset.from_mnist_search(search_data)
    registry = build_frozen_registry(root)
    winner_defs: dict[str, RepresentationDefinition] = {}
    for optimizer, row in winners["representative_winners"].items():
        program = Expr.from_dict(row["program"])
        definition = _definition(f"v32_{optimizer}", program)
        winner_defs[optimizer] = definition
        registry[definition.name] = definition
    runner = EvaluationRunner(
        registry,
        cache=FeatureMatrixCache(root / "cache/v32_winner_characterization"),
    )
    final_data = load_mnist_final_data(root / "data/mnist")
    robust = char_protocol["panels"]["robustness"]
    test_dataset = EvaluationDataset.from_mnist_official_test(
        search_data,
        final_data,
        test_sample_size=int(robust["test_sample_size"]),
        test_sample_seed=int(robust["test_sample_seed"]),
    )
    if test_dataset.evaluation_partition != "official_test":
        raise ValueError("robustness characterization must use the frozen official test panel")

    core_seed_ids = tuple(char_protocol["panels"]["linear_accuracy"]["seeds"])
    linear_probe = char_protocol["panels"]["linear_accuracy"]["probe"]
    rbf_probe = char_protocol["panels"]["rbf_probe"]["probe"]
    train_size = int(char_protocol["panels"]["linear_accuracy"]["train_size"])
    core_rows = [EvaluationResult.from_dict(row) for row in read_jsonl(root / "results/v31/core_matrix.jsonl")]
    hog_baseline = [
        row
        for row in core_rows
        if row.key.representation == "hog"
        and row.key.probe == linear_probe
        and row.key.train_size == train_size
        and row.key.seed in core_seed_ids
    ]

    outputs: dict[str, Any] = {}
    for optimizer, winner in winners["representative_winners"].items():
        definition = winner_defs[optimizer]
        linear_results = [
            runner.evaluate(
                dataset=search_dataset,
                representation=definition.name,
                probe=linear_probe,
                train_size=train_size,
                seed=int(seed),
            )
            for seed in core_seed_ids
        ]
        rbf_results = [
            runner.evaluate(
                dataset=search_dataset,
                representation=definition.name,
                probe=rbf_probe,
                train_size=train_size,
                seed=int(seed),
            )
            for seed in core_seed_ids
        ]
        augmented_name = f"hog_plus_{definition.name}"
        augmented = build_concatenated_representation(
            registry, "hog", definition.name
        )
        registry[augmented_name] = augmented
        runner.representations[augmented_name] = augmented
        complementarity_results = [
            runner.evaluate(
                dataset=search_dataset,
                representation=augmented_name,
                probe=linear_probe,
                train_size=train_size,
                seed=int(seed),
            )
            for seed in char_protocol["panels"]["hog_complementarity"]["seeds"]
        ]
        complementarity = paired_complementarity(hog_baseline, complementarity_results)

        robustness_rows = []
        for seed in robust["seeds"]:
            model = runner.fit_model(
                dataset=test_dataset,
                representation=definition.name,
                probe=robust["probe"],
                train_size=int(robust["train_size"]),
                seed=int(seed),
            )
            clean_predictions, _, _ = model.predict(test_dataset.evaluation_images)
            transformed_images = transform_images(
                test_dataset.evaluation_images,
                robust["transformation"],
                seed=int(robust["transformation_seed"]),
            )
            transformed_predictions, _, _ = model.predict(transformed_images)
            clean_accuracy = float(
                accuracy_score(test_dataset.evaluation_labels, clean_predictions)
            )
            transformed_accuracy = float(
                accuracy_score(test_dataset.evaluation_labels, transformed_predictions)
            )
            robustness_rows.append(
                {
                    "seed": int(seed),
                    "clean_accuracy": clean_accuracy,
                    "transformed_accuracy": transformed_accuracy,
                    "accuracy_drop": clean_accuracy - transformed_accuracy,
                    "prediction_agreement": float(
                        np.mean(clean_predictions == transformed_predictions)
                    ),
                    "evaluation_split_id": test_dataset.evaluation_split_id,
                }
            )
        outputs[optimizer] = {
            "optimizer_seed": winner["optimizer_seed"],
            "run_complete": winner["run_complete"],
            "evaluated_candidates": winner["evaluated_candidates"],
            "candidate_id": winner["candidate_id"],
            "primary_fitness": winner["primary_fitness"],
            "feature_dim": definition.dimension,
            "linear_accuracy": _mean_sd([row.accuracy for row in linear_results]),
            "linear_per_seed": {str(row.key.seed): row.accuracy for row in linear_results},
            "rbf_accuracy": _mean_sd([row.accuracy for row in rbf_results]),
            "rbf_per_seed": {str(row.key.seed): row.accuracy for row in rbf_results},
            "hog_complementarity_linear": {
                "mean_delta": float(
                    statistics.mean(float(row["delta_complementarity"]) for row in complementarity)
                ),
                "per_seed": {
                    str(row["seed"]): float(row["delta_complementarity"])
                    for row in complementarity
                },
            },
            "robustness": {
                "transformation": robust["transformation"],
                "accuracy_drop_mean": float(
                    statistics.mean(row["accuracy_drop"] for row in robustness_rows)
                ),
                "per_seed": robustness_rows,
                "evaluation_partition": test_dataset.evaluation_partition,
                "evaluation_split_id": test_dataset.evaluation_split_id,
            },
        }

    behavior = char_protocol["panels"]["behavioral_novelty"]
    rng = np.random.default_rng(int(behavior["sampling_seed"]))
    indices = np.sort(
        rng.choice(
            len(search_data.validation_images),
            size=int(behavior["probe_image_count"]),
            replace=False,
        )
    )
    probe_images = search_data.validation_images[indices]
    behavioral = _behavioral_diversity(root, winners, probe_images)
    result = {
        "schema_version": 1,
        "characterization_protocol_sha256": char_hash,
        "primary_protocol_sha256": parent["protocol_sha256"],
        "v31_protocol_sha256": v31_manifest["protocol"]["sha256"],
        "frozen_winners_sha256": winner_hash,
        "selection_rule": winners["selection_rule"],
        "winners": outputs,
        "behavioral_diversity": behavioral,
        "feedback_to_search": False,
    }
    output = root / "results/v32/summary/winner_characterization.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return output
