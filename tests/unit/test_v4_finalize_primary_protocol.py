"""Versioned primary-protocol amendments preserve their supersession chain."""

import hashlib
import json

import pytest

from experiments.v4_finalize_primary_protocol import (
    _supersedes_record,
    finalize_protocol,
)

_PENDING_DECISIONS = [
    "evaluator_compiler_snapshot_and_worker_permissions_context_policy",
    "candidate_and_token_budgets_seeds_attempt_cap_timeouts_incomplete_run_policy",
    "common_initial_program_manifest",
    "language_complexity_penalty_definition_and_coefficient",
    "discovery_only_language_selection_rule_and_tie_breakers",
    "AUC_bounds_normalization_primary_contrast_statistics_and_numeric_support_criteria",
]


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


def test_finalized_protocol_clears_resolved_phase_zero_decisions(tmp_path, monkeypatch):
    import experiments.v4_finalize_primary_protocol as finalizer

    monkeypatch.setattr(finalizer, "ROOT", tmp_path)
    monkeypatch.setattr(
        finalizer,
        "_require_clean_commits",
        lambda: ("a" * 40, "b" * 40),
    )
    monkeypatch.setattr(
        finalizer,
        "_source_pins",
        lambda: {
            "V4_PRIMARY_DESIGN.md": "c" * 64,
            "configs/v4/phase12_primary/evaluate.py": "d" * 64,
        },
    )
    historical = tmp_path / "results/v4/protocol.json"
    historical.parent.mkdir(parents=True)
    historical_raw = json.dumps(
        {
            "candidate_feedback": {"status": "draft"},
            "evaluator_basis": {"split_fingerprints_sha256": "e" * 64},
            "pending_preregistration_decisions": _PENDING_DECISIONS,
        }
    ).encode()
    historical.write_bytes(historical_raw)
    historical.with_suffix(".json.sha256").write_text(
        f"{hashlib.sha256(historical_raw).hexdigest()}  protocol.json\n"
    )
    (historical.parent / "protocol.sha256").write_text(
        f"{hashlib.sha256(historical_raw).hexdigest()}  protocol.json\n"
    )
    initial = tmp_path / "V4_INITIAL_PROGRAMS.json"
    initial.write_text("{}\n", encoding="utf-8")
    (tmp_path / "V4_INITIAL_PROGRAMS.sha256").write_text(
        f"{hashlib.sha256(initial.read_bytes()).hexdigest()}  V4_INITIAL_PROGRAMS.json\n"
    )

    destination = tmp_path / "results/v4/primary_protocol_v11.json"
    result = finalize_protocol(destination, version="v4-primary-11")
    finalized = json.loads(destination.read_text(encoding="utf-8"))

    assert result["sha256"] == hashlib.sha256(destination.read_bytes()).hexdigest()
    assert finalized["pending_preregistration_decisions"] == []
    discovery = finalized["primary_discovery"]
    assert discovery["discovery_seeds"] == [1101, 1202, 1303, 1404, 1505]
    assert discovery["initial_programs_sha256"] == hashlib.sha256(initial.read_bytes()).hexdigest()
    assert discovery["language_selection"]["candidate_must_be_successfully_evaluated"] is True
    assert discovery["candidate_auc"]["normalizer"] == 180
    assert discovery["primary_contrast_and_statistics"]["exact_one_sided_sign_flip_assignments"] == 32
    fresh = finalized["primary_fresh_search"]
    assert fresh["conditions"] == [
        {"language": "G0", "optimizer": "fixed_iterative_codex"},
        {"language": "G*", "optimizer": "fixed_iterative_codex"},
        {"language": "G0", "optimizer": "EvE"},
        {"language": "G*", "optimizer": "EvE"},
    ]
    assert fresh["run_count"] == 20
    assert fresh["total_primary_search_runs"] == 25
    assert finalized["storage_layout"]["version"] == 2
    assert finalized["storage_layout"]["candidate_worker_can_read_mnist_cache"] is False
