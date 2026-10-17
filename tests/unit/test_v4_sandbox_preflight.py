"""Preflight rejects missing evidence and protects existing candidate files."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from experiments import v4_sandbox_preflight as preflight


def make_workspace(tmp_path: Path) -> Path:
    workspace = tmp_path / "results/v4/scratch/workspace"
    (workspace / ".git").mkdir(parents=True)
    (workspace / ".codex").mkdir()
    (workspace / ".codex/config.toml").write_text("")
    (workspace / "candidate").mkdir()
    (workspace / "structural_check").mkdir()
    (workspace / "structural_check/manifest.json").write_text(
        json.dumps(
            {
                "files": {},
                "launcher_python_executable": sys.executable,
            }
        )
    )
    return workspace


@pytest.mark.parametrize("stdout", ["", "{}", '{"checks":{},"passed":true}'])
def test_successful_exit_without_complete_checks_is_failure(
    tmp_path, monkeypatch, stdout
):
    workspace = make_workspace(tmp_path)
    monkeypatch.setenv("TMPDIR", str(tmp_path))
    monkeypatch.setattr(preflight, "ROOT", tmp_path)
    monkeypatch.setattr(
        preflight.subprocess,
        "run",
        lambda *a, **kw: subprocess.CompletedProcess(a[0], 0, stdout, ""),
    )
    monkeypatch.setattr(
        preflight.subprocess, "check_output", lambda *a, **kw: "codex-test"
    )
    evidence = tmp_path / "results/v4/evidence.json"

    result = preflight.run_preflight(workspace, evidence)

    assert result["passed"] is False
    assert result["checks"]["complete_probe_report"] is False
    assert json.loads(evidence.read_text())["passed"] is False
    assert not list(tmp_path.glob("v4-preflight-*-read"))


def test_preflight_never_overwrites_existing_candidates(tmp_path, monkeypatch):
    workspace = make_workspace(tmp_path)
    candidate = workspace / "candidate/program.json"
    candidate.write_text("original candidate")
    monkeypatch.setenv("TMPDIR", str(tmp_path))
    monkeypatch.setattr(preflight, "ROOT", tmp_path)

    result = preflight.run_preflight(
        workspace, tmp_path / "results/v4/evidence.json"
    )
    assert result["passed"] is False
    assert "empty probe paths" in result["error"]
    assert candidate.read_text() == "original candidate"


def test_preflight_probes_repo_local_mnist_cache_read_access(tmp_path, monkeypatch):
    workspace = make_workspace(tmp_path)
    cache = tmp_path / "results/v4/cache/datasets/mnist_784"
    evidence = tmp_path / "results/v4/evidence.json"
    monkeypatch.setattr(preflight, "ROOT", tmp_path)
    monkeypatch.setenv("TMPDIR", str(tmp_path))
    monkeypatch.setattr(
        preflight.subprocess,
        "run",
        lambda *a, **kw: subprocess.CompletedProcess(
            a[0],
            0,
            json.dumps({"passed": True, "checks": {"mnist_cache_read_denied": True}}),
            "",
        ),
    )
    monkeypatch.setattr(
        preflight.subprocess, "check_output", lambda *a, **kw: "codex-test"
    )

    result = preflight.run_preflight(workspace, evidence, mnist_cache_dir=cache)

    assert result["checks"]["mnist_cache_read_denied"] is True
    assert result["passed"] is False  # The mocked response omits the other OS probes.
    assert not list(cache.glob(".v4-worker-read-canary-*"))
