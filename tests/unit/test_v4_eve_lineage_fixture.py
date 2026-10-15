import json

from experiments.v4_eve_lineage_fixture import (
    _language_only_preflight_passed,
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
