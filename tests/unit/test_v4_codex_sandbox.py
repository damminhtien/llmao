"""Tests for the V4 Codex wrapper's least-privilege permission profile."""

from __future__ import annotations

import runpy
import tomllib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
WRAPPER = runpy.run_path(str(ROOT / "scripts/codex-v4-sandbox"))


def test_wrapper_removes_only_legacy_workspace_write_flag() -> None:
    args = [
        "--no-alt-screen",
        "-s",
        "workspace-write",
        "-a",
        "never",
        "candidate task",
    ]

    assert WRAPPER["_strip_legacy_sandbox"](args) == [
        "--no-alt-screen",
        "-a",
        "never",
        "candidate task",
    ]


def test_wrapper_rejects_other_sandbox_modes_and_legacy_overrides() -> None:
    with pytest.raises(ValueError, match="only workspace-write"):
        WRAPPER["_strip_legacy_sandbox"](["--sandbox", "danger-full-access"])
    with pytest.raises(ValueError, match="legacy sandbox overrides"):
        WRAPPER["_strip_legacy_sandbox"](
            ["-c", "sandbox_workspace_write.network_access=false"]
        )


def test_wrapper_installs_and_preserves_workspace_only_profile(tmp_path: Path) -> None:
    code_home = tmp_path / ".codex-driver-home" / ".codex"
    code_home.mkdir(parents=True)
    config_path = code_home / "config.toml"
    config_path.write_text(
        'model = "gpt-6-luna"\n\n[features]\nhooks = true\n',
        encoding="utf-8",
    )

    WRAPPER["_install_profile"](config_path)
    first_write = config_path.read_bytes()
    config = tomllib.loads(first_write.decode("utf-8"))
    profile = config["permissions"]["llmao-v4-workspace-only"]

    assert config["default_permissions"] == "llmao-v4-workspace-only"
    assert profile["extends"] == ":workspace"
    assert profile["filesystem"][":root"] == "deny"
    assert profile["filesystem"][":minimal"] == "read"
    assert profile["filesystem"][":tmpdir"] == "deny"
    assert profile["filesystem"][":slash_tmp"] == "deny"
    filesystem_reads = {
        path: access
        for path, access in profile["filesystem"].items()
        if path
        not in {":root", ":minimal", ":tmpdir", ":slash_tmp", ":workspace_roots"}
    }
    assert filesystem_reads == {
        str((ROOT / ".venv").resolve()): "read",
        str((ROOT / ".venv/bin/python").resolve().parent.parent): "read",
    }
    assert profile["filesystem"][":workspace_roots"] == {
        ".": "read",
        "candidate/language.json": "write",
        "candidate/program.json": "write",
        "solver/candidate/language.json": "write",
        "solver/candidate/program.json": "write",
    }
    assert profile["network"]["enabled"] is False
    assert config["features"]["hooks"] is True

    WRAPPER["_install_profile"](config_path)

    assert config_path.read_bytes() == first_write


def test_wrapper_rejects_a_mixed_legacy_sandbox_config(tmp_path: Path) -> None:
    code_home = tmp_path / ".codex-driver-home" / ".codex"
    code_home.mkdir(parents=True)
    config_path = code_home / "config.toml"
    config_path.write_text('sandbox_mode = "workspace-write"\n', encoding="utf-8")

    with pytest.raises(ValueError, match="cannot be combined"):
        WRAPPER["_install_profile"](config_path)


@pytest.mark.parametrize(
    "args",
    [
        ["--yolo"],
        ["-pescape"],
        ["-Pescape"],
        ["-adanger"],
        ["--dangerously-bypass-approvals-and-sandbox"],
        ["--config=sandbox_mode=read-only"],
        ["--config", "default_permissions=other"],
        ["-cpermissions.escape.network.enabled=true"],
        ["--add-dir=/tmp"],
        ["--profile=other"],
        ["--enable", "hooks"],
        ["-a", "on-request"],
    ],
)
def test_wrapper_rejects_policy_escape_arguments(args):
    with pytest.raises(ValueError):
        WRAPPER["_strip_legacy_sandbox"](args)


def test_wrapper_accepts_actual_eve_driver_overrides():
    args = [
        "-c",
        'model_reasoning_effort="max"',
        "-c",
        'web_search="disabled"',
        "-c",
        "features.multi_agent=false",
    ]
    assert WRAPPER["_strip_legacy_sandbox"](args) == args


def test_wrapper_rejects_legacy_workspace_config(tmp_path):
    (tmp_path / ".git").mkdir()
    config = tmp_path / ".codex/config.toml"
    config.parent.mkdir()
    config.write_text('sandbox_mode="workspace-write"\n')
    with pytest.raises(ValueError, match="workspace config overrides"):
        WRAPPER["_validate_workspace"](tmp_path)
