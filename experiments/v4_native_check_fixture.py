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


def _failure_details(exc: Exception) -> dict[str, object]:
    details: dict[str, object] = {
        "exception_type": type(exc).__name__,
        "message": str(exc),
    }
    if isinstance(exc, subprocess.CalledProcessError):
        details.update(
            command=exc.cmd,
            return_code=exc.returncode,
            stdout=exc.stdout,
            stderr=exc.stderr,
        )
    return details


def _uses_pinned_native_command(
    invocation: dict[str, object], workspace: Path
) -> bool:
    execution = invocation.get("native_driver_execution")
    command = execution.get("command") if isinstance(execution, dict) else None
    if not isinstance(command, list) or not all(
        isinstance(argument, str) for argument in command
    ):
        return False

    def has_option_value(option: str, value: str) -> bool:
        return any(
            command[index] == option and command[index + 1] == value
            for index in range(len(command) - 1)
        )

    return (
        bool(command)
        and command[0] == str((ROOT / "scripts/codex-v4-sandbox").resolve())
        and has_option_value("-s", "workspace-write")
        and has_option_value("-C", str(workspace.resolve()))
    )


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


def _build_workspace(
    workspace: Path,
    run_id: str,
    *,
    structural_bundle: Path | None = None,
) -> dict:
    if not PROJECT_PYTHON.is_file() or not os.access(PROJECT_PYTHON, os.X_OK):
        raise ValueError("verified project Python entrypoint is unavailable")
    contract_digest = None
    if structural_bundle is None:
        contract_digest = _sha256(CONTRACT)
        if contract_digest != CONTRACT.with_suffix(".sha256").read_text().split()[0]:
            raise ValueError("historical follow-up contract digest changed")
        contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        protocol_digest = contract["source_pins"]["base_protocol_sha256"]
        if _sha256(PROTOCOL) != protocol_digest:
            raise ValueError("historical pilot protocol digest changed")
        structural_source_commit = contract["source_pins"][
            "structural_bundle_source_commit"
        ]
    else:
        source_bundle = structural_bundle.expanduser().resolve(strict=True)
        source_manifest = source_bundle / "manifest.json"
        manifest_payload = json.loads(source_manifest.read_text(encoding="utf-8"))
        protocol_digest = manifest_payload["protocol_sha256"]
        structural_source_commit = manifest_payload["source_commit"]
    if not workspace.is_relative_to(FIXTURE_CACHE) or workspace.exists():
        raise ValueError(
            "workspace must be a new fixture under the dedicated cache root"
        )
    workspace.mkdir(parents=True)

    bundle = workspace / "structural_check"
    if structural_bundle is None:
        builder = runpy.run_path(str(ROOT / "experiments/v4_build_check_bundle.py"))
        manifest = builder["build_bundle"](
            bundle,
            repo_root=ROOT,
            commit=structural_source_commit,
            protocol_path=PROTOCOL,
            protocol_sha256=protocol_digest,
            python_executable=PROJECT_PYTHON,
        )
    else:
        shutil.copytree(source_bundle, bundle)
        manifest = json.loads((bundle / "manifest.json").read_text(encoding="utf-8"))
        _verify_bundle(bundle, manifest)

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
    system_prompt = workspace / "native_system_prompt.md"
    system_prompt.write_bytes(
        (ROOT / "configs/v4/native_fixture_worker.md").read_bytes()
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
        "structural_source_commit": structural_source_commit,
        "python_executable": str(PROJECT_PYTHON.absolute()),
        "python_is_symlink": PROJECT_PYTHON.is_symlink(),
        "bundle_manifest_sha256": _sha256(bundle / "manifest.json"),
        "bundle_file_count": len(manifest["files"]),
        "system_prompt_sha256": _sha256(system_prompt),
        "candidate_hashes": {
            str(path.relative_to(workspace)): _sha256(path)
            for path in sorted(candidates.rglob("*.json"))
        },
        "probe_name": f"v4-native-{run_id}-probe",
    }


