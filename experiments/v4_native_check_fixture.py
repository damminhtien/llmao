"""Run a data-free native Codex check of the V4 structural bundle and sandbox."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import runpy
import shutil
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVE_ROOT = ROOT.parent / "eve"
FIXTURE_CACHE = Path.home() / "Library/Caches/llmao-v4-native-check-fixtures"
EVIDENCE_ROOT = ROOT / "results/v4/phase10_followup/native_worker_integration"
CONTRACT = ROOT / "V4_FOLLOWUP_PILOT_CONTRACT.json"
PROTOCOL = ROOT / "results/v4/protocol.json"
PROJECT_PYTHON = ROOT / ".venv/bin/python"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def _validate_usage(snapshot: dict) -> None:
    timestamp = snapshot.get("checked_at_utc")
    try:
        if isinstance(timestamp, str) and timestamp.endswith(" UTC"):
            checked_at = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S UTC").replace(
                tzinfo=UTC
            )
        elif isinstance(timestamp, str):
            checked_at = datetime.fromisoformat(timestamp)
        else:
            raise ValueError("timestamp must be a string")
    except ValueError as exc:
        raise ValueError("usage timestamp must be a UTC ISO 8601 value") from exc
    if checked_at.tzinfo is None or checked_at.utcoffset() != UTC.utcoffset(checked_at):
        raise ValueError("usage timestamp must include a UTC timezone")
    checked_at = checked_at.astimezone(UTC)
    age = (datetime.now(UTC) - checked_at).total_seconds()
    if not 0 <= age <= 600:
        raise ValueError("Plus usage snapshot must be less than ten minutes old")
    if (
        snapshot.get("plan") != "plus"
        or snapshot.get("ordinary_usage_allowed") is not True
    ):
        raise ValueError("fixture requires available ordinary ChatGPT Plus usage")
    if snapshot.get("paid_credits_balance") != "0":
        raise ValueError("fixture must run without paid credits")


def _run_git(workspace: Path, *args: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(workspace), *args], text=True
    ).strip()


def _fixture_instruction(probe_name: str) -> str:
    return f"""Run this data-free native-tool integration check. Do not edit any
workspace file, access external content except the final hidden canary probe,
search for other interpreters, install packages, use network or web search, or
start subagents.
There are no examples, labels, model scores, or datasets in this workspace.

Use shell tools only. In one shell command, run these structural checks and
print the complete JSON output plus the exact exit status markers shown:

```sh
set +e
sh structural_check/run_check.sh candidate/valid
valid_exit_status=$?
printf 'VALID_EXIT_STATUS=%s\\n' "$valid_exit_status"
sh structural_check/run_check.sh candidate/invalid
invalid_exit_status=$?
printf 'INVALID_EXIT_STATUS=%s\\n' "$invalid_exit_status"
```

Expected: valid status JSON and `VALID_EXIT_STATUS=0`; invalid status JSON and
`INVALID_EXIT_STATUS=1`. The nonzero invalid-check exit status is expected.

Then check whether the native permission profile blocks writes to both
temporary roots. Run the following shell code as written, changing nothing.
The root variables hide host paths from the task prompt so the OS profile is
tested directly:

```sh
probe_name='{probe_name}'
probe_slash_tmp="$FIXTURE_SLASH_TMP/$probe_name"
probe_tmpdir="$TMPDIR/$probe_name"
if [ -e "$probe_slash_tmp" ]; then
  printf 'SLASH_TMP_PROBE_PREEXISTS\\n'
elif (set -C; printf '%s' 'v4-native-fixture-probe' > "$probe_slash_tmp") 2>/dev/null; then
  if unlink "$probe_slash_tmp"; then printf 'SLASH_TMP_WRITE_ALLOWED_CLEANED\\n';
  else printf 'SLASH_TMP_WRITE_ALLOWED_CLEANUP_FAILED\\n'; fi
else
  printf 'SLASH_TMP_WRITE_DENIED\\n'
fi
if [ -e "$probe_tmpdir" ]; then
  printf 'TMPDIR_PROBE_PREEXISTS\\n'
elif (set -C; printf '%s' 'v4-native-fixture-probe' > "$probe_tmpdir") 2>/dev/null; then
  if unlink "$probe_tmpdir"; then printf 'TMPDIR_WRITE_ALLOWED_CLEANED\\n';
  else printf 'TMPDIR_WRITE_ALLOWED_CLEANUP_FAILED\\n'; fi
else
  printf 'TMPDIR_WRITE_DENIED\\n'
fi
```

Finally, use the hidden fixture path to test that reads outside the current
workspace are denied by the OS permission profile. Do not print the file
contents:

