"""Capture complete tmux launch failures without changing EvE's engine."""

from __future__ import annotations

import fcntl
import importlib
import json
import subprocess
from pathlib import Path
from types import ModuleType
from typing import Any


def _text(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


def failure_record(
    error: subprocess.CalledProcessError,
    *,
    cwd: str | Path | None = None,
    pane_id: str | None = None,
) -> dict[str, Any]:
    """Return the command and captured output carried by CalledProcessError."""
    return {
        "schema_version": 1,
        "event": "tmux_command_failed",
        "command": error.cmd,
        "return_code": error.returncode,
        "stdout": _text(error.stdout),
        "stderr": _text(error.stderr),
        "cwd": str(cwd) if cwd is not None else None,
        "pane_id": pane_id,
    }


def append_failure(
    trace_path: Path,
    error: subprocess.CalledProcessError,
    *,
    cwd: str | Path | None = None,
    pane_id: str | None = None,
) -> dict[str, Any]:
    """Append one complete failure event to a locked JSONL trace."""
    record = failure_record(error, cwd=cwd, pane_id=pane_id)
    payload = (json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n").encode(
        "utf-8"
    )
    trace_path = Path(trace_path)
    trace_path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = trace_path.open("ab")
    try:
        fcntl.flock(descriptor.fileno(), fcntl.LOCK_EX)
        descriptor.write(payload)
        descriptor.flush()
    finally:
        fcntl.flock(descriptor.fileno(), fcntl.LOCK_UN)
        descriptor.close()
    return record


def install_tmux_failure_capture(
    trace_path: Path,
    *,
    driver_module: ModuleType | None = None,
) -> None:
    """Record launch exceptions raised by EvE's native Codex tmux driver."""
    module = driver_module or importlib.import_module(
        "scaling_evolve.providers.agent.drivers.codex_tmux"
    )
    original = module.launch_in_pane
    if getattr(original, "__v4_failure_capture__", False):
        raise RuntimeError("tmux failure capture is already installed")

    def traced_launch_in_pane(*args: object, **kwargs: object) -> object:
        try:
            return original(*args, **kwargs)
        except subprocess.CalledProcessError as exc:
            append_failure(
                trace_path,
                exc,
                cwd=kwargs.get("cwd") if isinstance(kwargs.get("cwd"), (str, Path)) else None,
                pane_id=(
                    str(kwargs["pane_id"]) if kwargs.get("pane_id") is not None else None
                ),
            )
            raise

    traced_launch_in_pane.__v4_failure_capture__ = True  # type: ignore[attr-defined]
    traced_launch_in_pane.__wrapped__ = original  # type: ignore[attr-defined]
    module.launch_in_pane = traced_launch_in_pane
