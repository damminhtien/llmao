"""Complete tmux subprocess evidence is retained by the external runner hook."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from types import ModuleType

import pytest

from experiments.v4_tmux_failure_capture import (
    append_failure,
    install_tmux_failure_capture,
)


def test_append_failure_preserves_command_and_text_streams(tmp_path: Path) -> None:
    trace_path = tmp_path / "tmux.jsonl"
    error = subprocess.CalledProcessError(
        17,
        ["tmux", "respawn-pane", "-t", "%8"],
        output=b"tmux stdout\n",
        stderr=b"can't find pane: %8\n",
    )

    record = append_failure(trace_path, error, cwd=tmp_path, pane_id="%8")

    assert record["command"] == error.cmd
    assert record["return_code"] == 17
    assert record["stdout"] == "tmux stdout\n"
    assert record["stderr"] == "can't find pane: %8\n"
    assert record["cwd"] == str(tmp_path)
    assert record["pane_id"] == "%8"
    assert json.loads(trace_path.read_text(encoding="utf-8")) == record


def test_installed_hook_traces_then_reraises_the_original_error(
    tmp_path: Path,
) -> None:
    expected = subprocess.CalledProcessError(
        1,
        ["tmux", "respawn-pane", "-k", "-t", "%9"],
        output="stdout details",
        stderr="stderr details",
    )
    module = ModuleType("fake_codex_tmux")

    def fail_launch(**_kwargs: object) -> None:
        raise expected

    module.launch_in_pane = fail_launch  # type: ignore[attr-defined]
    trace_path = tmp_path / "trace.jsonl"
    install_tmux_failure_capture(trace_path, driver_module=module)

    with pytest.raises(subprocess.CalledProcessError) as raised:
        module.launch_in_pane(pane_id="%9", cwd=tmp_path)  # type: ignore[attr-defined]

    assert raised.value is expected
    record = json.loads(trace_path.read_text(encoding="utf-8"))
    assert record["command"] == expected.cmd
    assert record["return_code"] == 1
    assert record["stdout"] == "stdout details"
    assert record["stderr"] == "stderr details"
    assert record["cwd"] == str(tmp_path)
    assert record["pane_id"] == "%9"


def test_hook_rejects_double_installation(tmp_path: Path) -> None:
    module = ModuleType("fake_codex_tmux")
    module.launch_in_pane = lambda **_kwargs: None  # type: ignore[attr-defined]
    install_tmux_failure_capture(tmp_path / "trace.jsonl", driver_module=module)

    with pytest.raises(RuntimeError, match="already installed"):
        install_tmux_failure_capture(tmp_path / "trace.jsonl", driver_module=module)
