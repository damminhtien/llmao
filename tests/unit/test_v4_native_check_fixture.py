"""Native V4 fixture postconditions require direct worker evidence."""

from __future__ import annotations

import pytest

from experiments.v4_native_check_fixture import _verify_native_outputs


def test_native_fixture_requires_all_structural_and_sandbox_checks() -> None:
    result = _verify_native_outputs(
        [
            '{"status":"valid","feature_dimension":6}',
            "VALID_EXIT_STATUS=0",
            '{"status":"invalid","reason":"unknown operation"}',
            "INVALID_EXIT_STATUS=1",
            "SLASH_TMP_WRITE_DENIED",
            "TMPDIR_WRITE_DENIED",
            "OUTSIDE_READ_DENIED",
        ],
        slash_tmp_probe_exists=False,
        tmpdir_probe_exists=False,
        outside_read_probe_unchanged=True,
        outside_read_probe_cleaned=True,
        candidate_contents_unchanged=True,
        changed_paths=[],
        git_status="",
    )

    assert result["passed"] is True


def test_native_fixture_rejects_missing_denials_or_workspace_changes() -> None:
    result = _verify_native_outputs(
        [
            '{"status":"valid"}',
            "VALID_EXIT_STATUS=0",
            '{"status":"invalid"}',
            "INVALID_EXIT_STATUS=1",
            "SLASH_TMP_WRITE_ALLOWED_CLEANED",
            "TMPDIR_WRITE_DENIED",
            "OUTSIDE_READ_ALLOWED",
        ],
        slash_tmp_probe_exists=False,
        tmpdir_probe_exists=False,
        outside_read_probe_unchanged=False,
        outside_read_probe_cleaned=False,
        candidate_contents_unchanged=False,
        changed_paths=["candidate/program.json"],
        git_status="M candidate/program.json",
    )

    assert result["passed"] is False
    checks = result["checks"]
    assert checks["no_probe_write_allowed"] is False
    assert checks["candidate_files_unchanged"] is False
    assert checks["no_workspace_paths_changed"] is False


def test_failed_preflight_prevents_worker_creation(tmp_path, monkeypatch):
    from experiments import v4_native_check_fixture as fixture
    from experiments import v4_sandbox_preflight as preflight

    monkeypatch.setattr(fixture, "FIXTURE_CACHE", tmp_path)
    monkeypatch.setattr(fixture, "EVIDENCE_ROOT", tmp_path)
    monkeypatch.setenv("TMPDIR", str(tmp_path))
    monkeypatch.setattr(fixture, "_build_workspace", lambda *_: {})
    monkeypatch.setattr(preflight, "run_preflight", lambda *_: {"passed": False})

    def unexpected_launch(*args, **kwargs):
        pytest.fail("a failed preflight must never create a tmux worker")

    monkeypatch.setattr(fixture.subprocess, "check_output", unexpected_launch)

    with pytest.raises(RuntimeError, match="native worker was not started"):
        fixture.run_fixture(
            "blocked", tmp_path / "workspace", tmp_path / "evidence"
        )
