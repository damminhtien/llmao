"""Freeze the V4 primary protocol from the approved pre-discovery design."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

if __package__:
    from .v4_primary_contract import (
        EVE_ROOT,
        ROOT,
        git_value,
        sha256_file,
        tracked_tree_is_clean,
    )
else:
    from v4_primary_contract import (
        EVE_ROOT,
        ROOT,
        git_value,
        sha256_file,
        tracked_tree_is_clean,
    )

_PENDING_PREREGISTRATION_DECISIONS = {
    "evaluator_compiler_snapshot_and_worker_permissions_context_policy",
    "candidate_and_token_budgets_seeds_attempt_cap_timeouts_incomplete_run_policy",
    "common_initial_program_manifest",
    "language_complexity_penalty_definition_and_coefficient",
    "discovery_only_language_selection_rule_and_tie_breakers",
    "AUC_bounds_normalization_primary_contrast_statistics_and_numeric_support_criteria",
}


def _write_exclusive(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(payload)


def _source_pins() -> dict[str, str]:
    paths = {
        *(
            path.relative_to(ROOT).as_posix()
            for path in (ROOT / "src/bias_optimizer").rglob("*.py")
        ),
        *(
            path.relative_to(ROOT).as_posix()
            for path in (ROOT / "experiments").glob("v4_*.py")
        ),
        *(
            path.relative_to(ROOT).as_posix()
            for path in (ROOT / "configs/v4/phase12_primary").rglob("*")
            if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc"
        ),
        "configs/v4/phase12_primary_worker.md",
        "scripts/codex-v4-sandbox",
        "pyproject.toml",
        "uv.lock",
        "V4_PROTOCOL.md",
        "V4_PRIMARY_DESIGN.md",
        "V4_SANDBOX_REPAIR.md",
        "V4_INITIAL_PROGRAMS.json",
        "results/v4/languages/g0.json",
        "results/v4/languages/g0.json.sha256",
        "results/v4/languages/gh.json",
        "results/v4/languages/gh.json.sha256",
    }
    if not (ROOT / "uv.lock").is_file():
        paths.remove("uv.lock")
    return {relative: sha256_file(ROOT / relative) for relative in sorted(paths)}


def _require_clean_commits() -> tuple[str, str]:
    if not tracked_tree_is_clean(ROOT):
        raise SystemExit("commit all primary source changes before finalizing the protocol")
    if git_value(EVE_ROOT, "status", "--porcelain", "--untracked-files=all"):
        raise SystemExit("EvE checkout must be clean before protocol finalization")
    return git_value(ROOT, "rev-parse", "HEAD"), git_value(EVE_ROOT, "rev-parse", "HEAD")


def _supersedes_record(path: Path, *, root: Path = ROOT) -> dict[str, str]:
    root = root.resolve(strict=True)
    source = Path(path)
    if not source.is_absolute():
        source = root / source
    source = source.resolve(strict=True)
    if root not in source.parents:
        raise ValueError("superseded protocol must be inside the repository")
    raw = source.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    sidecar = source.with_suffix(source.suffix + ".sha256")
    fields = sidecar.read_text(encoding="utf-8").split()
    if not fields or fields[0] != digest:
        raise ValueError("superseded protocol digest does not verify")
    previous = json.loads(raw)
    version = previous.get("version")
    if previous.get("status") != "finalized_primary" or not isinstance(version, str):
        raise ValueError("superseded protocol is not a finalized primary protocol")
    return {"path": source.relative_to(root).as_posix(), "version": version, "sha256": digest}


def finalize_protocol(
    destination: Path,
    *,
    version: str = "v4-primary-1",
    supersedes: Path | None = None,
) -> dict[str, Any]:
    if not re.fullmatch(r"v4-primary-[1-9][0-9]*", version):
        raise ValueError("primary protocol version must look like v4-primary-N")
    llmao_commit, eve_commit = _require_clean_commits()
    historical_path = ROOT / "results/v4/protocol.json"
    historical_sha = sha256_file(historical_path)
    sidecar_fields = (ROOT / "results/v4/protocol.sha256").read_text().split()
    if not sidecar_fields or sidecar_fields[0] != historical_sha:
        raise ValueError("historical pilot protocol digest does not verify")
    initial_digest = sha256_file(ROOT / "V4_INITIAL_PROGRAMS.json")
    initial_fields = (ROOT / "V4_INITIAL_PROGRAMS.sha256").read_text().split()
    if not initial_fields or initial_fields[0] != initial_digest:
        raise ValueError("common initial-program digest does not verify")

    protocol = json.loads(historical_path.read_text(encoding="utf-8"))
    protocol.update(
        status="finalized_primary",
        version=version,
        finalized_at_utc=datetime.now(UTC).isoformat(),
        historical_pilot_protocol={
            "path": "results/v4/protocol.json",
            "sha256": historical_sha,
            "status": "draft_only_pending_preregistration",
        },
        discovery_language_complexity_penalty={
            "definition": "number of invented macros in the complete language inventory",
            "coefficient": 0.0005,
            "formula": "discovery_fitness = stage_one_fitness - 0.0005 * C(G)",
            "applies_to": "joint_language_discovery_only",
            "max_language_penalty": 0.004,
        },
        candidate_feedback={
            **protocol["candidate_feedback"],
            "allowed_outputs": [
                "accuracy_500",
                "feature_dimension",
                "feature_runtime_ms",
                "training_runtime_ms",
                "inference_runtime_ms",
                "stage_one_fitness",
                "language_complexity",
                "language_penalty",
                "discovery_fitness",
                "program_complexity_components",
                "structured_failure",
            ],
            "discovery_fitness_available": True,
            "language_penalty_applied": True,
            "status": "finalized_primary_only",
        },
        primary_design={
            "exact_cli_model_identifier": "gpt-6-luna",
            "requested_reasoning_effort": "max",
            "backend": "codex_tmux",
            "driver_executable": "scripts/codex-v4-sandbox",
            "initial_language": "G0",
            "language_evolution_enabled": True,
            "context_cap_readonly_solver_examples": 32,
            "native_turn_cap_per_proposal": 80,
            "proposal_timeout_seconds": 3600,
            "boundary_repair_attempts": 0,
            "evaluator_timeout_seconds": 1800,
            "official_test_access": False,
            "paid_credits": False,
            "plan_upgrade": False,
            "live_account_usage_gate": False,
        },
        implementation_pins={
            "llmao_commit": llmao_commit,
            "eve_commit": eve_commit,
            "initial_programs_path": "V4_INITIAL_PROGRAMS.json",
            "initial_programs_sha256": initial_digest,
            "split_fingerprints_sha256": protocol["evaluator_basis"][
                "split_fingerprints_sha256"
            ],
        },
        primary_discovery={
            "condition": "EvE + GPT-6 Luna + max reasoning + G0 initial language + language evolution enabled",
            "discovery_seeds": [1101, 1202, 1303, 1404, 1505],
            "fresh_search_seeds": [101, 202, 303, 404, 505],
            "initial_programs_path": "V4_INITIAL_PROGRAMS.json",
            "initial_program_count": 20,
            "initial_programs_sha256": initial_digest,
            "candidate_budget": {
                "unique_successful_expanded_asts": 200,
                "common_initial_ast_count": 20,
                "adaptive_unique_evaluations": 180,
                "adaptive_proposal_attempt_cap": 540,
                "exact_expanded_ast_repeats_advance_unique_budget": False,
                "count_invalid_repeat_timeout_and_failure_as_attempt": True,
                "no_replacement_proposals": True,
            },
            "token_budget": {
                "reported_input_plus_output_tokens": 500000000,
                "cached_input_counted_once": True,
                "seed_evaluations_model_tokens": 0,
                "all_conditions_same_cap": True,
            },
            "runtime_limits": {
                "native_turns_per_proposal": 80,
                "proposal_timeout_seconds": 3600,
                "boundary_repair_attempts": 0,
                "evaluator_timeout_seconds": 1800,
                "workers": 1,
                "parallel_workers": 1,
                "read_only_solver_examples": 32,
            },
            "rng": {
                "optimizer_random_seed": "discovery seed + 1",
                "solver_population_random_seed": "discovery seed + 2",
                "workspace_random_seed": "discovery seed + 3",
                "model_evaluation_seed": 42,
            },
            "resume_and_failure_rules": {
                "persist_each_completed_proposal_before_next_launch": True,
                "resume_same_run_root_and_restore_rng_state": True,
                "interrupted_workspace_is_archived_and_counted_as_consumed_attempt": True,
                "terminal_failure_or_timeout_consumes_attempt": True,
                "counter_reset_or_proposal_replacement": False,
                "protected_boundary_or_official_test_violation": "terminate_run_immediately",
                "attempt_or_token_cap_or_terminal_infrastructure_failure": "mark_incomplete_and_preserve_trajectory",
                "no_extrapolation_from_incomplete_run": True,
            },
            "discovery_objective": {
                "stage_one_fitness_unchanged": True,
                "language_complexity": "invented macros in complete language inventory",
                "penalty_coefficient": 0.0005,
            },
            "language_selection": {
                "candidate_must_be_successfully_evaluated": True,
                "candidate_must_contain_at_least_one_invented_macro": True,
                "maximize": "discovery_fitness",
                "tie_breakers": [
                    "fewer_macros",
                    "lexicographically_smaller_canonical_language_sha256",
                    "lexicographically_smaller_canonical_expanded_program_sha256",
                    "smaller_discovery_seed",
                ],
                "eligible_table_and_selection_calculation_required": True,
                "use_fresh_search_or_official_test_evidence": False,
            },
            "candidate_auc": {
                "best_so_far_score": "unchanged_stage_one_fitness",
                "start_unique_evaluation": 20,
                "end_unique_evaluation": 200,
                "integration": "left_endpoint_step",
                "normalizer": 180,
                "formula": "sum(b(n) for n in range(20, 200)) / 180",
            },
            "primary_contrast_and_statistics": {
                "per_seed_contrast": "mean of G*-G0 candidate AUC in fixed and EvE optimizer conditions",
                "exact_one_sided_sign_flip_assignments": 32,
                "sign_flip_statistic": "mean of five paired seed differences; include equal statistics in tail",
                "bootstrap_resamples": 10000,
                "bootstrap_seed": 4204,
                "bootstrap_confidence_level": 0.95,
                "bootstrap_interval": "two-sided percentile interval on paired seed records",
            },
            "numeric_support_criteria": {
                "mean_primary_auc_gain_minimum": 0.002,
                "one_sided_exact_p_maximum": 0.05,
                "bootstrap_lower_bound_above_zero": True,
                "positive_mean_gain_each_optimizer": True,
                "positive_seed_differences_minimum": 4,
                "independent_fresh_search_seeds_with_macro_reuse_minimum": 2,
                "protected_boundary_or_official_test_violations_maximum": 0,
            },
            "official_test_access": False,
            "runs_started": False,
        },
        source_pins=_source_pins(),
    )
    pending_decisions = protocol.get("pending_preregistration_decisions")
    if (
        not isinstance(pending_decisions, list)
        or len(pending_decisions) != len(_PENDING_PREREGISTRATION_DECISIONS)
        or not all(isinstance(item, str) for item in pending_decisions)
        or set(pending_decisions) != _PENDING_PREREGISTRATION_DECISIONS
    ):
        raise ValueError("historical preregistration decision inventory changed; resolve it explicitly")
    protocol["pending_preregistration_decisions"] = []
    if supersedes is not None:
        protocol["supersedes"] = _supersedes_record(supersedes)
    protocol["primary_design"].update(
        {
            "source_pins_sha256": hashlib.sha256(
                json.dumps(protocol["source_pins"], sort_keys=True, separators=(",", ":")).encode()
            ).hexdigest(),
        }
    )
    output = Path(destination)
    if not output.is_absolute():
        output = ROOT / output
    output_bytes = (
        json.dumps(protocol, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False)
        + "\n"
    ).encode("utf-8")
    digest = hashlib.sha256(output_bytes).hexdigest()
    sidecar_bytes = f"{digest}  {output.name}\n".encode()
    _write_exclusive(output, output_bytes)
    _write_exclusive(output.with_suffix(output.suffix + ".sha256"), sidecar_bytes)
    return {"path": str(output), "sha256": digest, "source_count": len(protocol["source_pins"])}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "results/v4/primary_protocol.json",
    )
    parser.add_argument("--version", default="v4-primary-1")
    parser.add_argument("--supersedes", type=Path)
    args = parser.parse_args()
    print(
        json.dumps(
            finalize_protocol(args.output, version=args.version, supersedes=args.supersedes),
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
