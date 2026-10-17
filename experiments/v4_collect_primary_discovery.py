"""Verify completed Phase 12 runs and assemble their primary lineage archive."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "experiments"))

from v4_primary_contract import read_hashed_json, validate_contract

from bias_optimizer.dsl.ast import Expr
from bias_optimizer.v4.candidate import CandidateProvenance, CandidateV4
from bias_optimizer.v4.candidate.loader import load_language_lineage
from bias_optimizer.v4.candidate.schema import load_macro_language
from bias_optimizer.v4.language import G0_LANGUAGE, macro_behavior_hash


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            raise ValueError(f"blank JSONL row at {path}:{number}")
        value = json.loads(line)
        if not isinstance(value, dict):
            raise TypeError(f"JSONL row at {path}:{number} must be an object")
        rows.append(value)
    return rows


def _verify_run_files(run_root: Path, manifest: dict[str, Any]) -> None:
    records = manifest.get("files")
    if not isinstance(records, list):
        raise TypeError("run manifest files must be a list")
    declared: set[str] = set()
    for record in records:
        relative = record.get("path")
        if not isinstance(relative, str) or relative in declared:
            raise ValueError("run manifest has an invalid or duplicate path")
        declared.add(relative)
        relative_path = Path(relative)
        if relative_path.is_absolute() or ".." in relative_path.parts:
            raise ValueError(f"run artifact path is unsafe: {relative}")
        source = run_root / relative
        if record.get("kind") == "symlink":
            if not source.is_symlink():
                raise ValueError(f"run symlink record changed: {relative}")
            if record.get("target") != os.readlink(source):
                raise ValueError(f"run symlink target changed: {relative}")
            continue
        resolved = source.resolve(strict=True)
        if run_root.resolve() not in resolved.parents or source.is_symlink() or not source.is_file():
            raise ValueError(f"run artifact is missing or unsafe: {relative}")
        raw = source.read_bytes()
        if _sha256(raw) != record.get("sha256") or len(raw) != record.get("size_bytes"):
            raise ValueError(f"run artifact digest or size differs: {relative}")

    actual: set[str] = set()
    for path in run_root.rglob("*"):
        if path.is_file() or path.is_symlink():
            relative = path.relative_to(run_root).as_posix()
            if relative not in {"run_manifest.json", "run_manifest.json.sha256"}:
                actual.add(relative)
    if actual != declared:
        raise ValueError(
            "run artifact inventory differs from its manifest: "
            f"unlisted={sorted(actual - declared)[:5]}, "
            f"missing={sorted(declared - actual)[:5]}"
        )


def _verified_run(contract_path: Path) -> dict[str, Any]:
    contract = validate_contract(
        contract_path,
        allow_existing_run_root=True,
    )
    run_root = Path(contract["verified_run_root"])
    manifest_path = run_root / "run_manifest.json"
    manifest, manifest_sha256 = read_hashed_json(manifest_path)
    sidecar = manifest_path.with_suffix(manifest_path.suffix + ".sha256")
    sidecar_fields = sidecar.read_text(encoding="ascii").split()
    if not sidecar_fields or sidecar_fields[0] != manifest_sha256:
        raise ValueError(f"run manifest sidecar mismatch: {manifest_path}")
    if manifest.get("status") != "complete":
        raise ValueError(f"seed {contract['seed']} is not a completed discovery run")
    if manifest.get("official_test_access") is not False:
        raise ValueError("run manifest does not affirm the official-test boundary")
    if (
        manifest.get("seed") != contract["seed"]
        or manifest.get("contract_sha256") != contract["verified_contract_sha256"]
        or manifest.get("protocol_sha256") != contract["verified_protocol_sha256"]
        or manifest.get("llmao_commit") != contract["llmao_commit"]
        or manifest.get("eve_commit") != contract["eve_commit"]
        or manifest.get("initial_programs_sha256") != contract["initial_programs_sha256"]
    ):
        raise ValueError("run manifest identity differs from its frozen contract")
    _verify_run_files(run_root, manifest)

    protocol = contract["verified_protocol"]
    limits = protocol["primary_discovery"]
    budget = limits["candidate_budget"]
    token_cap = limits["token_budget"]["reported_input_plus_output_tokens"]
    if (
        manifest.get("common_seed_count") != budget["common_initial_ast_count"]
        or manifest.get("unique_successful_expanded_asts")
        != budget["unique_successful_expanded_asts"]
        or manifest.get("adaptive_attempts", budget["adaptive_proposal_attempt_cap"] + 1)
        > budget["adaptive_proposal_attempt_cap"]
        or manifest.get("reported_input_plus_output_tokens", token_cap + 1) > token_cap
    ):
        raise ValueError("completed run does not reconcile with its preregistered budgets")

    trajectory = _read_jsonl(run_root / "trajectory.jsonl")
    proposals = [
        row
        for row in trajectory
        if row.get("kind") in {"adaptive_proposal", "interrupted_proposal"}
    ]
    attempts = int(manifest["adaptive_attempts"])
    if len(proposals) != attempts:
        raise ValueError("trajectory proposal count differs from the run manifest")
    numbered = [
        row.get("attempt") if row.get("kind") == "adaptive_proposal"
        else row.get("consumed_attempt")
        for row in proposals
    ]
    if sorted(numbered) != list(range(1, attempts + 1)):
        raise ValueError("adaptive and interrupted attempt numbers are not contiguous")
    token_total = sum(int(row.get("reported_input_plus_output_tokens", 0)) for row in proposals)
    if token_total != manifest.get("reported_input_plus_output_tokens"):
        raise ValueError("trajectory token totals differ from the run manifest")

    solver_rows = _read_jsonl(run_root / "solver_population.jsonl")
    optimizer_rows = _read_jsonl(run_root / "optimizer_population.jsonl")
    if len(solver_rows) != manifest.get("solver_population_entries"):
        raise ValueError("solver population count differs from the run manifest")
    if len(optimizer_rows) != manifest.get("optimizer_guidance_revisions"):
        raise ValueError("guidance revision count differs from the run manifest")
    if len({row.get("id") for row in solver_rows}) != len(solver_rows):
        raise ValueError("solver population contains duplicate entry IDs")

    successful = [row for row in solver_rows if row.get("evaluation_status") == "discovery_scored"]
    successful_hashes = {
        row.get("candidate", {}).get("expanded_program_sha256") for row in successful
    }
    successful_hashes.discard(None)
    if (
        len(successful) != manifest.get("successful_candidate_evaluations")
        or sorted(successful_hashes) != manifest.get("unique_expanded_ast_sha256")
        or len(successful_hashes) != manifest.get("unique_successful_expanded_asts")
    ):
        raise ValueError("candidate population does not reconcile with successful run counts")

    initial = [
        row
        for row in solver_rows
        if (row.get("primary_record") or {}).get("kind") == "common_initial_program"
    ]
    if len(initial) != budget["common_initial_ast_count"]:
        raise ValueError("the common initial program set is incomplete")
    initial_hashes = [row["primary_record"].get("expanded_program_sha256") for row in initial]
    if (
        len(set(initial_hashes)) != budget["common_initial_ast_count"]
        or any(
            row["primary_record"].get("program_manifest_sha256")
            != contract["initial_programs_sha256"]
            for row in initial
        )
    ):
        raise ValueError("common initial program identities do not match the contract")

    trajectory_by_entry = {
        row["solver_entry_id"]: row
        for row in proposals
        if isinstance(row.get("solver_entry_id"), str)
    }
    if len(trajectory_by_entry) != sum("solver_entry_id" in row for row in proposals):
        raise ValueError("trajectory contains duplicate solver entry IDs")
    return {
        "contract": contract,
        "contract_path": str(Path(contract_path).resolve()),
        "run_root": run_root,
        "run_manifest": manifest,
        "run_manifest_sha256": manifest_sha256,
        "solver_rows": solver_rows,
        "optimizer_rows": optimizer_rows,
        "trajectory": trajectory,
        "trajectory_by_entry": trajectory_by_entry,
        "successful_hashes": successful_hashes,
        "initial_hashes": initial_hashes,
    }


def _validated_candidate(
    row: dict[str, Any], *, protocol: dict[str, Any]
) -> tuple[CandidateV4, dict[str, Any]]:
    files = row.get("files")
    context = row.get("evaluation_context")
    state = row.get("lineage_state")
    parent_lineage = row.get("parent_language_lineage")
    parent = row.get("lineage_parent")
    artifact = row.get("evaluator_artifact")
    score = row.get("score_record")
    if (
        not isinstance(files, dict)
        or not isinstance(context, dict)
        or not isinstance(state, dict)
        or not isinstance(parent_lineage, list)
        or not isinstance(parent, dict)
        or not isinstance(artifact, dict)
        or not isinstance(score, dict)
    ):
        raise TypeError(f"successful solver entry {row.get('id')} lacks lineage evidence")
    try:
        language_data = json.loads(files["candidate/language.json"])
        program_data = json.loads(files["candidate/program.json"])
        parent_language = load_language_lineage(parent_lineage)
        language = load_macro_language(language_data, parent_language)
        program = Expr.from_dict(program_data)
        provenance = CandidateProvenance.from_dict(context["provenance"])
        if language.introduced_macros != provenance.invented_primitives:
            raise ValueError("introduced macro inventory differs from evaluator provenance")
        candidate = CandidateV4(
            candidate_id=context["candidate_id"],
            language=language,
            program=program,
            provenance=provenance,
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError(f"solver entry {row.get('id')} failed lineage replay: {exc}") from exc

    expected_identity = hashlib.sha256(
        f"{candidate.language_hash}\0{candidate.program.to_json()}".encode()
    ).hexdigest()
    generation = candidate.provenance.generation
    lineage_hashes: list[str] = []
    parent_language_replay = G0_LANGUAGE
    for index, snapshot in enumerate(state["language_lineage"]):
        step_language = load_macro_language(snapshot, parent_language_replay)
        lineage_hashes.append(step_language.sha256)
        parent_language_replay = step_language
        if index < len(state["language_lineage"]) - 1:
            continue
        if step_language.to_dict() != language.to_dict():
            raise ValueError("terminal lineage snapshot differs from candidate language")
    if (
        context["parent_language_lineage"] != parent_lineage
        or state["language_lineage"][:-1] != parent_lineage
        or len(parent_lineage) != generation
    ):
        raise ValueError("candidate parent lineage does not match its validated context")
    candidate_record = artifact.get("candidate", {})
    primary = row.get("primary_record") or {}
    expected_parent_hash = parent_language.sha256
    recorded_parent_hash = parent.get("parent_language_hash")
    if generation == 0:
        recorded_parent_hash = expected_parent_hash if recorded_parent_hash is None else recorded_parent_hash
    if (
        state.get("schema_version") != 1
        or len(state.get("language_lineage", [])) != generation + 1
        or state.get("candidate_id") != candidate.candidate_id
        or state.get("generation") != generation
        or state.get("language_hash") != candidate.language_hash
        or candidate.provenance.parent_candidate_id != parent.get("parent_candidate_id")
        or candidate.provenance.parent_candidate_id != primary.get("parent_candidate_id")
        or parent.get("generation") != generation
        or recorded_parent_hash != expected_parent_hash
        or language.parent_language_hash != expected_parent_hash
        or candidate_record.get("candidate_id") != candidate.candidate_id
        or candidate_record.get("language_sha256") != candidate.language_hash
        or candidate_record.get("program_sha256") != candidate.program_hash
        or candidate_record.get("expanded_program_sha256") != candidate.expanded_program_hash
        or candidate_record.get("parent_language_sha256") != candidate.parent_language_hash
        or candidate_record.get("parent_candidate_id") != candidate.provenance.parent_candidate_id
        or candidate_record.get("generation") != generation
        or primary.get("expanded_program_sha256") != candidate.expanded_program_hash
        or (
            primary.get("candidate_id") is not None
            and primary.get("candidate_id") != candidate.candidate_id
        )
        or (
            primary.get("language_sha256") is not None
            and primary.get("language_sha256") != candidate.language_hash
        )
        or (
            primary.get("generation") is not None
            and primary.get("generation") != generation
        )
        or (
            primary.get("introduced_macros") is not None
            and primary.get("introduced_macros")
            != list(candidate.provenance.invented_primitives)
        )
        or candidate.candidate_id != f"candidate-{expected_identity[:20]}"
        or candidate.provenance.evaluation_seed
        != protocol["evaluator_basis"]["training_subset_seed"]
        or candidate.provenance.model_backend.model_identifier
        != protocol["primary_design"]["exact_cli_model_identifier"]
        or candidate.provenance.model_backend.reasoning_effort
        != protocol["primary_design"]["requested_reasoning_effort"]
        or candidate.provenance.model_backend.backend
        != protocol["candidate_boundary"]["codex_driver"]
    ):
        raise ValueError(f"solver entry {row.get('id')} has inconsistent candidate lineage")
    if (
        score.get("status") != "discovery_scored"
        or score.get("discovery_ready") is not True
        or score.get("candidate_id") != candidate.candidate_id
        or score.get("discovery_fitness") != row.get("score", {}).get("score")
        or artifact.get("protocol_sha256") != protocol["protocol_sha256"]
    ):
        raise ValueError(f"solver entry {row.get('id')} has inconsistent score evidence")
    if generation == 0 and (
        parent_lineage
        or candidate.provenance.parent_candidate_id is not None
        or parent.get("parent_candidate_id") is not None
    ):
        raise ValueError("generation-zero candidates must descend directly from G0")
    if generation > 0 and (
        not parent_lineage or parent_language.sha256 != language.parent_language_hash
    ):
        raise ValueError("candidate parent language is missing from its lineage")
    return candidate, {
        "parent_language_hash": expected_parent_hash,
        "parent_lineage_hashes": lineage_hashes[:-1],
        "candidate_identity_sha256": expected_identity,
    }


def _language_record(language: Any) -> dict[str, Any]:
    if language is G0_LANGUAGE:
        return {
            "language_hash": G0_LANGUAGE.sha256,
            "kind": "G0",
            "snapshot": G0_LANGUAGE.to_dict(),
            "macro_behavior_inventory": [],
            "semantic_vocabulary_hash": _sha256(
                json.dumps(
                    {"base_language_hash": G0_LANGUAGE.sha256, "macro_behaviors": []},
                    sort_keys=True,
                    separators=(",", ":"),
                ).encode("utf-8")
            ),
        }
    behaviors = {
        macro.name: macro_behavior_hash(macro, language) for macro in language.macros
    }
    inventory = sorted(behaviors.values())
    vocabulary_hash = _sha256(
        json.dumps(
            {"base_language_hash": G0_LANGUAGE.sha256, "macro_behaviors": inventory},
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    )
    return {
        "language_hash": language.sha256,
        "kind": "G*",
        "snapshot": language.to_dict(),
        "macro_behavior_inventory": inventory,
        "semantic_vocabulary_hash": vocabulary_hash,
    }


def _build_lineage(
    runs: list[dict[str, Any]], protocol: dict[str, Any]
) -> dict[str, Any]:
    languages: dict[str, dict[str, Any]] = {G0_LANGUAGE.sha256: _language_record(G0_LANGUAGE)}
    edges: dict[tuple[str, str], dict[str, Any]] = {}
    primitives: dict[str, dict[str, Any]] = {}
    observations: list[dict[str, Any]] = []
    candidate_groups: dict[str, list[str]] = defaultdict(list)
    representation_groups: dict[str, list[str]] = defaultdict(list)

    for run in runs:
        contract = run["contract"]
        seed = contract["seed"]
        run_id = f"discovery-{seed}"
        for row in run["solver_rows"]:
            primary = row.get("primary_record") or {}
            entry_id = str(row.get("id"))
            observation_id = f"{run_id}:{entry_id}"
            trajectory = run["trajectory_by_entry"].get(entry_id, {})
            observation: dict[str, Any] = {
                "observation_id": observation_id,
                "run_id": run_id,
                "independent_search_id": f"seed-{seed}",
                "solver_entry_id": entry_id,
                "kind": primary.get("kind", "adaptive_proposal"),
                "attempt": trajectory.get("attempt"),
                "status": row.get("evaluation_status", "missing_evaluator_artifact"),
                "candidate_id": primary.get("candidate_id"),
                "parent_candidate_id": primary.get("parent_candidate_id"),
                "generation": primary.get("generation"),
                "score": row.get("score", {}).get("score"),
                "token_usage": row.get("token_usage"),
                "optimizer_token_usage": row.get("optimizer_token_usage"),
                "expanded_program_sha256": primary.get("expanded_program_sha256"),
                "language_sha256": primary.get("language_sha256"),
            }
            if row.get("evaluation_status") == "discovery_scored":
                candidate, replay = _validated_candidate(row, protocol=protocol)
                lineage_state = row["lineage_state"]
                snapshots = lineage_state["language_lineage"]
                used = set(candidate.provenance.used_primitives)
                observation.update(
                    {
                        "candidate_id": candidate.candidate_id,
                        "parent_candidate_id": candidate.provenance.parent_candidate_id,
                        "generation": candidate.provenance.generation,
                        "language_sha256": candidate.language_hash,
                        "parent_language_sha256": replay["parent_language_hash"],
                        "program_sha256": candidate.program_hash,
                        "expanded_program_sha256": candidate.expanded_program_hash,
                        "introduced_macros": list(candidate.provenance.invented_primitives),
                        "used_macros": sorted(used),
                        "guidance_sha256": candidate.provenance.guidance_hash,
                        "model_backend": candidate.provenance.model_backend.to_dict(),
                        "lineage_language_sha256": replay["parent_lineage_hashes"]
                        + [candidate.language_hash],
                    }
                )
                candidate_groups[candidate.candidate_id].append(observation_id)
                representation_groups[candidate.expanded_program_hash].append(observation_id)
                parent_language = G0_LANGUAGE
                for generation, snapshot in enumerate(snapshots):
                    language = load_macro_language(snapshot, parent_language)
                    language_record = _language_record(language)
                    languages.setdefault(language.sha256, language_record)
                    parent_macros = getattr(parent_language, "macro_map", {})
                    current_macros = language.macro_map
                    added = sorted(set(current_macros) - set(parent_macros))
                    removed = sorted(set(parent_macros) - set(current_macros))
                    changed = sorted(
                        name
                        for name in set(parent_macros) & set(current_macros)
                        if parent_macros[name].sha256 != current_macros[name].sha256
                    )
                    if parent_language.sha256 != language.sha256:
                        edge = edges.setdefault(
                            (parent_language.sha256, language.sha256),
                            {
                                "parent_language_hash": parent_language.sha256,
                                "child_language_hash": language.sha256,
                                "added_macros": added,
                                "removed_macros": removed,
                                "changed_macros": changed,
                                "observations_at_child": [],
                            },
                        )
                        if generation == len(snapshots) - 1:
                            edge["observations_at_child"].append(observation_id)
                    behaviors = {
                        macro.name: macro_behavior_hash(macro, language)
                        for macro in language.macros
                    }
                    for macro in language.macros:
                        behavior = behaviors[macro.name]
                        primitive = primitives.setdefault(
                            behavior,
                            {
                                "behavior_hash": behavior,
                                "aliases": [],
                                "definition_hashes": [],
                                "birth_events": [],
                                "use_observations": [],
                                "inherited_use_observations": [],
                                "unused_inventory_observations": [],
                                "observed_run_ids": [],
                                "use_run_ids": [],
                                "observed_solver_entry_ids": [],
                                "declared_independent_search_ids": [],
                            },
                        )
                        if macro.name not in primitive["aliases"]:
                            primitive["aliases"].append(macro.name)
                        if macro.sha256 not in primitive["definition_hashes"]:
                            primitive["definition_hashes"].append(macro.sha256)
                        birth = {
                            "language_hash": language.sha256,
                            "generation": generation,
                            "macro_name": macro.name,
                        }
                        if macro.name in added and birth not in primitive["birth_events"]:
                            primitive["birth_events"].append(birth)
                        if generation != len(snapshots) - 1:
                            continue
                        primitive["observed_run_ids"].append(run_id)
                        primitive["observed_solver_entry_ids"].append(entry_id)
                        if macro.name in used:
                            primitive["use_observations"].append(observation_id)
                            primitive["use_run_ids"].append(run_id)
                            primitive["declared_independent_search_ids"].append(f"seed-{seed}")
                            if macro.name not in added:
                                primitive["inherited_use_observations"].append(observation_id)
                        else:
                            primitive["unused_inventory_observations"].append(observation_id)
                    parent_language = language
            else:
                observation["failure_record"] = primary
            observations.append(observation)

    candidate_versions: dict[tuple[int, str], set[tuple[int, str]]] = defaultdict(set)
    for observation in observations:
        if observation["status"] == "discovery_scored":
            candidate_versions[(
                int(observation["run_id"].removeprefix("discovery-")),
                observation["candidate_id"],
            )].add((observation["generation"], observation["language_sha256"]))
    for observation in observations:
        parent_id = observation.get("parent_candidate_id")
        if not parent_id or observation["status"] != "discovery_scored":
            continue
        seed = int(observation["run_id"].removeprefix("discovery-"))
        parent_versions = candidate_versions.get((seed, parent_id), set())
        expected_parent = (
            observation["generation"] - 1,
            observation["parent_language_sha256"],
        )
        if expected_parent not in parent_versions:
            raise ValueError(f"candidate parent is absent from its search: {observation['observation_id']}")

    by_id = {item["observation_id"]: item for item in observations}
    for primitive in primitives.values():
        for key in (
            "aliases",
            "definition_hashes",
            "observed_run_ids",
            "use_run_ids",
            "observed_solver_entry_ids",
            "declared_independent_search_ids",
        ):
            primitive[key] = sorted(set(primitive[key]))
        inherited = primitive["inherited_use_observations"]
        primitive["descendant_observation_count"] = len(inherited)
        primitive["distinct_descendant_candidate_count"] = len(
            {by_id[item]["candidate_id"] for item in inherited}
        )
        primitive["independent_search_reuse_established"] = (
            len(primitive["declared_independent_search_ids"]) > 1
            if primitive["use_run_ids"]
            and len(primitive["declared_independent_search_ids"])
            == len(primitive["use_run_ids"])
            else None
        )
        primitive["score_observations"] = [
            {"observation_id": item, "score": by_id[item]["score"]}
            for item in primitive["use_observations"]
        ]

    return {
        "schema_version": 1,
        "interpretation": "preregistered Phase 12 discovery lineage; discovery evidence only",
        "protocol_sha256": runs[0]["contract"]["verified_protocol_sha256"],
        "source_runs": [
            {
                "run_id": f"discovery-{run['contract']['seed']}",
                "independent_search_id": f"seed-{run['contract']['seed']}",
                "contract_path": run["contract_path"],
                "contract_sha256": run["contract"]["verified_contract_sha256"],
                "run_root": str(run["run_root"]),
                "run_manifest_sha256": run["run_manifest_sha256"],
                "successful_evaluations": run["run_manifest"]["successful_candidate_evaluations"],
                "unique_expanded_asts": run["run_manifest"]["unique_successful_expanded_asts"],
            }
            for run in runs
        ],
        "languages": [languages[key] for key in sorted(languages)],
        "edges": [edges[key] for key in sorted(edges)],
        "primitives": [primitives[key] for key in sorted(primitives)],
        "candidate_observations": dict(sorted(candidate_groups.items())),
        "expanded_representation_observations": dict(sorted(representation_groups.items())),
        "observations": observations,
        "guidance_revisions": [
            {
                "run_id": f"discovery-{run['contract']['seed']}",
                "solver_entry_count": len(run["solver_rows"]),
                "optimizer_revision_count": len(run["optimizer_rows"]),
                "revisions": [
                    {
                        "id": item["id"],
                        "guidance_sha256": item["guidance_sha256"],
                        "score": item["score"],
                        "files": item["files"],
                    }
                    for item in run["optimizer_rows"]
                ],
            }
            for run in runs
        ],
    }


def _lineage_mermaid(archive: dict[str, Any]) -> str:
    identities = {
        item["language_hash"]: f"L{index}"
        for index, item in enumerate(archive["languages"])
    }
    lines = ["flowchart TD"]
    for language in archive["languages"]:
        digest = language["language_hash"]
        count = len(language["macro_behavior_inventory"])
        lines.append(f'  {identities[digest]}["{language["kind"]} {digest[:12]} / {count} macros"]')
    for edge in archive["edges"]:
        lines.append(
            f"  {identities[edge['parent_language_hash']]} --> "
            f"{identities[edge['child_language_hash']]}"
        )
    return "\n".join(lines) + "\n"


def collect(
    contract_paths: list[Path], *, output: Path, graph: Path
) -> dict[str, Any]:
    if len(contract_paths) != 5:
        raise ValueError("Phase 12 requires all five preregistered discovery contracts")
    runs = [_verified_run(path) for path in contract_paths]
    protocol = runs[0]["contract"]["verified_protocol"]
    expected_seeds = protocol["primary_discovery"]["discovery_seeds"]
    observed_seeds = sorted(run["contract"]["seed"] for run in runs)
    if observed_seeds != sorted(expected_seeds) or len(set(observed_seeds)) != 5:
        raise ValueError("contract set does not match all five preregistered seeds")
    protocol_hashes = {run["contract"]["verified_protocol_sha256"] for run in runs}
    if len(protocol_hashes) != 1:
        raise ValueError("discovery runs do not share one finalized protocol")
    initial_hash_sets = {tuple(sorted(run["initial_hashes"])) for run in runs}
    if len(initial_hash_sets) != 1:
        raise ValueError("discovery runs do not share the same twenty initial ASTs")
    resolved_output = output.expanduser().resolve(strict=False)
    resolved_graph = graph.expanduser().resolve(strict=False)
    if resolved_output == resolved_graph or resolved_output.exists() or resolved_graph.exists():
        raise FileExistsError("archive and graph must be distinct new paths")
    archive = _build_lineage(runs, protocol)
    archive["integrity"] = {
        "candidate_budget": protocol["primary_discovery"]["candidate_budget"],
        "token_budget": protocol["primary_discovery"]["token_budget"],
        "official_test_access": False,
        "run_manifests_reconciled": True,
        "candidate_lineage_replayed": True,
    }
    raw = (json.dumps(archive, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n").encode()
    graph_raw = _lineage_mermaid(archive).encode()
    for path, payload in ((resolved_output, raw), (resolved_graph, graph_raw)):
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("xb") as stream:
            stream.write(payload)
        digest_path = path.with_suffix(path.suffix + ".sha256")
        with digest_path.open("xb") as stream:
            stream.write(f"{_sha256(payload)}  {path.name}\n".encode("ascii"))
    return {
        "archive": str(resolved_output),
        "archive_sha256": _sha256(raw),
        "graph": str(resolved_graph),
        "graph_sha256": _sha256(graph_raw),
        "runs": len(runs),
        "observations": len(archive["observations"]),
        "languages": len(archive["languages"]),
        "language_edges": len(archive["edges"]),
        "primitive_behaviors": len(archive["primitives"]),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", type=Path, action="append", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--graph", type=Path, required=True)
    args = parser.parse_args()
    try:
        from .v4_artifact_paths import resolve_v4_output_path
    except ImportError:
        from v4_artifact_paths import resolve_v4_output_path

    output = resolve_v4_output_path(args.output, repo_root=ROOT)
    graph = resolve_v4_output_path(args.graph, repo_root=ROOT)
    print(json.dumps(collect(args.contract, output=output, graph=graph), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
