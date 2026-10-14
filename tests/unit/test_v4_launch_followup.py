"""The follow-up supervisor checks ordinary Plus usage and immutable sources."""

import hashlib
import json
import runpy
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

MODULE = runpy.run_path(
    str(Path(__file__).resolve().parents[2] / "experiments/v4_launch_followup.py")
)


def _usage() -> dict:
    return {
        "checked_at_utc": datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC"),
        "plan": "plus",
        "ordinary_usage_allowed": True,
        "five_hour_window_used_percent": 39,
        "weekly_window_used_percent": 23,
    }


@pytest.mark.parametrize(
    "key,value",
    [
        ("plan", "pro"),
        ("ordinary_usage_allowed", False),
        ("ordinary_usage_allowed", 1),
        ("five_hour_window_used_percent", 100),
        ("weekly_window_used_percent", None),
    ],
)
def test_usage_rejects_unavailable_or_wrong_plan(key, value) -> None:
    usage = _usage()
    usage[key] = value
    with pytest.raises(ValueError):
        MODULE["_validate_usage"](usage)


def test_usage_requires_a_fresh_plus_snapshot() -> None:
    usage = _usage()
    MODULE["_validate_usage"](usage)
    usage["checked_at_utc"] = (datetime.now(UTC) - timedelta(minutes=11)).strftime(
        "%Y-%m-%d %H:%M:%S UTC"
    )
    with pytest.raises(ValueError, match="ten minutes"):
        MODULE["_validate_usage"](usage)


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