def run_fixture(run_id: str, workspace: Path, evidence: Path) -> dict:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", run_id):
        raise ValueError(
            "run id must contain only letters, digits, hyphens, and underscores"
        )
    workspace = workspace.expanduser().absolute()
    evidence = evidence.expanduser().absolute()
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
    workspace_info = _build_workspace(workspace, run_id)
    from experiments.v4_sandbox_preflight import run_preflight

    preflight = run_preflight(workspace, evidence / "sandbox_preflight.json")
    if not preflight["passed"]:
        raise RuntimeError("sandbox preflight failed; native worker was not started")
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
    session_create_command = [
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
    ]
    pane = subprocess.check_output(session_create_command, text=True).strip()
    outside_read_probe_unchanged = False
    outside_read_probe_cleaned = False
    transcript_dir = evidence / "native_transcripts"
    invocations: list[dict[str, object]] = []
    session_cleanup: dict[str, object] = {}
    try:
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
            codex_system_prompt_file=str(workspace / "native_system_prompt.md"),
            provider_env={
                "FIXTURE_SLASH_TMP": "/tmp",
                "FIXTURE_OUTSIDE_READ": str(outside_read_probe),
            },
        )
        outside_read_probe.write_text(
            "v4-native-outside-read-canary\n", encoding="utf-8"
        )
        transcript_dir.mkdir()
        for invocation_number in (1, 2):
            invocation: dict[str, object] = {
                "invocation": invocation_number,
                "pane_id": pane,
                "pane_id_before": None,
            }
            try:
                pane_before = subprocess.run(
                    ["tmux", "display-message", "-p", "-t", pane, "#{pane_id}"],
                    check=True,
                    capture_output=True,
                    text=True,
                )
                invocation["pane_id_before"] = pane_before.stdout.strip()
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
                metadata = rollout.state.metadata
                invocation.update(
                    native_summary=rollout.summary,
                    native_usage=(
                        rollout.usage.model_dump(mode="json") if rollout.usage else None
                    ),
                    native_driver_execution=metadata.get("driver_execution"),
                    changed_paths=rollout.changed_paths,
                    candidate_hashes_after={
                        str(path.relative_to(workspace)): _sha256(path)
                        for path in sorted((workspace / "candidate").rglob("*.json"))
                    },
                    git_status_after=_run_git(
                        workspace, "status", "--porcelain", "--untracked-files=all"
                    ),
                )
                transcript_value = metadata.get("provider_transcript_path")
                if not isinstance(transcript_value, str):
                    raise TypeError("native worker transcript path was not recorded")
                transcript_source = Path(transcript_value)
                if transcript_source.is_symlink() or not transcript_source.is_file():
                    raise ValueError(
                        "native worker transcript is missing or not a regular file"
                    )
                transcript = transcript_dir / f"invocation-{invocation_number:02d}.jsonl"
                shutil.copyfile(transcript_source, transcript)
                pane_after = subprocess.run(
                    ["tmux", "display-message", "-p", "-t", pane, "#{pane_id}"],
                    check=True,
                    capture_output=True,
                    text=True,
                )
                invocation.update(
                    status="completed",
                    pane_id_after=pane_after.stdout.strip(),
                    transcript=transcript.relative_to(evidence).as_posix(),
                    transcript_sha256=_sha256(transcript),
                    native_tool_calls=_tool_calls(transcript),
                    native_tool_outputs=_tool_output_texts(transcript),
                )
            except Exception as exc:  # noqa: BLE001 - retain every invocation failure.
                captured = subprocess.run(
                    ["tmux", "capture-pane", "-p", "-S", "-200", "-t", pane],
                    check=False,
                    capture_output=True,
                    text=True,
                )
                pane_after = subprocess.run(
                    ["tmux", "display-message", "-p", "-t", pane, "#{pane_id}"],
                    check=False,
                    capture_output=True,
                    text=True,
                )
                failure = _failure_details(exc)
                invocation.update(
                    status="failed",
                    pane_id_after=pane_after.stdout.strip()
                    if pane_after.returncode == 0
                    else None,
                    failure=failure,
                    pane_capture_exit_code=captured.returncode,
                    pane_capture_stdout=captured.stdout,
                    pane_capture_stderr=captured.stderr,
                )
                _write_json(
                    evidence / f"native_worker_failure_{invocation_number:02d}.json",
                    invocation,
                )
            invocations.append(invocation)
    finally:
        cleanup = subprocess.run(
            ["tmux", "kill-session", "-t", session_name],
            check=False,
            capture_output=True,
            text=True,
        )
        session_cleanup = {
            "command": ["tmux", "kill-session", "-t", session_name],
            "return_code": cleanup.returncode,
            "stdout": cleanup.stdout,
            "stderr": cleanup.stderr,
        }
        if outside_read_probe.exists():
            outside_read_probe_unchanged = (
                outside_read_probe.is_file()
                and outside_read_probe.read_text(encoding="utf-8")
                == "v4-native-outside-read-canary\n"
            )
            if outside_read_probe_unchanged:
                outside_read_probe.unlink()
        outside_read_probe_cleaned = not outside_read_probe.exists()

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
        "native_system_prompt.md",
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
    system_prompt_path = workspace / "native_system_prompt.md"
    system_prompt_unchanged = (
        _sha256(system_prompt_path) == workspace_info["system_prompt_sha256"]
    )
    all_checks: dict[str, bool] = {}
    all_tool_calls: list[dict[str, str]] = []
    all_tool_outputs: list[str] = []
    all_changed_paths: set[str] = set()
    for invocation in invocations:
        number = invocation["invocation"]
        prefix = f"invocation_{number:02d}"
        transcript_relative = invocation.get("transcript")
        transcript_path = (
            evidence / transcript_relative
            if isinstance(transcript_relative, str)
            else None
        )
        transcript_captured = bool(
            transcript_path
            and transcript_path.is_file()
            and not transcript_path.is_symlink()
            and _sha256(transcript_path) == invocation.get("transcript_sha256")
        )
        same_pane_reused = (
            invocation.get("pane_id_before") == pane
            and invocation.get("pane_id_after") == pane
        )
        driver_execution = invocation.get("native_driver_execution")
        driver_command = (
            driver_execution.get("command")
            if isinstance(driver_execution, dict)
            else None
        )
        prompt_file_route_used = isinstance(driver_command, list) and any(
            isinstance(argument, str)
            and "model_instructions_file=" in argument
            and str(system_prompt_path) in argument
            for argument in driver_command
        )
        pinned_native_command = _uses_pinned_native_command(invocation, workspace)
        completed = invocation.get("status") == "completed"
        all_checks[f"{prefix}_completed"] = completed
        all_checks[f"{prefix}_transcript_captured"] = transcript_captured
        all_checks[f"{prefix}_same_pane_reused"] = same_pane_reused
        all_checks[f"{prefix}_system_prompt_file_route"] = prompt_file_route_used
        all_checks[f"{prefix}_uses_pinned_sandbox_command"] = pinned_native_command
        if completed:
            invocation_outputs = invocation.get("native_tool_outputs", [])
            invocation_calls = invocation.get("native_tool_calls", [])
            changed_paths = invocation.get("changed_paths", [])
            invocation_status = invocation.get("git_status_after", "")
            invocation_candidates = invocation.get("candidate_hashes_after", {})
            check = _verify_native_outputs(
                invocation_outputs,
                slash_tmp_probe_exists=slash_probe_written,
                tmpdir_probe_exists=tmpdir_probe_written,
                outside_read_probe_unchanged=outside_read_probe_unchanged,
                outside_read_probe_cleaned=outside_read_probe_cleaned,
                candidate_contents_unchanged=(
                    invocation_candidates == workspace_info["candidate_hashes"]
                ),
                changed_paths=changed_paths,
                git_status=invocation_status,
            )
            invocation["verification"] = check
            for name, passed in check["checks"].items():
                all_checks[f"{prefix}_{name}"] = passed
            all_tool_calls.extend(invocation_calls)
            all_tool_outputs.extend(invocation_outputs)
            all_changed_paths.update(changed_paths)
        else:
            invocation["verification"] = {
                "passed": False,
                "checks": {"invocation_completed": False},
            }
            all_checks[f"{prefix}_invocation_completed"] = False

    all_checks["two_sequential_invocations"] = len(invocations) == 2
    all_checks["same_driver_instance_reused_pane"] = (
        len(invocations) == 2
        and all(
            item.get("pane_id") == pane
            and item.get("pane_id_before") == pane
            and item.get("pane_id_after") == pane
            for item in invocations
        )
    )
    all_checks["tmux_session_cleanup_succeeded"] = (
        session_cleanup.get("return_code") == 0
    )
    all_checks["fixture_system_prompt_unchanged"] = system_prompt_unchanged
    verification = {
        "passed": bool(all_checks) and all(all_checks.values()),
        "checks": all_checks,
    }
    native_summaries = [
        item.get("native_summary")
        for item in invocations
        if isinstance(item.get("native_summary"), str)
    ]
    result = {
        "schema_version": 2,
        "run_id": run_id,
        "purpose": "two sequential data-free native structural and workspace-only checks",
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
        "native_run_lifecycle": {
            "session_created_by": "fixture",
            "session_create_command": session_create_command,
            "session_name": session_name,
            "pane_id": pane,
            "driver_class": "CodexTmuxSessionDriver",
            "driver_instance_count": 1,
            "requested_invocations": 2,
            "session_cleanup": session_cleanup,
            "system_prompt_file": str(system_prompt_path),
            "system_prompt_sha256": workspace_info["system_prompt_sha256"],
        },
        "native_invocations": invocations,
        "native_summary": "\n".join(native_summaries),
        "native_changed_paths": sorted(all_changed_paths),
        "native_tool_calls": all_tool_calls,
        "native_tool_outputs": all_tool_outputs,
        "native_usage_by_invocation": [
            {"invocation": item["invocation"], "usage": item.get("native_usage")}
            for item in invocations
            if item.get("status") == "completed"
        ],
        "native_driver_execution_by_invocation": [
            {
                "invocation": item["invocation"],
                "execution": item.get("native_driver_execution"),
            }
            for item in invocations
            if item.get("status") == "completed"
        ],
        "git_status_after": git_status,
        "candidate_hashes_after": post_candidate_hashes,
        "candidate_contents_unchanged": candidate_contents_unchanged,
        "slash_tmp_probe_still_exists_before_cleanup": slash_probe_written,
        "tmpdir_probe_still_exists_before_cleanup": tmpdir_probe_written,
        "outside_read_probe_unchanged": outside_read_probe_unchanged,
        "native_check_verification": verification,
    }
    _write_json(evidence / "result.json", result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--workspace", required=True, type=Path)
    parser.add_argument("--evidence", required=True, type=Path)
    args = parser.parse_args()
    result = run_fixture(args.run_id, args.workspace, args.evidence)
    print(
        json.dumps(
            {
                "run_id": result["run_id"],
                "summary": result["native_summary"],
                "invocations": [
                    {
                        "invocation": item["invocation"],
                        "status": item["status"],
                        "transcript": item.get("transcript"),
                    }
                    for item in result["native_invocations"]
                ],
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
