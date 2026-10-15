"""The follow-up supervisor checks pinned sources and protected boundaries."""

import hashlib
import json
import runpy
from pathlib import Path

MODULE = runpy.run_path(
    str(Path(__file__).resolve().parents[2] / "experiments/v4_launch_followup.py")
)


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
