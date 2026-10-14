"""Verify archived pilot artifacts and replay structural checks without data."""

from __future__ import annotations

import csv
import hashlib
import json
import math
import shutil
import tempfile
from pathlib import Path
from typing import Any

from bias_optimizer.v4.candidate.check import (
    check_candidate_directory,
    validate_lineage_state,
)
from bias_optimizer.v4.candidate.loader import read_json
from bias_optimizer.v4.candidate.provenance import CandidateValidationError


def verify_artifact(record: dict[str, Any], root: Path) -> Path:
    """Verify a regular, repository-relative artifact against its recorded digest."""
    if set(record) != {"path", "sha256", "size_bytes"}:
        raise CandidateValidationError("artifact record has an invalid shape")
    relative = Path(record["path"])
    if relative.is_absolute() or ".." in relative.parts:
        raise CandidateValidationError(
            "artifact path must stay inside the artifact root"
        )
    root = root.resolve(strict=True)
    path = root / relative
    if any(part.is_symlink() for part in [path, *path.parents] if part != root):
        raise CandidateValidationError("artifact path must not contain symlinks")
    if not path.resolve(strict=True).is_relative_to(root) or not path.is_file():
        raise CandidateValidationError(
            "artifact must be a regular file inside its root"
        )
    content = path.read_bytes()
    if type(record["size_bytes"]) is not int or len(content) != record["size_bytes"]:
        raise CandidateValidationError(f"artifact size mismatch: {relative}")
    if hashlib.sha256(content).hexdigest() != record["sha256"]:
        raise CandidateValidationError(f"artifact digest mismatch: {relative}")
    return path


