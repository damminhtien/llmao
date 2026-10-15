"""The Phase 12 runner must implement its finalized protocol exactly."""

from __future__ import annotations

import copy

import pytest

from experiments.v4_run_primary_discovery import _verify_protocol_matches_runner


@pytest.fixture
def protocol() -> dict:
    return {
        "primary_design": {
            "exact_cli_model_identifier": "gpt-6-luna",
            "requested_reasoning_effort": "max",
            "backend": "codex_tmux",
            "official_test_access": False,
        },
        "primary_discovery": {
            "discovery_seeds": [1101, 1202, 1303, 1404, 1505],
            "official_test_access": False,
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
                "reported_input_plus_output_tokens": 500_000_000,
                "cached_input_counted_once": True,
                "seed_evaluations_model_tokens": 0,
            },
            "runtime_limits": {
                "native_turns_per_proposal": 80,
                "proposal_timeout_seconds": 3_600,
                "boundary_repair_attempts": 0,
                "evaluator_timeout_seconds": 1_800,
                "workers": 1,
                "parallel_workers": 1,
                "read_only_solver_examples": 32,
            },
            "discovery_objective": {"penalty_coefficient": 0.0005},
        },
    }


def test_runner_accepts_the_frozen_phase12_settings(protocol: dict) -> None:
    _verify_protocol_matches_runner(protocol, 1101)


@pytest.mark.parametrize(
    ("section", "key", "value"),
    [
        ("candidate_budget", "adaptive_proposal_attempt_cap", 541),
        ("token_budget", "reported_input_plus_output_tokens", 500_000_001),
        ("runtime_limits", "workers", 2),
    ],
)
def test_runner_rejects_protocol_runner_drift(
    protocol: dict, section: str, key: str, value: int
) -> None:
    modified = copy.deepcopy(protocol)
    modified["primary_discovery"][section][key] = value
    with pytest.raises(ValueError, match="differ from the Phase 12 runner"):
        _verify_protocol_matches_runner(modified, 1101)


def test_runner_rejects_non_preregistered_seed(protocol: dict) -> None:
    with pytest.raises(ValueError, match="differ from the Phase 12 runner"):
        _verify_protocol_matches_runner(protocol, 9999)
