"""Terminal collection never replaces evidence or archives a live run."""

from __future__ import annotations

import hashlib
import json
import runpy
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
COLLECTOR = runpy.run_path(str(ROOT / "experiments/v4_collect_followup.py"))


@pytest.fixture
def collector(tmp_path, monkeypatch):
    namespace = COLLECTOR["collect"].__globals__
    monkeypatch.setitem(namespace, "ROOT", tmp_path)
    metadata = tmp_path / "metadata"
    metadata.mkdir()
    monkeypatch.setitem(namespace, "METADATA", metadata)
    return namespace, tmp_path, metadata


def test_collection_rejects_live_run_before_writing(collector) -> None:
    namespace, root, metadata = collector
    contract = root / "V4_FOLLOWUP_REPAIR_CONTRACT_20261015-04.json"
    contract.write_text("{}")
    digest = hashlib.sha256(contract.read_bytes()).hexdigest()
    contract.with_suffix(".sha256").write_text(digest + "  contract.json\n")
    (metadata / "execution.json").write_text(
        json.dumps({"status": "running", "contract_sha256": digest})
    )
    destination = root / "archive"
    with pytest.raises(ValueError, match="normally exited"):
        namespace["collect"](destination)
    assert not destination.exists()


def test_collection_rejects_existing_and_escaping_paths(collector) -> None:
    namespace, root, _ = collector
    destination = root / "archive"
    destination.mkdir()
    for path in (destination, root / ".." / "outside"):
        with pytest.raises(ValueError, match="new directory inside"):
            namespace["collect"](path)


def test_copy_preserves_bytes_and_rejects_replacement_or_symlink(collector) -> None:
    namespace, root, _ = collector
    source = root / "source.json"
    source.write_bytes(b'{"original": true}\n')
    target = root / "archive/source.json"
    record = namespace["_copy"](source, target)
    assert target.read_bytes() == source.read_bytes()
    assert record["sha256"] == hashlib.sha256(source.read_bytes()).hexdigest()
    with pytest.raises(FileExistsError):
        namespace["_copy"](source, target)
    linked = root / "linked.json"
    linked.symlink_to(source)
    with pytest.raises(ValueError, match="regular file"):
        namespace["_copy"](linked, root / "other.json")


def test_collection_verifies_the_execution_tmux_failure_trace(collector) -> None:
    namespace, root, _ = collector
    trace = root / "tmux_failures.jsonl"
    failure = {
        "command": ["tmux", "respawn-pane"],
        "return_code": 37,
        "stdout": "out\n",
        "stderr": "err\n",
        "cwd": str(root),
        "pane_id": "%1",
    }
    trace.write_text(json.dumps(failure) + "\n")
    supervisor = runpy.run_path(str(ROOT / "experiments/v4_launch_followup.py"))
    summary = supervisor["_tmux_failure_trace_summary"](trace)
    contract = {
        "schema_version": 5,
        "launch": {"tmux_failure_trace": str(trace)},
    }

    path, verified = namespace["_verify_tmux_failure_trace"](
        contract,
        {"tmux_failure_trace": summary},
        supervisor,
    )

    assert path == trace
    assert verified == summary

    with pytest.raises(ValueError, match="differs from captured tmux failures"):
        namespace["_verify_tmux_failure_trace"](
            contract,
            {"tmux_failure_trace": {**summary, "record_count": 0}},
            supervisor,
        )
