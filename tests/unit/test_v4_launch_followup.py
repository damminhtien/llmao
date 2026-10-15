"""The follow-up supervisor checks pinned sources and protected boundaries."""

import hashlib
import json
import runpy
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
MODULE = runpy.run_path(
    str(ROOT / "experiments/v4_launch_followup.py")
)


def test_runner_command_uses_external_failure_capture_bootstrap(tmp_path):
    command = MODULE["_eve_runner_command"](tmp_path, ["loop.max_iterations=10"])

    assert command[:3] == [
        str(tmp_path / ".venv/bin/python"),
        "-u",
        str(ROOT / "experiments/v4_eve_runner.py"),
    ]
    assert command[-1] == "loop.max_iterations=10"


def test_default_contract_targets_the_next_frozen_repair():
    assert MODULE["DEFAULT_CONTRACT"].name == "V4_FOLLOWUP_REPAIR_CONTRACT_20261015-04.json"


def test_latest_failed_repair_contract_and_archive_remain_pinned():
    evidence = MODULE["_verify_latest_failed_repair_artifacts"]()

    assert evidence["latest_failed_repair_contract_sha256"] == "7689417fc9295bb4c49565f92240f27aad890bdff853234b34a8f4b60dddb60e"
    assert evidence["latest_failed_repair_archive_manifest_sha256"] == "cd059044554c7a83a26499e759c7ddcf9026d54e886c49a104c1f2f7421b9f08"
    assert evidence["latest_failed_repair_archive_records_verified"] == 208
    assert evidence["latest_failed_repair_wrapper_sha256"] == "c130fefd1527414ff3f0989a3ebe491d2a2e268b558ddb256716734fef01982a"


def test_pre_worker_hydra_startup_failure_is_preserved():
    evidence = MODULE["_verify_failed_startup_contract_03"]()

    assert evidence["failed_startup_contract_20261015_03_sha256"] == "84df233e5cfc16b8fc8223fd609c0a7ad8322839184f5a1b6d2074daed2ad465"
    assert len(evidence["failed_startup_execution_record_sha256"]) == 64
    assert len(evidence["failed_startup_console_output_sha256"]) == 64


def test_tmux_failure_trace_summary_preserves_exact_subprocess_details(tmp_path):
    path = tmp_path / "tmux_failures.jsonl"
    failure = {
        "command": ["tmux", "respawn-pane", "-t", "%1"],
        "return_code": 37,
        "stdout": "stdout marker\n",
        "stderr": "stderr marker\n",
        "cwd": str(tmp_path),
        "pane_id": "%1",
    }
    path.write_text(json.dumps(failure) + "\n")

    summary = MODULE["_tmux_failure_trace_summary"](path)

    assert summary["exists"] is True
    assert summary["record_count"] == 1
    assert summary["records"] == [failure]
    assert summary["sha256"] == hashlib.sha256(path.read_bytes()).hexdigest()


def test_tmux_failure_trace_summary_rejects_incomplete_records(tmp_path):
    path = tmp_path / "tmux_failures.jsonl"
    path.write_text(json.dumps({"command": ["tmux"]}) + "\n")

    with pytest.raises(ValueError, match="incomplete tmux trace"):
        MODULE["_tmux_failure_trace_summary"](path)


def test_boundary_monitor_waits_for_materialization_then_checks_sources(
    tmp_path,
) -> None:
    workspace = tmp_path / "solver_workspaces/worker"
    bundle = workspace / "structural_check"
    bundle.mkdir(parents=True)
    source = bundle / "check.py"
    source.write_text("pass\n")
    manifest = {
        "files": {
            "check.py": {"sha256": hashlib.sha256(source.read_bytes()).hexdigest()}
        }
    }
    manifest_path = bundle / "manifest.json"
    manifest_path.write_text(json.dumps(manifest))
    digest = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
    seen = set()
    assert MODULE["_boundary_violation"](tmp_path, digest, seen) is None
    assert not seen
    metadata = workspace / ".scaling_evolve/worker.yaml"
    metadata.parent.mkdir()
    metadata.write_text("name: followup\n")
    assert MODULE["_boundary_violation"](tmp_path, digest, seen) is None
    assert seen == {bundle}
    source.write_text("changed\n")
    assert "source" in MODULE["_boundary_violation"](tmp_path, digest, seen)
    source.unlink()
    assert "inventory" in MODULE["_boundary_violation"](tmp_path, digest, seen)
    manifest_path.unlink()
    assert "manifest" in MODULE["_boundary_violation"](tmp_path, digest, seen)


def test_boundary_monitor_stops_on_eve_forbidden_change(tmp_path) -> None:
    marker = tmp_path / "artifacts/solver/forbidden_changes.txt"
    marker.parent.mkdir(parents=True)
    marker.write_text("README.md changed\n")
    assert "forbidden" in MODULE["_boundary_violation"](tmp_path, "0" * 64, set())


def test_seed_monitor_accepts_only_the_pinned_fresh_g0(tmp_path) -> None:
    seed = tmp_path / "evaluation_workspaces/seed_1_seed/solver/candidate"
    seed.mkdir(parents=True)
    language = seed / "language.json"
    program = seed / "program.json"
    language.write_text('{"macros": [], "introduced_macros": []}\n')
    program.write_text('{"op": "image"}\n')
    expected = {
        "seed_files_sha256": {
            "examples/task/candidate/language.json": hashlib.sha256(
                language.read_bytes()
            ).hexdigest(),
            "examples/task/candidate/program.json": hashlib.sha256(
                program.read_bytes()
            ).hexdigest(),
        }
    }
    assert MODULE["_initial_seed_violation"](tmp_path, expected) is None
    program.write_text('{"op": "different"}\n')
    assert "fresh G0" in MODULE["_initial_seed_violation"](tmp_path, expected)