def replay_pilot(
    manifest_path: Path,
    *,
    artifact_root: Path,
    protocol_path: Path,
) -> dict[str, Any]:
    """Retain each original observation while rechecking immutable structure."""
    manifest = read_json(manifest_path)
    if manifest.get("schema_version") != 1 or manifest.get("phase") != 10:
        raise CandidateValidationError("expected a Phase 10 pilot manifest")
    protocol_digest = hashlib.sha256(protocol_path.read_bytes()).hexdigest()
    if protocol_digest != manifest["environment"]["protocol_sha256"]:
        raise CandidateValidationError(
            "replay protocol differs from the executed protocol"
        )
    verified = 0
    telemetry: dict[int, dict[str, str]] = {}
    for record in manifest["run"]["evidence_files"].values():
        path = verify_artifact(record, artifact_root)
        if path.name == "phase2_solvers.csv":
            with path.open(newline="", encoding="utf-8") as stream:
                for row in csv.DictReader(stream):
                    iteration = int(row["iteration"])
                    if iteration in telemetry:
                        raise CandidateValidationError(
                            "pilot telemetry repeats an iteration"
                        )
                    telemetry[iteration] = row
        verified += 1
    if set(telemetry) != set(range(1, len(manifest["attempts"]) + 1)):
        raise CandidateValidationError(
            "pilot telemetry must cover every proposal exactly once"
        )
    observations = []
    accepted_states: dict[str, dict[str, Any]] = {}
    for index, record in enumerate([manifest["seed"], *manifest["attempts"]]):
        if index and record.get("iteration") != index:
            raise CandidateValidationError(
                "pilot attempts must have contiguous ordered iterations"
            )
        files = record["files"]
        expected = {
            "language.json",
            "program.json",
            "lineage_state.json",
            "lineage_parent.json",
            "evaluation.json",
        }
        if set(files) != expected:
            raise CandidateValidationError(
                "pilot observation has an invalid file inventory"
            )
        paths = {
            name: verify_artifact(value, artifact_root) for name, value in files.items()
        }
        verified += len(paths)
        state = read_json(paths["lineage_state.json"])
        validate_lineage_state(state)
        parent = read_json(paths["lineage_parent.json"])
        evaluation = read_json(paths["evaluation.json"])
        score = evaluation["score"]
        if index and json.loads(telemetry[index]["score_json"]) != score:
            raise CandidateValidationError(
                "telemetry score differs from archived evaluation"
            )
        valid = score["status"] == "stage_one_only"
        if score["status"] not in {"stage_one_only", "failed"}:
            raise CandidateValidationError("unexpected pilot evaluation status")
        if valid != (evaluation["validation_error"] is None):
            raise CandidateValidationError("evaluation error contradicts its status")
        for name, value in score.items():
            if type(value) in (int, float) and not math.isfinite(value):
                raise CandidateValidationError(f"non-finite archived metric: {name}")
        if valid:
            if score["discovery_ready"] is not False:
                raise CandidateValidationError("pilot score must remain exploratory")
            for key in ("llmao_commit", "evaluator_version_sha256"):
                if score[key] != manifest["environment"][key]:
                    raise CandidateValidationError(f"score provenance mismatch: {key}")
            if state["generation"] == 0:
                parent_state = None
            else:
                snapshots = state["language_lineage"][:-1]
                parent_state = {
                    "schema_version": 1,
                    "candidate_id": score["parent_candidate_id"],
                    "generation": state["generation"] - 1,
                    "language_hash": parent["parent_language_hash"],
                    "language_lineage": snapshots,
                }
        else:
            parent_state = state
        if parent_state is not None:
            if accepted_states.get(parent_state["candidate_id"]) != parent_state:
                raise CandidateValidationError(
                    "parent is not a previously accepted candidate state"
                )
            if parent["v4_parent_candidate_id"] != parent_state["candidate_id"]:
                raise CandidateValidationError(
                    "parent candidate differs from accepted lineage"
                )
            if parent["parent_language_hash"] != parent_state["language_hash"]:
                raise CandidateValidationError(
                    "parent language differs from accepted lineage"
                )
            if parent["generation"] != parent_state["generation"] + 1:
                raise CandidateValidationError(
                    "proposal generation differs from accepted lineage"
                )
        with tempfile.TemporaryDirectory(prefix="v4-structural-replay-") as temporary:
            directory = Path(temporary)
            for name in ("language.json", "program.json"):
                shutil.copyfile(paths[name], directory / name)
            checked = check_candidate_directory(
                directory,
                parent_state=parent_state,
                protocol_path=protocol_path,
            )
        if (checked["status"] == "valid") != valid:
            raise CandidateValidationError(
                f"structural outcome changed for observation {index}"
            )
        if valid:
            if (
                checked["candidate_id"] != score["candidate_id"]
                or checked["candidate_id"] != state["candidate_id"]
            ):
                raise CandidateValidationError(
                    "archived candidate identity differs from content"
                )
            if checked["language_hash"] != state["language_hash"]:
                raise CandidateValidationError(
                    "archived language differs from lineage state"
                )
            if read_json(paths["language.json"]) != state["language_lineage"][-1]:
                raise CandidateValidationError(
                    "language file differs from current lineage snapshot"
                )
            if checked["feature_dimension"] != score["feature_dimension"]:
                raise CandidateValidationError(
                    "archived feature dimension differs from expansion"
                )
            if (
                parent["generation"] != state["generation"]
                or parent["v4_parent_candidate_id"] != score["parent_candidate_id"]
            ):
                raise CandidateValidationError(
                    "candidate parent provenance is inconsistent"
                )
            accepted_states[state["candidate_id"]] = state
        observations.append(
            {
                "observation_id": f"{manifest['run']['run_id']}:{'seed' if index == 0 else index}",
                "iteration": None if index == 0 else index,
                "is_seed": index == 0,
                "eve_solver_entry_id": telemetry[index]["solver_id"] if index else None,
                "worker_telemetry": telemetry[index] if index else None,
                "original_evaluation": evaluation,
                "structural_check": checked,
                "source_files": files,
                "lineage_state": state,
                "lineage_parent": parent,
            }
        )
    representations: dict[str, list[str]] = {}
    for observation in observations[1:]:
        checked = observation["structural_check"]
        if checked["status"] == "valid":
            representations.setdefault(checked["expanded_program_hash"], []).append(
                observation["observation_id"]
            )
    return {
        "schema_version": 1,
        "run_id": manifest["run"]["run_id"],
        "account_plan": manifest["environment"]["account_plan"],
        "protocol_sha256": protocol_digest,
        "source_manifest_sha256": hashlib.sha256(
            manifest_path.read_bytes()
        ).hexdigest(),
        "interpretation": "structural replay only; no data or new score evaluation",
        "verified_source_files": verified,
        "valid_proposals": sum(
            item["structural_check"]["status"] == "valid" for item in observations[1:]
        ),
        "invalid_proposals": sum(
            item["structural_check"]["status"] == "invalid" for item in observations[1:]
        ),
        "unique_valid_expanded_representations": len(representations),
        "expanded_representation_observations": representations,
        "observations": observations,
    }