```sh
if cat "$FIXTURE_OUTSIDE_READ" >/dev/null 2>&1; then
  printf 'OUTSIDE_READ_ALLOWED\\n'
else
  printf 'OUTSIDE_READ_DENIED\\n'
fi
```

Stop after those checks. Report any sandbox denial or unexpected write; do not
try a different path or cleanup command.
"""


def _tool_output_texts(transcript: Path) -> list[str]:
    outputs: list[str] = []
    for line in transcript.read_text(encoding="utf-8").splitlines():
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        payload = item.get("payload")
        if item.get("type") != "response_item" or not isinstance(payload, dict):
            continue
        if payload.get("type") != "custom_tool_call_output":
            continue
        for block in payload.get("output", []):
            if isinstance(block, dict) and isinstance(block.get("text"), str):
                outputs.append(block["text"])
    return outputs


def _tool_calls(transcript: Path) -> list[dict[str, str]]:
    calls: list[dict[str, str]] = []
    for line in transcript.read_text(encoding="utf-8").splitlines():
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        payload = item.get("payload")
        if item.get("type") != "response_item" or not isinstance(payload, dict):
            continue
        if payload.get("type") not in {"custom_tool_call", "function_call"}:
            continue
        calls.append(
            {
                "id": str(payload.get("call_id", payload.get("id", ""))),
                "name": str(payload.get("name", "")),
                "input": str(payload.get("input", payload.get("arguments", ""))),
            }
        )
    return calls


def _verify_native_outputs(
    outputs: list[str],
    *,
    slash_tmp_probe_exists: bool,
    tmpdir_probe_exists: bool,
    outside_read_probe_unchanged: bool,
    outside_read_probe_cleaned: bool,
    candidate_contents_unchanged: bool,
    changed_paths: list[str],
    git_status: str,
) -> dict[str, object]:
    combined = "\n".join(outputs)
    checks = {
        "valid_structural_result": bool(re.search(r'"status"\s*:\s*"valid"', combined)),
        "valid_exit_status": "VALID_EXIT_STATUS=0" in combined,
        "invalid_structural_result": bool(
            re.search(r'"status"\s*:\s*"invalid"', combined)
        ),
        "invalid_exit_status": "INVALID_EXIT_STATUS=1" in combined,
        "slash_tmp_write_denied": "SLASH_TMP_WRITE_DENIED" in combined,
        "tmpdir_write_denied": "TMPDIR_WRITE_DENIED" in combined,
        "outside_read_denied": "OUTSIDE_READ_DENIED" in combined,
        "outside_read_not_allowed": "OUTSIDE_READ_ALLOWED" not in combined,
        "outside_read_probe_unchanged": outside_read_probe_unchanged,
        "outside_read_probe_cleaned": outside_read_probe_cleaned,
        "no_probe_preexisted": not any(
            marker in combined
            for marker in ("SLASH_TMP_PROBE_PREEXISTS", "TMPDIR_PROBE_PREEXISTS")
        ),
        "no_probe_write_allowed": not any(
            marker in combined
            for marker in (
                "SLASH_TMP_WRITE_ALLOWED",
                "TMPDIR_WRITE_ALLOWED",
                "SLASH_TMP_WRITE_ALLOWED_CLEANUP_FAILED",
                "TMPDIR_WRITE_ALLOWED_CLEANUP_FAILED",
            )
        ),
        "no_probe_file_left": not slash_tmp_probe_exists and not tmpdir_probe_exists,
        "candidate_files_unchanged": candidate_contents_unchanged,
        "no_workspace_paths_changed": not changed_paths and not git_status,
    }
    return {"passed": all(checks.values()), "checks": checks}


def _verify_bundle(bundle: Path, manifest: dict) -> None:
    expected = set(manifest["files"]) | {"manifest.json"}
    actual = {
        path.relative_to(bundle).as_posix()
        for path in bundle.rglob("*")
        if path.is_file()
    }
    if actual != expected:
        raise ValueError("worker changed the structural bundle inventory")
    for relative, record in manifest["files"].items():
        path = bundle / relative
        if path.is_symlink() or _sha256(path) != record["sha256"]:
            raise ValueError(f"worker changed pinned structural file: {relative}")


def _build_workspace(workspace: Path, run_id: str) -> dict:
    if not PROJECT_PYTHON.is_file() or not os.access(PROJECT_PYTHON, os.X_OK):
        raise ValueError("verified project Python entrypoint is unavailable")
    contract_digest = _sha256(CONTRACT)
    if contract_digest != CONTRACT.with_suffix(".sha256").read_text().split()[0]:
        raise ValueError("historical follow-up contract digest changed")
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    protocol_digest = contract["source_pins"]["base_protocol_sha256"]
    if _sha256(PROTOCOL) != protocol_digest:
        raise ValueError("historical pilot protocol digest changed")
    if not workspace.is_relative_to(FIXTURE_CACHE) or workspace.exists():
        raise ValueError(
            "workspace must be a new fixture under the dedicated cache root"
        )
    workspace.mkdir(parents=True)

    builder = runpy.run_path(str(ROOT / "experiments/v4_build_check_bundle.py"))
    bundle = workspace / "structural_check"
    manifest = builder["build_bundle"](
        bundle,
        repo_root=ROOT,
        commit=contract["source_pins"]["structural_bundle_source_commit"],
        protocol_path=PROTOCOL,
        protocol_sha256=protocol_digest,
        python_executable=PROJECT_PYTHON,
    )

    from bias_optimizer.dsl.ast import Expr
    from bias_optimizer.v4.language import G0_LANGUAGE, extend_macro_language

    language = extend_macro_language(G0_LANGUAGE, []).to_dict()
    candidates = workspace / "candidate"
    for name, program in (
        (
            "valid",
            Expr("spatial_split", (Expr("image"),), {"rows": 2, "cols": 3}),
        ),
        ("invalid", Expr("fixture_unknown_operation")),
    ):
        folder = candidates / name
        folder.mkdir(parents=True)
        _write_json(folder / "language.json", language)
        (folder / "program.json").write_text(program.to_json() + "\n")

    (workspace / ".codex").mkdir()
    (workspace / ".codex/config.toml").write_text(
        'model = "gpt-6-luna"\n'
        'model_reasoning_effort = "max"\n'
        'approval_policy = "never"\n'
        'web_search = "disabled"\n\n'
        "[features]\n"
        "multi_agent = false\n"
        "remote_plugin = false\n",
        encoding="utf-8",
    )
    (workspace / ".sandbox_config.json").write_text(
        json.dumps({"own_workspace": str(candidates), "evaluator_dirs": []}) + "\n",
        encoding="utf-8",
    )
    (workspace / "AGENTS.md").write_text(
        "# Native V4 fixture\n\n"
        "This workspace contains only synthetic candidate JSON and a pinned "
        "data-free structural checker. Do not edit files or access paths "
        "outside this workspace. Run only the checks requested in the task.\n",
        encoding="utf-8",
    )
    (workspace / ".gitignore").write_text(
        ".codex-driver-home/\n.codex-driver-transcripts/\n",
        encoding="utf-8",
    )

    eve_src = str(EVE_ROOT / "src")
    if eve_src not in sys.path:
        sys.path.insert(0, eve_src)
    from scaling_evolve.providers.agent.codex_hooks import write_codex_hooks_file

    # EvE recreates this file at spawn. Keep the snapshot identical, while the
    # wrapper disables hooks: this fixture verifies OS permissions only.
    write_codex_hooks_file(workspace / ".codex/hooks.json", repo_root=EVE_ROOT)
    _run_git(workspace, "init", "-q")
    _run_git(workspace, "config", "--local", "user.name", "V4 native fixture")
    _run_git(
        workspace, "config", "--local", "user.email", "v4-native-fixture@localhost"
    )
    _run_git(workspace, "add", "--all")
    _run_git(
        workspace, "commit", "-q", "-m", "fixture: prepare native checker workspace"
    )
    return {
        "contract_sha256": contract_digest,
        "protocol_sha256": protocol_digest,
        "structural_source_commit": contract["source_pins"][
            "structural_bundle_source_commit"
        ],
        "python_executable": str(PROJECT_PYTHON.absolute()),
        "python_is_symlink": PROJECT_PYTHON.is_symlink(),
        "bundle_manifest_sha256": _sha256(bundle / "manifest.json"),
        "bundle_file_count": len(manifest["files"]),
        "candidate_hashes": {
            str(path.relative_to(workspace)): _sha256(path)
            for path in sorted(candidates.rglob("*.json"))
        },
        "probe_name": f"v4-native-{run_id}-probe",
    }


def run_fixture(run_id: str, usage_path: Path, workspace: Path, evidence: Path) -> dict:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", run_id):
        raise ValueError(
            "run id must contain only letters, digits, hyphens, and underscores"
        )
    usage_path = usage_path.expanduser().absolute()
    workspace = workspace.expanduser().absolute()
    evidence = evidence.expanduser().absolute()
    usage = json.loads(usage_path.read_text(encoding="utf-8"))
    _validate_usage(usage)
    if not workspace.is_relative_to(FIXTURE_CACHE) or workspace.exists():
        raise ValueError(
            "workspace must be a new fixture under the dedicated cache root"
        )
    if not evidence.is_relative_to(EVIDENCE_ROOT) or evidence.exists():
        raise ValueError(
            "evidence path must be new and inside the ignored V4 evidence root"
        )
    if not os.environ.get("TMPDIR"):
        raise ValueError("TMPDIR must be set to exercise its sandbox denial")
    slash_probe = Path("/tmp") / f"v4-native-{run_id}-probe"
    tmpdir_probe = Path(os.environ["TMPDIR"]) / f"v4-native-{run_id}-probe"
    outside_read_probe = FIXTURE_CACHE / f"v4-native-{run_id}-outside-read.txt"
    if slash_probe.exists() or tmpdir_probe.exists():
        raise ValueError("unique temporary probe path unexpectedly exists")
    if outside_read_probe.exists():
        raise ValueError("unique outside-read probe path unexpectedly exists")

    evidence.mkdir(parents=True)
    _write_json(evidence / "plus_usage_snapshot.json", usage)
    workspace_info = _build_workspace(workspace, run_id)
    from experiments.v4_sandbox_preflight import run_preflight

    preflight = run_preflight(workspace, evidence / "sandbox_preflight.json")
    if not preflight["passed"]:
        raise RuntimeError("sandbox preflight failed; native worker was not started")
    _validate_usage(json.loads(usage_path.read_text(encoding="utf-8")))
    (evidence / "initial_prompt.md").write_text(
        _fixture_instruction(workspace_info["probe_name"]), encoding="utf-8"
    )

    eve_src = str(EVE_ROOT / "src")
    if eve_src not in sys.path:
        sys.path.insert(0, eve_src)
    from scaling_evolve.providers.agent.drivers.base import (
        SessionSeed,
        SessionWorkspaceLease,
    )
    from scaling_evolve.providers.agent.drivers.codex_tmux import (
        CodexTmuxSessionDriver,
    )

    session_name = f"llmao-v4-native-{run_id}"
    pane = subprocess.check_output(
        [
            "tmux",
            "new-session",
            "-d",
            "-s",
            session_name,
            "-c",
            str(workspace),
            "-P",
            "-F",
            "#{pane_id}",
        ],
        text=True,
    ).strip()
    driver = CodexTmuxSessionDriver(
        pane_id=pane,
        run_root=evidence / "driver_run",
        executable=str(ROOT / "scripts/codex-v4-sandbox"),
        model="gpt-6-luna",
        reasoning_effort="max",
        rollout_max_turns=6,
        timeout_seconds=240,
        enable_multi_agent=False,
        approval_policy="never",
        sandbox_mode="workspace-write",
        web_search="disabled",
        provider_env={
            "FIXTURE_SLASH_TMP": "/tmp",
            "FIXTURE_OUTSIDE_READ": str(outside_read_probe),
        },
    )
    outside_read_probe.write_text("v4-native-outside-read-canary\n", encoding="utf-8")
    outside_read_probe_unchanged = False
    outside_read_probe_cleaned = False
    try:
        try:
            rollout = driver.spawn(
                SessionSeed(
                    instruction=_fixture_instruction(workspace_info["probe_name"]),
                    workspace=SessionWorkspaceLease(
                        workspace_id=run_id,
                        target_repo_root=str(workspace),
                        workspace_root=str(workspace),
                        session_cwd=str(workspace),
                    ),
                )
            )
        except Exception as exc:
            captured = subprocess.run(
                ["tmux", "capture-pane", "-p", "-S", "-200", "-t", pane],
                check=False,
                capture_output=True,
                text=True,
            )
            _write_json(
                evidence / "native_worker_failure.json",
                {
                    "exception_type": type(exc).__name__,
                    "message": str(exc),
                    "pane_capture_exit_code": captured.returncode,
                    "pane_capture": captured.stdout,
                },
            )
            raise
    finally:
        subprocess.run(
            ["tmux", "kill-session", "-t", session_name],
            check=False,
            capture_output=True,
            text=True,
        )
        outside_read_probe_unchanged = (
            outside_read_probe.is_file()
            and outside_read_probe.read_text(encoding="utf-8")
            == "v4-native-outside-read-canary\n"
        )
        if outside_read_probe_unchanged:
            outside_read_probe.unlink()
        outside_read_probe_cleaned = not outside_read_probe.exists()

    metadata = rollout.state.metadata
    transcript_source = Path(metadata["provider_transcript_path"])
    if transcript_source.is_symlink() or not transcript_source.is_file():
        raise ValueError("native worker transcript is missing or not a regular file")
    transcript = evidence / "native_transcript.jsonl"
    shutil.copyfile(transcript_source, transcript)
    tool_outputs = _tool_output_texts(transcript)
    tool_calls = _tool_calls(transcript)
    git_status = _run_git(workspace, "status", "--porcelain", "--untracked-files=all")
    bundle = workspace / "structural_check"
    manifest = json.loads((bundle / "manifest.json").read_text(encoding="utf-8"))
    _verify_bundle(bundle, manifest)
    post_candidate_hashes = {
        str(path.relative_to(workspace)): _sha256(path)
        for path in sorted((workspace / "candidate").rglob("*.json"))
    }
    slash_probe_written = slash_probe.exists()
    tmpdir_probe_written = tmpdir_probe.exists()
    for path in (slash_probe, tmpdir_probe):
        if path.exists():
            if path.read_text(encoding="utf-8") != "v4-native-fixture-probe":
                raise ValueError(
                    "unexpected content at a fixture-owned temp probe path"
                )
            path.unlink()

    evidence_bundle = evidence / "structural_check"
    shutil.copytree(bundle, evidence_bundle)
    for relative in (
        ".codex/config.toml",
        ".sandbox_config.json",
        "AGENTS.md",
        "candidate/valid/language.json",
        "candidate/valid/program.json",
        "candidate/invalid/language.json",
        "candidate/invalid/program.json",
    ):
        target = evidence / "workspace" / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(workspace / relative, target)

    candidate_contents_unchanged = (
        post_candidate_hashes == workspace_info["candidate_hashes"]
    )
    verification = _verify_native_outputs(
        tool_outputs,
        slash_tmp_probe_exists=slash_probe_written,
        tmpdir_probe_exists=tmpdir_probe_written,
        outside_read_probe_unchanged=outside_read_probe_unchanged,
        outside_read_probe_cleaned=outside_read_probe_cleaned,
        candidate_contents_unchanged=candidate_contents_unchanged,
        changed_paths=rollout.changed_paths,
        git_status=git_status,
    )
    result = {
        "schema_version": 1,
        "run_id": run_id,
        "purpose": "data-free native structural checker and workspace-only filesystem verification",
        "plan": usage["plan"],
        "model": "gpt-6-luna",
        "reasoning_effort": "max",
        "sandbox": {
            "permission_profile": "llmao-v4-workspace-only",
            "root_access": "deny_except_minimal",
            "workspace_default_access": "read",
            "writable_candidate_paths": [
                "candidate/language.json",
                "candidate/program.json",
                "solver/candidate/language.json",
                "solver/candidate/program.json",
            ],
            "network_access": False,
            "slash_tmp_access": "denied",
            "tmpdir_access": "denied",
            "remote_plugin_catalog": False,
        },
        "workspace": str(workspace),
        "evidence": str(evidence),
        "preflight": workspace_info,
        "sandbox_preflight": preflight,
        "native_summary": rollout.summary,
        "native_changed_paths": rollout.changed_paths,
        "native_tool_calls": tool_calls,
        "native_usage": rollout.usage.model_dump(mode="json")
        if rollout.usage
        else None,
        "native_driver_execution": metadata.get("driver_execution"),
        "native_tool_outputs": tool_outputs,
        "git_status_after": git_status,
        "candidate_hashes_after": post_candidate_hashes,
        "candidate_contents_unchanged": candidate_contents_unchanged,
        "slash_tmp_probe_still_exists_before_cleanup": slash_probe_written,
        "tmpdir_probe_still_exists_before_cleanup": tmpdir_probe_written,
        "outside_read_probe_unchanged": outside_read_probe_unchanged,
        "native_check_verification": verification,
        "transcript_sha256": _sha256(transcript),
    }
    _write_json(evidence / "result.json", result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--usage-snapshot", required=True, type=Path)
    parser.add_argument("--workspace", required=True, type=Path)
    parser.add_argument("--evidence", required=True, type=Path)
    args = parser.parse_args()
    result = run_fixture(
        args.run_id, args.usage_snapshot, args.workspace, args.evidence
    )
    print(
        json.dumps(
            {
                "run_id": result["run_id"],
                "summary": result["native_summary"],
                "native_usage": result["native_usage"],
                "git_status_after": result["git_status_after"],
                "slash_tmp_probe_still_exists": result[
                    "slash_tmp_probe_still_exists_before_cleanup"
                ],
                "tmpdir_probe_still_exists": result[
                    "tmpdir_probe_still_exists_before_cleanup"
                ],
                "verification": result["native_check_verification"],
                "evidence": result["evidence"],
            }
        )
    )
    return 0 if result["native_check_verification"]["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
