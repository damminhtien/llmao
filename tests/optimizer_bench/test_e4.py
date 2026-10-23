from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path

from bias_optimizer.dsl.ast import Expr
from bias_optimizer.dsl.validator import SearchTrack
from bias_optimizer.llm.program_proposer import ProgramSearchContext
from bias_optimizer.optimizer_bench.e1 import (
    _e1_prompt,
    canonical_e1_program,
    e1_output_schema,
    load_e1_pilot_language,
    verify_e1_grammar,
)
from bias_optimizer.optimizer_bench.runner import load_seed_programs, verify_protocol
from bias_optimizer.optimizer_bench.schema import CandidateEvaluation, SearchTrace
from bias_optimizer.v4.language.base_language import EXCLUDED_V3_OPERATIONS

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
_SPEC = importlib.util.spec_from_file_location("llmao_e4_runner", ROOT / "experiments/e4.py")
if _SPEC is None or _SPEC.loader is None:
    raise RuntimeError("cannot load E4 command module for tests")
e4 = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = e4
_SPEC.loader.exec_module(e4)
e1_runner = e4.e1_runner


def _operation_constants(value: object) -> set[str]:
    found: set[str] = set()
    if isinstance(value, dict):
        properties = value.get("properties")
        operation = properties.get("op") if isinstance(properties, dict) else None
        if isinstance(operation, dict) and isinstance(operation.get("const"), str):
            found.add(operation["const"])
        for child in value.values():
            found.update(_operation_constants(child))
    elif isinstance(value, list):
        for child in value:
            found.update(_operation_constants(child))
    return found


def test_e4_recipe_guidance_preserves_the_same_frozen_g0_behaviors() -> None:
    language, _ = load_e1_pilot_language(ROOT)
    expansions = e4._macro_default_expansions(language)
    recipes = e4._recipe_guidance(expansions, macros_enabled=False)
    macro_guidance = e4._recipe_guidance(expansions, macros_enabled=True)
    g0_operations = set(verify_e1_grammar(None)["g0_operations"])
    pilot_operations = _operation_constants(e1_output_schema(language))

    assert set(expansions) == set(language.macro_map)
    assert all(name not in recipes for name in language.macro_map)
    assert all(name in macro_guidance for name in language.macro_map)
    assert pilot_operations - g0_operations == set(language.macro_map)
    assert not pilot_operations.intersection(EXCLUDED_V3_OPERATIONS)
    for ast in expansions.values():
        encoded_tree = json.dumps(ast.to_dict(), sort_keys=True, separators=(",", ":"))
        assert encoded_tree in recipes
        assert encoded_tree in macro_guidance
        expanded, macro_names = canonical_e1_program(ast, None)
        assert expanded.to_json() == ast.to_json()
        assert macro_names == ()


def test_e4_pilot_macros_expand_deterministically_to_valid_unique_g0_programs() -> None:
    language, _ = load_e1_pilot_language(ROOT)
    expansions = e4._macro_default_expansions(language)
    policy = e4._verify_policy_and_caps(language, expansions)

    assert policy["g0_excludes_pilot_macros"] is True
    assert policy["focus_is_guidance_only"] is True
    assert policy["strict_structure_and_duplicate_checks"] is True
    assert policy["resource_caps"]["attempts_per_condition"] == 20
    for macro in language.macros:
        call = Expr(macro.name, tuple(Expr("image") for _ in macro.input_types), {})
        expanded, used = canonical_e1_program(call, language)
        direct, direct_used = canonical_e1_program(expanded, None)
        assert used == (macro.name,)
        assert direct_used == ()
        assert expanded.to_json() == direct.to_json()
        assert e4.ast_hash(expanded) == e4.ast_hash(direct)


def test_e4_reuses_the_same_frozen_initial_score_records_without_recomputing() -> None:
    protocol = verify_protocol(ROOT)
    seeds = load_seed_programs(protocol)
    rows = e4._load_shared_initial_scores(seeds)
    seen: list[tuple[str, tuple]] = []

    def observe(condition: str, initial_rows: tuple):
        seen.append((condition, initial_rows))
        return condition

    e1_runner._run_pair_with_shared_scores(rows, observe)
    assert len(rows) == 20
    assert seen[0][1] is seen[1][1]
    assert seen[0][1] is rows
    assert seen[1][1] is rows


def test_e4_prompt_guidance_is_attached_without_changing_focus_context() -> None:
    language, _ = load_e1_pilot_language(ROOT)
    expansions = e4._macro_default_expansions(language)
    guidance = e4._recipe_guidance(expansions, macros_enabled=False)
    context = ProgramSearchContext(
        generation=1,
        track=SearchTrack.DISCOVERY,
        max_feature_dim=128,
        top_candidates=(),
        underexplored_cells=(),
        mechanism_focus="free_exploration",
    )
    prompt = _e1_prompt(context, 1, None, 1, guidance)

    assert "Requested mechanism family for this batch: free_exploration." in prompt
    assert guidance in prompt
    assert all(name not in prompt for name in language.macro_map)
    assert not any(operation in prompt for operation in EXCLUDED_V3_OPERATIONS)


