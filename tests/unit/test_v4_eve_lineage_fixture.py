import json
from pathlib import Path

from experiments.v4_eve_lineage_fixture import (
    _apply_primary_fixture_config,
    _language_only_preflight_passed,
    _primary_fixture_immutable_files,
    _render_lineage_fixture_prompt,
    _write_fixture_manifest,
)


def test_fixture_manifest_hashes_all_evidence_files(tmp_path):
    (tmp_path / "native_transcripts").mkdir()
    (tmp_path / "native_transcripts/invocation-01.jsonl").write_text("{}\n")
    (tmp_path / "result.json").write_text('{"status": "passed"}\n')

    manifest_record = _write_fixture_manifest(
        tmp_path,
        run_id="fixture-01",
        status="passed",
    )
    manifest = json.loads((tmp_path / "manifest.json").read_text())
    sidecar = (tmp_path / "manifest.sha256").read_text().split()[0]

    assert manifest_record["sha256"] == sidecar
    assert manifest["status"] == "passed"
    assert set(manifest["files"]) == {
        "native_transcripts/invocation-01.jsonl",
        "result.json",
    }


def test_language_only_preflight_requires_language_write_and_program_denial():
    assert _language_only_preflight_passed(
        {
            "passed": True,
            "checks": {
                "solver/candidate/language.json": True,
                "solver/candidate/program.json": True,
            },
        },
        0,
    )


def test_language_only_preflight_rejects_empty_checks():
    assert not _language_only_preflight_passed(
        {"passed": True, "checks": {}},
        0,
    )


def test_lineage_fixture_prompt_only_requests_the_selected_parent_handoff():
    prompt = _render_lineage_fixture_prompt(
        prefill_id="selected-prefill",
        language_hash="a" * 64,
    )

    assert "solver_examples/selected-prefill/logs/evaluate/lineage_state.json" in prompt
    assert "parent_language_hash" in prompt
    assert "`language_hash` value `" + "a" * 64 in prompt
    assert "Keep `solver/candidate/program.json` byte-for-byte identical" in prompt
    assert "Do not read data, run a model evaluator, change the program" in prompt
    assert "solver_examples/selected-prefill/" in prompt


def test_primary_fixture_config_keeps_the_pinned_worker_overlay():
    config = {
        "application": {"path": "old-task"},
        "optimizer": {"workers": {"items": [{"immutable": "pinned-overlay"}]}},
    }

    _apply_primary_fixture_config(
        config,
        task_root=Path("/primary/task"),
    )

    assert config["application"]["path"] == "/primary/task"
    assert (
        config["optimizer"]["workers"]["items"][0]["immutable"]
        == "pinned-overlay"
    )


def test_primary_fixture_replaces_checker_but_preserves_pinned_guidance(tmp_path):
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    (bundle / "manifest.json").write_text('{"version":2}')
    (bundle / "run_check.sh").write_text("#!/bin/sh\nexit 0\n")
    reference = tmp_path / "g0_reference.json"
    reference.write_text('{"primitive":"g0"}')

    immutable = _primary_fixture_immutable_files(
        {
            "README.md": "pinned task template",
            "AGENTS.md": "pinned boundary guidance",
            "structural_check/manifest.json": '{"version":1}',
            "structural_check/old.py": "stale checker",
        },
        checker_bundle_path=bundle,
        g0_reference_path=reference,
    )

    assert immutable["README.md"] == "pinned task template"
    assert immutable["AGENTS.md"] == "pinned boundary guidance"
    assert immutable["structural_check/manifest.json"] == '{"version":2}'
    assert immutable["structural_check/run_check.sh"] == "#!/bin/sh\nexit 0\n"
    assert "structural_check/old.py" not in immutable
    assert immutable["g0_reference.json"] == '{"primitive":"g0"}'
