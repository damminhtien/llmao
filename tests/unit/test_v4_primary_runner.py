"""The Phase 12 runner must implement its finalized protocol exactly."""

from __future__ import annotations

import copy
import importlib.util
import json
import sys
from pathlib import Path

import pytest

from experiments.v4_run_primary_discovery import (
    _prepare_primary_worker_immutable,
    _verified_protocol_path,
    _verify_protocol_matches_runner,
)
from experiments.v4_run_primary_discovery import (
    _run as run_subprocess,
)

_EVALUATOR_PATH = (
    Path(__file__).resolve().parents[2] / "configs/v4/phase12_primary/evaluate.py"
)
_EVALUATOR_SPEC = importlib.util.spec_from_file_location(
    "phase12_primary_evaluate", _EVALUATOR_PATH
)
assert _EVALUATOR_SPEC is not None and _EVALUATOR_SPEC.loader is not None
_EVALUATOR_MODULE = importlib.util.module_from_spec(_EVALUATOR_SPEC)
_EVALUATOR_SPEC.loader.exec_module(_EVALUATOR_MODULE)
_configured_python = _EVALUATOR_MODULE._configured_python


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


def test_runner_subprocess_helper_remains_callable(tmp_path):
    result = run_subprocess(
        [sys.executable, "-c", "print('primary-runner-helper')"],
        cwd=tmp_path,
    )

    assert result.returncode == 0
    assert result.stdout == "primary-runner-helper\n"


def test_runner_uses_the_contract_validated_absolute_protocol_path(tmp_path):
    protocol = tmp_path / "primary_protocol.json"
    protocol.write_text("{}\n", encoding="utf-8")

    resolved = _verified_protocol_path(
        {
            "protocol_path": "results/v4/primary_protocol.json",
            "verified_protocol_path": str(protocol),
        }
    )

    assert resolved == protocol.resolve()


def test_runner_rejects_unresolved_relative_protocol_paths():
    with pytest.raises(ValueError, match="must be absolute"):
        _verified_protocol_path({"verified_protocol_path": "results/v4/protocol.json"})


def test_evaluator_preserves_pinned_venv_launcher_symlink(tmp_path, monkeypatch) -> None:
    target = tmp_path / "python"
    target.write_text("#!/bin/sh\n", encoding="utf-8")
    target.chmod(0o755)
    launcher = tmp_path / ".venv/bin/python"
    launcher.parent.mkdir(parents=True)
    launcher.symlink_to(target)
    monkeypatch.setenv("LLMAO_PYTHON", str(launcher))

    configured_python = _configured_python()

    assert configured_python == launcher
    assert configured_python != target
    assert configured_python.resolve() == target


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


def test_primary_worker_overlay_renders_task_guidance_and_checker(tmp_path) -> None:
    task_root = tmp_path / "task"
    checker_bundle = tmp_path / "checker"
    run_root = tmp_path / "run"
    task_root.mkdir()
    checker_bundle.mkdir()
    (task_root / "README.md").write_text("{solver_examples_block}\n", encoding="utf-8")
    (task_root / "AGENTS.md").write_text("candidate-only\n", encoding="utf-8")
    (task_root / "g0_reference.json").write_text('{"version": 1}\n', encoding="utf-8")
    (checker_bundle / "manifest.json").write_text('{"version": 2}\n', encoding="utf-8")
    (checker_bundle / "run_check.sh").write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    run_root.mkdir()

    overlay = _prepare_primary_worker_immutable(
        run_root=run_root,
        checker_bundle=checker_bundle,
        protocol_sha256="a" * 64,
        resume=False,
        task_root=task_root,
    )

    assert (overlay / "README.md").read_text(encoding="utf-8") == "{solver_examples_block}\n"
    assert (overlay / "AGENTS.md").read_text(encoding="utf-8") == "candidate-only\n"
    assert (overlay / "g0_reference.json").read_text(encoding="utf-8") == '{"version": 1}\n'
    assert (overlay / "structural_check/manifest.json").is_file()
    manifest = json.loads((run_root / "worker_immutable_manifest.json").read_text())
    assert set(manifest["files"]) == {
        "README.md",
        "AGENTS.md",
        "g0_reference.json",
        "structural_check/manifest.json",
        "structural_check/run_check.sh",
    }
    assert _prepare_primary_worker_immutable(
        run_root=run_root,
        checker_bundle=checker_bundle,
        protocol_sha256="a" * 64,
        resume=True,
        task_root=task_root,
    ) == overlay
