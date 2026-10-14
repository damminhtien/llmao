"""Language lineage summaries from verified structural replay observations."""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from collections.abc import Mapping, Sequence
from typing import Any

from bias_optimizer.v4.candidate.loader import load_language_lineage
from bias_optimizer.v4.candidate.provenance import CandidateValidationError
from bias_optimizer.v4.language import G0_LANGUAGE, macro_behavior_hash


def build_lineage_archive(
    replays: Sequence[Mapping[str, Any]],
    *,
    independent_search_ids: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """Keep observation, language, candidate, and computation identities distinct.

    Callers must obtain replays through ``replay_pilot``. Declared independent
    search identities come from a study contract, never worker-entry IDs.
    """
    declared = dict(independent_search_ids or {})
    runs = [replay["run_id"] for replay in replays]
    if len(runs) != len(set(runs)):
        raise CandidateValidationError("cannot archive the same run twice")
    if set(declared) - set(runs) or any(
        not isinstance(value, str) or not value.strip() for value in declared.values()
    ):
        raise CandidateValidationError(
            "independent search declarations must identify archived runs"
        )
    languages: dict[str, Any] = {
        G0_LANGUAGE.sha256: {
            "language_hash": G0_LANGUAGE.sha256,
            "kind": "G0",
            "snapshot": G0_LANGUAGE.to_dict(),
            "macro_behavior_inventory": [],
        },
    }
    edges: dict[tuple[str, str], Any] = {}
    primitives: dict[str, Any] = {}
    observations = []
    candidate_groups: dict[str, list[str]] = defaultdict(list)
    representation_groups: dict[str, list[str]] = defaultdict(list)
    for replay in replays:
        run_id = replay["run_id"]
        for source in replay["observations"]:
            checked = source["structural_check"]
            observation = dict(source)
            observation["run_id"] = run_id
            observation["independent_search_id"] = declared.get(run_id)
            observations.append(observation)
            if checked["status"] != "valid":
                continue
            observation_id = source["observation_id"]
            candidate_groups[checked["candidate_id"]].append(observation_id)
            representation_groups[checked["expanded_program_hash"]].append(
                observation_id
            )
            snapshots = source["lineage_state"]["language_lineage"]
            parent = G0_LANGUAGE
            for generation in range(len(snapshots)):
                language = load_language_lineage(snapshots[: generation + 1])
                behaviors = {
                    macro.name: macro_behavior_hash(macro, language)
                    for macro in language.macros
                }
                inventory = sorted(behaviors.values())
                vocabulary_hash = hashlib.sha256(
                    json.dumps(
                        {
                            "base_language_hash": G0_LANGUAGE.sha256,
                            "macro_behaviors": inventory,
                        },
                        sort_keys=True,
                        separators=(",", ":"),
                    ).encode()
                ).hexdigest()
                languages.setdefault(
                    language.sha256,
                    {
                        "language_hash": language.sha256,
                        "kind": "G*",
                        "snapshot": language.to_dict(),
                        "macro_behavior_inventory": inventory,
                        "semantic_vocabulary_hash": vocabulary_hash,
                    },
                )
                parent_macros = getattr(parent, "macro_map", {})
                current_macros = language.macro_map
                added = sorted(set(current_macros) - set(parent_macros))
                removed = sorted(set(parent_macros) - set(current_macros))
                changed = sorted(
                    name
                    for name in set(parent_macros) & set(current_macros)
                    if parent_macros[name].sha256 != current_macros[name].sha256
                )
                edge = edges.setdefault(
                    (parent.sha256, language.sha256),
                    {
                        "parent_language_hash": parent.sha256,
                        "child_language_hash": language.sha256,
                        "added_macros": added,
                        "removed_macros": removed,
                        "changed_macros": changed,
                        "observations_at_child": [],
                    },
                )
                if generation == len(snapshots) - 1:
                    edge["observations_at_child"].append(observation_id)
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
                    if source["eve_solver_entry_id"]:
                        primitive["observed_solver_entry_ids"].append(
                            source["eve_solver_entry_id"]
                        )
                    if macro.name in checked["used_macros"]:
                        primitive["use_observations"].append(observation_id)
                        primitive["use_run_ids"].append(run_id)
                        if declared.get(run_id):
                            primitive["declared_independent_search_ids"].append(
                                declared[run_id]
                            )
                        if macro.name not in added:
                            primitive["inherited_use_observations"].append(
                                observation_id
                            )
                    else:
                        primitive["unused_inventory_observations"].append(
                            observation_id
                        )
                parent = language
    by_id = {observation["observation_id"]: observation for observation in observations}
    if len(by_id) != len(observations):
        raise CandidateValidationError("observation identities must be unique")
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
            {
                by_id[identity]["structural_check"]["candidate_id"]
                for identity in inherited
            }
        )
        primitive["independent_search_reuse_established"] = (
            len(primitive["declared_independent_search_ids"]) > 1
            if primitive["use_run_ids"]
            and all(run in declared for run in primitive["use_run_ids"])
            else None
        )
        primitive["score_observations"] = [
            {
                "observation_id": identity,
                "score": by_id[identity]["original_evaluation"]["score"],
            }
            for identity in primitive["use_observations"]
        ]
    return {
        "schema_version": 1,
        "interpretation": "exploratory pilot lineage; not a discovery finding",
        "source_runs": [
            {
                "run_id": replay["run_id"],
                "source_manifest_sha256": replay["source_manifest_sha256"],
                "protocol_sha256": replay["protocol_sha256"],
                "independent_search_id": declared.get(replay["run_id"]),
            }
            for replay in replays
        ],
        "languages": [languages[key] for key in sorted(languages)],
        "edges": [edges[key] for key in sorted(edges)],
        "primitives": [primitives[key] for key in sorted(primitives)],
        "candidate_observations": dict(sorted(candidate_groups.items())),
        "expanded_representation_observations": dict(
            sorted(representation_groups.items())
        ),
        "observations": observations,
    }


def lineage_mermaid(archive: Mapping[str, Any]) -> str:
    """Emit a graph with safe generated node labels and digest prefixes."""
    identities = {
        item["language_hash"]: f"L{index}"
        for index, item in enumerate(archive["languages"])
    }
    lines = ["flowchart TD"]
    for language in archive["languages"]:
        digest = language["language_hash"]
        count = len(language["macro_behavior_inventory"])
        lines.append(
            f'  {identities[digest]}["{language["kind"]} {digest[:12]} / {count} macros"]'
        )
    for edge in archive["edges"]:
        parent = identities[edge["parent_language_hash"]]
        child = identities[edge["child_language_hash"]]
        lines.append(f"  {parent} --> {child}")
    return "\n".join(lines) + "\n"
