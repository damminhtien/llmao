"""Versioned primary-protocol amendments preserve their supersession chain."""

import hashlib
import json

import pytest

from experiments.v4_finalize_primary_protocol import _supersedes_record


def test_supersedes_record_verifies_and_names_the_prior_protocol(tmp_path):
    prior = tmp_path / "results/v4/primary_protocol_v1.json"
    prior.parent.mkdir(parents=True)
    raw = json.dumps(
        {"status": "finalized_primary", "version": "v4-primary-1"}
    ).encode()
    prior.write_bytes(raw)
    digest = hashlib.sha256(raw).hexdigest()
    prior.with_suffix(".json.sha256").write_text(f"{digest}  {prior.name}\n")

    record = _supersedes_record(prior, root=tmp_path)

    assert record == {
        "path": "results/v4/primary_protocol_v1.json",
        "version": "v4-primary-1",
        "sha256": digest,
    }


def test_supersedes_record_rejects_a_changed_prior_protocol(tmp_path):
    prior = tmp_path / "primary_protocol.json"
    prior.write_text('{"status":"finalized_primary","version":"v4-primary-1"}')
    prior.with_suffix(".json.sha256").write_text(f"{'0' * 64}  {prior.name}\n")

    with pytest.raises(ValueError, match="digest does not verify"):
        _supersedes_record(prior, root=tmp_path)


def test_supersedes_record_rejects_protocol_outside_repository(tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    outside = tmp_path / "outside.json"
    raw = b'{"status":"finalized_primary","version":"v4-primary-1"}'
    outside.write_bytes(raw)
    outside.with_suffix(".json.sha256").write_text(
        f"{hashlib.sha256(raw).hexdigest()}  {outside.name}\n"
    )

    with pytest.raises(ValueError, match="inside the repository"):
        _supersedes_record(outside, root=root)