def test_e4_candidate_auc_uses_the_shared_adaptive_evaluation_range() -> None:
    conditions = {
        "g0_recipes": {
            "counts": {"scored_adaptive_candidates": 2},
            "fitness": {"adaptive_unique_candidate_curve": [0.4, 0.6, 0.7]},
        },
        "g_pilot_macros": {
            "counts": {"scored_adaptive_candidates": 1},
            "fitness": {"adaptive_unique_candidate_curve": [0.4, 0.5]},
        },
    }
    e4._set_comparable_candidate_auc(conditions)

    assert conditions["g0_recipes"]["fitness"]["comparable_adaptive_evaluation_range"] == 1
    assert conditions["g_pilot_macros"]["fitness"]["comparable_adaptive_evaluation_range"] == 1
    assert conditions["g0_recipes"]["fitness"]["adaptive_candidate_auc_trapezoid"] == 0.5
    assert conditions["g_pilot_macros"]["fitness"]["adaptive_candidate_auc_trapezoid"] == 0.45


def test_e4_curve_segments_preserve_attempt_and_candidate_indices() -> None:
    assert e4._curve_segments(
        [0.4, 0.4, 0.6], label="attempt", first_index=1
    ) == "attempt 1–2: 0.400000; attempt 3–3: 0.600000"
    assert e4._curve_segments(
        [0.4, 0.4], label="k", first_index=0
    ) == "k 0–1: 0.400000"


def test_e4_macro_adoption_is_counted_from_raw_ast_even_when_archive_is_expanded() -> None:
    protocol = verify_protocol(ROOT)
    seeds = load_seed_programs(protocol)
    initial_rows = e4._load_shared_initial_scores(seeds)
    language, _ = load_e1_pilot_language(ROOT)
    macro_name = "stroke_degree_profile"
    macro = language.macro_map[macro_name]
    raw_program = Expr(macro.name, tuple(Expr("image") for _ in macro.input_types), {})
    expanded, _ = canonical_e1_program(raw_program, language)
    initial_prompt = "fixed prompt"
    raw_response = json.dumps(
        {
            "proposals": [
                {
                    "name": "raw macro use",
                    "hypothesis": "A reused pattern may be useful.",
                    "mechanism": "structural recipe",
                    "program": raw_program.to_dict(),
                    "prediction": "Fitness may improve.",
                    "falsification": "Reject if the score does not improve.",
                }
            ]
        }
    )
    call = {
        "requested_proposal_slots": 1,
        "raw_response": raw_response,
        "prompt_sha256": hashlib.sha256(initial_prompt.encode()).hexdigest(),
        "prompt_tokens": 10,
        "response_tokens": 5,
        "elapsed_ms": 20.0,
        "schema_sha256": "fixture",
    }
    # The normalized archive intentionally contains only the expanded G0 form.
    archive = {"prompt": initial_prompt, "response": json.dumps(expanded.to_dict())}
    score = CandidateEvaluation(
        candidate_id=e4.ast_hash(expanded),
        evaluation_index=21,
        fitness=0.5,
        accuracy=0.5,
        feature_dim=19,
        runtime_ms=1.0,
        structural_descriptor=("pixel", "orderless", "global", "single", "compact"),
        program=expanded,
        metadata={"proposal_attempt": 1},
    )
    trace = SearchTrace(
        optimizer="llm_iterative",
        optimizer_seed=202,
        evaluated_candidates=(*initial_rows, score),
        proposal_attempts=1,
        valid_proposal_count=1,
        invalid_count=0,
        duplicate_count=0,
        rejected_by_constraint_count=0,
        llm_calls=1,
        llm_tokens=15,
        proposal_time_ms=20.0,
        evaluation_time_ms=1.0,
        total_wall_time_ms=21.0,
        complete=True,
        termination_reason="adaptive_attempt_cap_reached",
        budget_total_evaluations=40,
        budget_seed_evaluations=20,
        budget_max_proposal_attempts=20,
    )

    parsed = e4._parse_raw_proposals(
        [call],
        [archive],
        trace,
        language,
        {row.candidate_id for row in initial_rows},
        {macro_name: expanded},
    )

    assert parsed["raw_macro_proposals_by_name"][macro_name] == 1
    assert parsed["typed_valid_macro_proposals_by_name"][macro_name] == 1
    assert parsed["raw_structural_pattern_proposals_by_name"][macro_name] == 1
    assert parsed["scored_macro_invocations_by_name"][macro_name] == 1
    assert parsed["proposal_slots"][0]["status"] == "scored"
