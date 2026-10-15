"""Exercise Phase2Runner-to-native-driver lineage handoff without dataset access."""

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
from types import ModuleType
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONTRACT = ROOT / "V4_FOLLOWUP_REPAIR_CONTRACT_20261015-02.json"
PROJECT_PYTHON = ROOT / ".venv/bin/python"
EVIDENCE_ROOT = ROOT / "results/v4/phase10_followup/native_worker_integration"
CACHE_ROOT = Path.home() / "Library/Caches/llmao-v4-eve-lineage-fixtures"
LANGUAGE_ONLY_PROBE = r"""
import errno, json, os, sys
workspace = sys.argv[1]
checks = {}
def can_write(relative, expected):
    try:
        descriptor = os.open(os.path.join(workspace, relative), os.O_WRONLY)
        os.close(descriptor)
        checks[relative] = expected
    except OSError as exc:
        checks[relative] = (not expected) and exc.errno in (errno.EPERM, errno.EACCES)
can_write("solver/candidate/language.json", True)
can_write("solver/candidate/program.json", False)
print(json.dumps({"checks": checks, "passed": all(checks.values())}, sort_keys=True))
sys.exit(0 if all(checks.values()) else 1)
"""


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_fixture_manifest(output: Path, *, run_id: str, status: str) -> dict[str, Any]:
    files: dict[str, dict[str, str | int]] = {}
    for path in sorted(output.rglob("*")):
        if path.is_symlink():
            raise ValueError(f"fixture evidence contains a symlink: {path}")
        if path.is_dir():
            continue
        if not path.is_file():
            raise ValueError(f"fixture evidence contains a special file: {path}")
        relative = path.relative_to(output).as_posix()
        if relative in {"manifest.json", "manifest.sha256"}:
            continue
        content = path.read_bytes()
        files[relative] = {
            "sha256": hashlib.sha256(content).hexdigest(),
            "size_bytes": len(content),
        }
    manifest = {
        "schema_version": 1,
        "run_id": run_id,
        "status": status,
        "files": files,
    }
    manifest_path = output / "manifest.json"
    sidecar_path = output / "manifest.sha256"
    _write_json(manifest_path, manifest)
    digest = _sha256(manifest_path)
    with sidecar_path.open("x", encoding="ascii") as stream:
        stream.write(f"{digest}  manifest.json\n")
    return {"path": str(manifest_path), "sha256": digest, "files": len(files)}


def _language_only_preflight_passed(payload: dict[str, Any], return_code: int) -> bool:
    expected_checks = {
        "solver/candidate/language.json": True,
        "solver/candidate/program.json": True,
    }
    return (
        return_code == 0
        and payload.get("passed") is True
        and payload.get("checks") == expected_checks
    )


def _render_lineage_fixture_prompt(
    *,
    prefill_id: str,
    language_hash: str,
) -> str:
    state_path = f"solver_examples/{prefill_id}/logs/evaluate/lineage_state.json"
    return (
        "# Data-free lineage handoff fixture\n\n"
        "This is one synthetic integration check, not a search or proposal. Do not "
        "read data, run a model evaluator, change the program, or edit any file "
        "other than `solver/candidate/language.json`.\n\n"
        f"Use only the selected prefill `{prefill_id}` at `solver_examples/{prefill_id}/`. "
        f"Read `{state_path}` and set only `parent_language_hash` in "
        "`solver/candidate/language.json` to the exact selected state's "
        f"`language_hash` value `{language_hash}`. Preserve every other language "
        "field exactly. Keep `solver/candidate/program.json` byte-for-byte "
        "identical to the selected prefill's `solver/candidate/program.json`.\n\n"
        "The fixture evaluator will run the pinned structural checker and real "
        "candidate-context builder after you finish. Stop after this single "
        "lineage handoff.\n"
    )


def _run_context_builder(
    candidate_directory: Path,
    *,
    context_path: Path,
    lineage_state_path: Path,
    parent_lineage_path: Path | None = None,
    parent_candidate_id: str | None = None,
    generation: int = 0,
) -> dict[str, Any]:
    command = [
        str(PROJECT_PYTHON),
        "-m",
        "experiments.v4_build_candidate_context",
        str(candidate_directory),
        str(context_path),
        "--lineage-state-output",
        str(lineage_state_path),
        "--generation",
        str(generation),
    ]
    if parent_lineage_path is not None:
        command.extend(["--parent-lineage", str(parent_lineage_path)])
    if parent_candidate_id is not None:
        command.extend(["--parent-candidate-id", parent_candidate_id])
    completed = subprocess.run(
        command,
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return {
        "command": command,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
        "context": _json(context_path),
        "lineage_state": _json(lineage_state_path),
    }


def _load_pinned_config(contract_path: Path, eve_root: Path) -> tuple[dict, Any]:
    eve_src = str(eve_root / "src")
    if eve_src not in sys.path:
        sys.path.insert(0, eve_src)
    from omegaconf import OmegaConf

    contract_bytes = contract_path.read_bytes()
    contract_digest = hashlib.sha256(contract_bytes).hexdigest()
    sidecar = contract_path.with_suffix(".sha256").read_text(encoding="ascii").split()[0]
    if contract_digest != sidecar:
        raise ValueError("repair contract digest mismatch")
    contract = json.loads(contract_bytes)
    source_pins = contract["source_pins"]
    if source_pins["eve_commit"] != subprocess.check_output(
        ["git", "-C", str(eve_root), "rev-parse", "HEAD"], text=True
    ).strip():
        raise ValueError("EvE checkout differs from the pinned repair runtime")
    status = subprocess.check_output(
        ["git", "-C", str(eve_root), "status", "--porcelain", "--untracked-files=all"],
        text=True,
    )
    if status:
        raise ValueError("EvE checkout must be clean for the data-free fixture")

    validation_path = Path(contract["launch"]["configuration_validation"])
    if _sha256(validation_path) != source_pins["configuration_validation_sha256"]:
        raise ValueError("resolved EvE configuration differs from its contract pin")
    validation = _json(validation_path)
    config = OmegaConf.create(validation["resolved_config"])
    immutable_root = Path(config["optimizer"]["workers"]["items"][0]["immutable"]).resolve()
    for relative, expected in source_pins["worker_immutable_files_sha256"].items():
        path = immutable_root / relative
        if path.is_symlink() or not path.is_file() or _sha256(path) != expected:
            raise ValueError(f"pinned worker overlay changed: {relative}")
    host_files = source_pins["host_files_sha256"]
    for relative in ("configs/v4/phase10_followup_worker.md",):
        path = ROOT / relative
        if path.is_symlink() or not path.is_file() or _sha256(path) != host_files[relative]:
            raise ValueError(f"pinned worker source changed: {relative}")

    fixture = contract["native_fixture_evidence"]
    fixture_root = Path(fixture["directory"])
    for relative, expected in fixture["files_sha256"].items():
        path = fixture_root / relative
        if path.is_symlink() or not path.is_file() or _sha256(path) != expected:
            raise ValueError(f"pinned native fixture evidence changed: {relative}")
    preflight = _json(fixture_root / "sandbox_preflight.json")
    native_result = _json(fixture_root / "result.json")
    native_verification = native_result.get("native_check_verification", {})
    if (
        preflight.get("passed") is not True
        or len(preflight.get("checks", {})) != 21
        or not all(preflight["checks"].values())
        or native_verification.get("passed") is not True
        or len(native_verification.get("checks", {})) != fixture["native_check_count"]
        or not all(native_verification["checks"].values())
    ):
        raise ValueError("pinned native sandbox fixture did not pass every check")

    wrapper = ROOT / "scripts/codex-v4-sandbox"
    if (
        host_files.get("scripts/codex-v4-sandbox") != fixture.get("wrapper_sha256")
        or wrapper.is_symlink()
        or not wrapper.is_file()
    ):
        raise ValueError("frozen wrapper pin no longer matches its historical fixture")
    return contract, config


def _verify_tmux_failure_capture(output: Path, eve_root: Path) -> dict[str, Any]:
    """Make a fake tmux fail once and verify exact subprocess evidence is captured."""
    eve_src = str(eve_root / "src")
    if eve_src not in sys.path:
        sys.path.insert(0, eve_src)
    from scaling_evolve.providers.agent import tmux_runtime

    fake_bin = output / "fake-bin"
    fake_bin.mkdir()
    fake_tmux = fake_bin / "tmux"
    fake_tmux.write_text(
        "#!/bin/sh\nprintf 'fixture stdout marker\\n'\n"
        "printf 'fixture stderr marker\\n' >&2\nexit 37\n",
        encoding="utf-8",
    )
    fake_tmux.chmod(0o755)
    trace_path = output / "tmux_failure_probe.jsonl"
    traced_module = ModuleType("v4_fixture_tmux_runtime")
    traced_module.launch_in_pane = tmux_runtime.launch_in_pane  # type: ignore[attr-defined]
    from experiments.v4_tmux_failure_capture import install_tmux_failure_capture

    install_tmux_failure_capture(trace_path, driver_module=traced_module)
    original_path = os.environ.get("PATH", "")
    os.environ["PATH"] = f"{fake_bin}{os.pathsep}{original_path}"
    try:
        try:
            traced_module.launch_in_pane(  # type: ignore[attr-defined]
                pane_id="%fixture",
                cwd=output,
                env={},
                argv=["codex"],
            )
        except subprocess.CalledProcessError:
            pass
        else:
            raise RuntimeError("fake tmux unexpectedly succeeded")
    finally:
        os.environ["PATH"] = original_path

    rows = [json.loads(line) for line in trace_path.read_text().splitlines()]
    if len(rows) != 1:
        raise ValueError("tmux failure hook did not record exactly one event")
    row = rows[0]
    command = row.get("command")
    if (
        not isinstance(command, list)
        or command[:6] != ["tmux", "respawn-pane", "-k", "-t", "%fixture", "-c"]
        or len(command) != 8
        or command[6] != str(output)
        or not isinstance(command[-1], str)
        or str(output) not in command[-1]
        or "codex" not in command[-1]
    ):
        raise ValueError("tmux failure hook did not preserve the exact command")
    if (
        row.get("return_code") != 37
        or row.get("stdout") != "fixture stdout marker\n"
        or row.get("stderr") != "fixture stderr marker\n"
        or row.get("cwd") != str(output)
        or row.get("pane_id") != "%fixture"
    ):
        raise ValueError("tmux failure hook dropped subprocess output or context")
    result = {"passed": True, "trace_file": trace_path.name, "failure": row}
    _write_json(output / "tmux_failure_probe.json", result)
    return result


class _DataFreeEvaluator:
    """Use LLMAO's real context builder while intentionally skipping all scoring."""

    def __init__(self, *, protocol_path: Path) -> None:
        self.protocol_path = protocol_path
        self.validation: dict[str, Any] = {"status": "not_run"}

    @staticmethod
    def check_boundary(workspace_root: Path, *, solver_workspace_builder: object) -> object:
        return solver_workspace_builder.boundary_check_result(workspace_root)

    def evaluate_candidate(
        self,
        workspace_root: Path,
        *,
        boundary_result: object,
        candidate_files: dict[str, str],
        optimize_logs: dict[str, str],
        solver_examples: list[object],
        prefill_solver: object,
        display_context: dict[str, str | int],
    ) -> tuple[dict[str, object], dict[str, str]]:
        del candidate_files, optimize_logs, solver_examples, display_context
        if not boundary_result.ok:
            self.validation = {
                "status": "boundary_failed",
                "summary": boundary_result.summary(),
            }
            return {"score": 0.0, "summary": "fixture boundary failed"}, {}

        selected_id = prefill_solver.id
        selected_state_path = (
            workspace_root
            / "solver_examples"
            / selected_id
            / "logs/evaluate/lineage_state.json"
        )
        selected_state = json.loads(selected_state_path.read_text(encoding="utf-8"))
        readme = (workspace_root / "README.md").read_text(encoding="utf-8")
        prefill_marker = f"solver_examples/{selected_id}/"
        language_path = workspace_root / "solver/candidate/language.json"
        program_path = workspace_root / "solver/candidate/program.json"
        candidate_language = _json(language_path)
        prefill_language = _json(workspace_root / "solver_examples" / selected_id / "solver/candidate/language.json")
        prefill_program_path = (
            workspace_root
            / "solver_examples"
            / selected_id
            / "solver/candidate/program.json"
        )
        expected_hash = selected_state["language_hash"]
        parent_matches = candidate_language.get("parent_language_hash") == expected_hash
        unchanged_except_parent = {
            key: value
            for key, value in candidate_language.items()
            if key != "parent_language_hash"
        } == {
            key: value
            for key, value in prefill_language.items()
            if key != "parent_language_hash"
        }
        program_unchanged = program_path.read_bytes() == prefill_program_path.read_bytes()
        check_command = [
            str(PROJECT_PYTHON),
            "-m",
            "experiments.v4_check_candidate",
            str(workspace_root / "solver/candidate"),
            "--parent-state",
            str(selected_state_path),
            "--protocol",
            str(self.protocol_path),
        ]
        checked = subprocess.run(
            check_command,
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        try:
            report = json.loads(checked.stdout)
        except json.JSONDecodeError:
            report = {
                "status": "invalid",
                "validation_error": "structural checker returned non-JSON output",
            }
        if not isinstance(report, dict):
            report = {
                "status": "invalid",
                "validation_error": "structural checker result must be a JSON object",
            }
        report["command"] = check_command
        report["return_code"] = checked.returncode
        report["stdout"] = checked.stdout
        report["stderr"] = checked.stderr
        context: dict[str, Any] | None = None
        child_state: dict[str, Any] | None = None
        context_builder: dict[str, Any] | None = None
        if report.get("status") == "valid" and checked.returncode == 0:
            context_builder = _run_context_builder(
                workspace_root / "solver/candidate",
                context_path=workspace_root / "fixture_candidate_context.json",
                lineage_state_path=workspace_root / "fixture_candidate_lineage_state.json",
                parent_lineage_path=(
                    workspace_root
                    / "solver_examples"
                    / selected_id
                    / "logs/evaluate/parent_language_lineage.json"
                ),
                parent_candidate_id=selected_state["candidate_id"],
                generation=selected_state["generation"] + 1,
            )
            context = context_builder["context"]
            child_state = context_builder["lineage_state"]
        checks = {
            "selected_prefill_rendered_in_readme": prefill_marker in readme,
            "selected_state_read_from_evE_workspace": selected_state_path.is_file(),
            "candidate_parent_matches_selected_language_hash": parent_matches,
            "candidate_language_unchanged_except_parent": unchanged_except_parent,
            "candidate_program_unchanged": program_unchanged,
            "real_context_builder_validated_candidate": report.get("status") == "valid",
            "real_context_builder_recorded_lineage": context_builder is not None
            and child_state is not None,
        }
        self.validation = {
            "status": "passed" if all(checks.values()) else "failed",
            "checks": checks,
            "selected_prefill_id": selected_id,
            "selected_lineage_state_sha256": _sha256(selected_state_path),
            "selected_language_hash": expected_hash,
            "candidate_parent_language_hash": candidate_language.get("parent_language_hash"),
            "candidate_check": report,
            "context_builder_command": (
                context_builder["command"] if context_builder is not None else None
            ),
            "context": context,
            "child_lineage_state": child_state,
        }
        logs = {
            "fixture_validation.json": json.dumps(self.validation, indent=2, sort_keys=True) + "\n"
        }
        if child_state is not None:
            logs["lineage_state.json"] = json.dumps(child_state, indent=2, sort_keys=True) + "\n"
        return {"score": 1.0 if all(checks.values()) else 0.0, "summary": "data-free lineage fixture"}, logs


def _verify_rollout(
    *,
    run_result: object,
    output: Path,
    tmux_trace: Path,
    system_prompt_path: Path,
) -> dict[str, Any]:
    rollouts = run_result.rollouts
    if len(rollouts) != 1:
        raise ValueError(f"expected one native rollout, got {len(rollouts)}")
    metadata = rollouts[0].state.metadata
    transcript_value = metadata.get("provider_transcript_path")
    if not isinstance(transcript_value, str):
        raise TypeError("EvE native driver did not record a provider transcript path")
    transcript_source = Path(transcript_value)
    if transcript_source.is_symlink() or not transcript_source.is_file():
        raise ValueError("native driver transcript is missing or unsafe")
    transcript = output / "native_transcripts/invocation-01.jsonl"
    transcript.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(transcript_source, transcript)
    instruction_path = metadata.get("instruction_path")
    execution = metadata.get("driver_execution")
    if not isinstance(instruction_path, str) or Path(instruction_path).name != "README.md":
        raise TypeError("EvE did not use its README.md prompt-file route")
    if not isinstance(execution, dict) or not isinstance(execution.get("command"), list):
        raise TypeError("EvE native driver execution command is missing")
    system_prompt = str(system_prompt_path.resolve(strict=True))
    if not any(
        isinstance(argument, str)
        and "model_instructions_file=" in argument
        and system_prompt in argument
        for argument in execution["command"]
    ):
        raise ValueError("native driver command did not use the pinned system prompt")
    failures = []
    if tmux_trace.is_file():
        failures = [json.loads(line) for line in tmux_trace.read_text().splitlines()]
    for failure in failures:
        if not all(
            key in failure
            for key in ("command", "return_code", "stdout", "stderr", "cwd", "pane_id")
        ):
            raise ValueError("native tmux trace is missing required failure fields")
    return {
        "driver_execution": execution,
        "instruction_path": instruction_path,
        "transcript": transcript.relative_to(output).as_posix(),
        "transcript_sha256": _sha256(transcript),
        "tmux_failures": failures,
    }


def _run_language_only_sandbox_preflight(
    workspace: Path,
    *,
    output: Path,
) -> dict[str, Any]:
    """Verify the fixture profile allows only the lineage file before model spawn."""
    wrapper_path = ROOT / "scripts/codex-v4-sandbox"
    code_home = workspace / ".codex-driver-home" / "lineage-language-only-preflight"
    if code_home.exists():
        raise FileExistsError("language-only preflight CODEX_HOME already exists")
    code_home.mkdir(parents=True)
    (code_home / "config.toml").write_text(
        'model = "gpt-6-luna"\n',
        encoding="utf-8",
    )
    environment = os.environ.copy()
    for key in (
        "OPENAI_API_KEY",
        "OPENAI_BASE_URL",
        "OPENAI_ORG_ID",
        "OPENAI_PROJECT_ID",
    ):
        environment.pop(key, None)
    environment.update(
        {
            "CODEX_HOME": str(code_home),
            "HOME": str(code_home.parent),
            "LLMAO_V4_FIXTURE_LANGUAGE_ONLY": "1",
        }
    )
    command = [
        str(wrapper_path),
        "sandbox",
        "-C",
        str(workspace),
        "--",
        str(PROJECT_PYTHON.resolve(strict=True)),
        "-IB",
        "-c",
        LANGUAGE_ONLY_PROBE,
        str(workspace),
    ]
    completed = subprocess.run(
        command,
        cwd=ROOT,
        env=environment,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError:
        payload = {"passed": False, "checks": {}}
    record = {
        "passed": _language_only_preflight_passed(payload, completed.returncode),
        "checks": payload.get("checks", {}),
        "command": command,
        "return_code": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }
    _write_json(output / "sandbox_profile_preflight.json", record)
    if not record["passed"]:
        raise RuntimeError("language-only Codex sandbox preflight failed")
    return record


def _install_fixture_driver_guards(
    driver: Any,
    *,
    output: Path,
    prefill_id: str,
    language_hash: str,
) -> dict[str, Any]:
    """Preflight EvE workspaces before spawn and capture abnormal tmux panes."""
    wrapper = runpy.run_path(str(ROOT / "scripts/codex-v4-sandbox"))
    preflight: dict[str, Any] = {"passed": False}
    pane_captures: list[dict[str, Any]] = []
    original_spawn = driver.spawn

    def checked_spawn(seed: Any) -> Any:
        workspace = Path(seed.working_directory).resolve(strict=True)
        readme = workspace / "README.md"
        original_readme = readme.read_text(encoding="utf-8")
        if f"solver_examples/{prefill_id}/" not in original_readme:
            raise ValueError("EvE README does not render the selected prefill")
        state_path = (
            workspace
            / "solver_examples"
            / prefill_id
            / "logs/evaluate/lineage_state.json"
        )
        if _json(state_path).get("language_hash") != language_hash:
            raise ValueError("EvE workspace prefill state differs from the fixture")
        prefill_program = (
            workspace
            / "solver_examples"
            / prefill_id
            / "solver/candidate/program.json"
        )
        candidate_program = workspace / "solver/candidate/program.json"
        if candidate_program.read_bytes() != prefill_program.read_bytes():
            raise ValueError("EvE candidate program differs from its selected prefill")
        readme.write_text(
            _render_lineage_fixture_prompt(
                prefill_id=prefill_id,
                language_hash=language_hash,
            ),
            encoding="utf-8",
        )
        wrapper["_validate_workspace"](workspace)
        sandbox_preflight = _run_language_only_sandbox_preflight(
            workspace,
            output=output,
        )
        preflight.update(
            {
                "passed": True,
                "sandbox_profile_preflight": sandbox_preflight,
                "workspace": str(workspace),
                "original_readme_sha256": hashlib.sha256(
                    original_readme.encode("utf-8")
                ).hexdigest(),
                "selected_prefill_program_sha256": _sha256(prefill_program),
                "markers": {
                    ".scaling_evolve/worker.yaml": _sha256(
                        workspace / ".scaling_evolve/worker.yaml"
                    ),
                    "structural_check/manifest.json": _sha256(
                        workspace / "structural_check/manifest.json"
                    ),
                    "README.md": _sha256(workspace / "README.md"),
                },
            }
        )
        _write_json(output / "workspace_preflight.json", preflight)
        return original_spawn(seed)

    driver.spawn = checked_spawn
    original_wait = driver._wait_for_completion

    def capture_abnormal_pane(**kwargs: Any) -> Any:
        try:
            completion = original_wait(**kwargs)
        except BaseException as exc:
            pane_id = str(kwargs.get("pane_id", ""))
            _capture_pane(pane_id, "wait_for_completion_exception", exc)
            raise
        if completion.session_jsonl is None or completion.task_complete_payload is None:
            _capture_pane(
                str(kwargs.get("pane_id", "")),
                "completion_without_transcript_or_task_complete",
            )
        return completion

    def _capture_pane(
        pane_id: str,
        reason: str,
        error: BaseException | None = None,
    ) -> None:
        from scaling_evolve.providers.agent.tmux_runtime import capture_pane

        record: dict[str, Any] = {"pane_id": pane_id, "reason": reason}
        if error is not None:
            record["error"] = f"{type(error).__name__}: {error}"
        try:
            record["contents"] = capture_pane(pane_id)
        except (OSError, subprocess.CalledProcessError) as capture_error:
            record["capture_error"] = (
                f"{type(capture_error).__name__}: {capture_error}"
            )
        pane_captures.append(record)
        _write_json(output / "abnormal_pane_captures.json", pane_captures)

    driver._wait_for_completion = capture_abnormal_pane
    return preflight


def run_fixture(run_id: str, *, contract_path: Path, eve_root: Path, output: Path) -> dict[str, Any]:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", run_id):
        raise ValueError("run ID must contain only letters, digits, hyphens, and underscores")
    eve_root = eve_root.expanduser().resolve(strict=True)
    output = output.expanduser().absolute()
    cache_run = CACHE_ROOT / run_id
    if not output.is_relative_to(EVIDENCE_ROOT) or output.exists():
        raise ValueError("fixture evidence path must be new inside the ignored evidence root")
    if cache_run.exists():
        raise ValueError("fixture cache path must be new")
    project_root = str(ROOT)
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    contract, config = _load_pinned_config(contract_path, eve_root)
    output.mkdir(parents=True)
    cache_run.mkdir(parents=True)
    _verify_tmux_failure_capture(output, eve_root)

    eve_src = str(eve_root / "src")
    if eve_src not in sys.path:
        sys.path.insert(0, eve_src)
    project_src = str(ROOT / "src")
    if project_src not in sys.path:
        sys.path.insert(0, project_src)
    from hydra.utils import instantiate
    from omegaconf import OmegaConf
    from scaling_evolve.algorithms.eve.factory import _load_solver_worker_configs
    from scaling_evolve.algorithms.eve.populations.entry import PopulationEntry
    from scaling_evolve.algorithms.eve.problem.repo import RepoTaskProblem
    from scaling_evolve.algorithms.eve.workflow.phase2 import Phase2Runner
    from scaling_evolve.algorithms.eve.workspace.solver_workspace import (
        SolverWorkspaceBuilder,
    )
    from scaling_evolve.providers.agent.drivers.codex_tmux import CodexTmuxSessionDriver

    config.loop.workspace_root = str(cache_run)
    config.loop.artifact_root = str(cache_run / "artifacts")
    config.loop.solver_db_path = str(cache_run / "solver_lineage.db")
    config.loop.optimizer_db_path = str(cache_run / "optimizer_lineage.db")
    config.loop.max_iterations = 1
    config.loop.n_workers_phase2 = 1
    config.loop.n_parallel_phase2 = 1
    config.loop.n_solver_examples_phase2 = 1
    config.loop.n_optimizer_examples_phase2 = 1
    config.loop.boundary_repair_attempts = 0
    config.loop.produce_optimizer_in_phase2 = 0

    problem = RepoTaskProblem.from_config(
        OmegaConf.to_container(config.application, resolve=True),
        cache_root=cache_run / "problem_cache",
        search_root=eve_root,
    )
    worker_configs = _load_solver_worker_configs(config, search_root=eve_root)
    selector = instantiate(config.optimizer.workers.selection, _convert_="all")
    builder = SolverWorkspaceBuilder(
        cache_run / "solver_workspaces",
        problem=problem,
        config=config.loop,
        immutable_files={},
        worker_configs=worker_configs,
        worker_selector=selector,
    )

    g0_files = {
        relative: (problem.snapshot_root / relative).read_text(encoding="utf-8")
        for relative in problem.editable_files
    }
    g0_candidate = cache_run / "g0_candidate"
    for relative, content in g0_files.items():
        path = g0_candidate / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    protocol_path = ROOT / "results/v4/protocol.json"
    parent_build = _run_context_builder(
        g0_candidate / "candidate",
        context_path=cache_run / "g0_context.json",
        lineage_state_path=cache_run / "g0_lineage_state.json",
    )
    parent_state = parent_build["lineage_state"]
    prefill_id = "solver_lineage_fixture_prefill"
    prefill = PopulationEntry(
        id=prefill_id,
        files=g0_files,
        score={"score": 0.0, "summary": "synthetic G0 prefill; not evaluated"},
        logs={
            "evaluate/lineage_state.json": json.dumps(parent_state, sort_keys=True),
            "evaluate/parent_language_lineage.json": json.dumps(
                parent_state["language_lineage"], sort_keys=True
            ),
        },
    )
    guidance_root = (eve_root / str(config.optimizer.initial_guidance)).resolve()
    guidance = {
        path.relative_to(guidance_root).as_posix(): path.read_text(encoding="utf-8")
        for path in guidance_root.rglob("*")
        if path.is_file()
    }
    guidance_path = "V4_SEARCH_GUIDANCE.md"
    if guidance_path not in guidance:
        raise FileNotFoundError("pinned V4 optimizer guidance is missing")
    guidance[guidance_path] += (
        "\n\n## Data-free lineage fixture\n\n"
        "This is one synthetic integration check, not a proposal run. Do not add a macro, "
        "change the program, read data, or run the model evaluator. Read the selected "
        "prefill's `logs/evaluate/lineage_state.json`, set only the candidate language's "
        "`parent_language_hash` to its exact `language_hash`, run the pinned structural "
        "checker with `--parent-state` pointing at that selected state, and stop.\n"
    )
    optimizer = PopulationEntry(
        id="optimizer_lineage_fixture",
        files=guidance,
        score={"elo": 1500.0},
        logs={},
    )
    evaluator = _DataFreeEvaluator(protocol_path=protocol_path)
    driver_config = contract["driver"]
    tmux_session = f"llmao-v4-lineage-{run_id}"
    pane_command = [
        "tmux",
        "new-session",
        "-d",
        "-s",
        tmux_session,
        "-c",
        str(cache_run),
        "-P",
        "-F",
        "#{pane_id}",
    ]
    pane_result = subprocess.run(pane_command, capture_output=True, text=True, check=True)
    pane_id = pane_result.stdout.strip()
    tmux_trace = output / "tmux_failures.jsonl"
    from experiments.v4_tmux_failure_capture import install_tmux_failure_capture

    install_tmux_failure_capture(tmux_trace)
    driver = None
    run_result = None
    workspace_preflight: dict[str, Any] = {"passed": False}
    try:
        driver = CodexTmuxSessionDriver(
            pane_id=pane_id,
            run_root=cache_run / "driver_run",
            executable=driver_config["executable"],
            model=driver_config["model"],
            reasoning_effort=driver_config["reasoning_effort"],
            rollout_max_turns=6,
            timeout_seconds=300,
            enable_multi_agent=False,
            approval_policy=driver_config["approval_policy"],
            sandbox_mode=driver_config["sandbox_mode"],
            web_search=driver_config["web_search"],
            codex_system_prompt_file=driver_config["system_prompt_file"],
            role="solver",
            provider_env={
                "LLMAO_PROJECT_ROOT": str(ROOT),
                "LLMAO_PYTHON": str(PROJECT_PYTHON),
                "LLMAO_DATA_DIR": str(cache_run / "no-data-access"),
                "LLMAO_V4_FIXTURE_LANGUAGE_ONLY": "1",
            },
        )
        workspace_preflight = _install_fixture_driver_guards(
            driver,
            output=output,
            prefill_id=prefill_id,
            language_hash=parent_state["language_hash"],
        )
        runner = Phase2Runner(
            solver_workspace_builder=builder,
            driver=driver,
            solver_evaluator=evaluator,
            step_label="lineage_fixture",
            iteration=1,
        )
        run_result = runner.run_single(
            optimizer=optimizer,
            solvers=[prefill],
            prefill_solver=prefill,
            worker_index=0,
        )
    finally:
        try:
            if driver is not None:
                driver.close()
        finally:
            cleanup = subprocess.run(
                ["tmux", "kill-session", "-t", tmux_session],
                capture_output=True,
                text=True,
                check=False,
            )

    if run_result is None or run_result.produced_solver is None:
        raise RuntimeError("EvE Phase2Runner produced no fixture candidate")
    rollout_evidence = _verify_rollout(
        run_result=run_result,
        output=output,
        tmux_trace=tmux_trace,
        system_prompt_path=Path(driver_config["system_prompt_file"]),
    )
    produced = run_result.produced_solver
    candidate_language = json.loads(produced.files["candidate/language.json"])
    report = evaluator.validation
    expected_hash = parent_state["language_hash"]
    passed = (
        report.get("status") == "passed"
        and candidate_language.get("parent_language_hash") == expected_hash
        and cleanup.returncode == 0
    )
    prompt = cache_run / "solver_workspaces" / run_result.workspace_id / "README.md"
    if prompt.is_file():
        shutil.copyfile(prompt, output / "README.md")
    result = {
        "schema_version": 1,
        "run_id": run_id,
        "status": "passed" if passed else "failed",
        "scope": "data-free Phase2Runner integration; evaluator context only; no dataset scoring",
        "contract_sha256": hashlib.sha256(contract_path.read_bytes()).hexdigest(),
        "eve_commit": contract["source_pins"]["eve_commit"],
        "configuration_validation_sha256": contract["source_pins"][
            "configuration_validation_sha256"
        ],
        "effective_fixture_overrides": {
            "loop.max_iterations": 1,
            "loop.n_workers_phase2": 1,
            "loop.n_parallel_phase2": 1,
            "loop.n_solver_examples_phase2": 1,
            "loop.n_optimizer_examples_phase2": 1,
            "loop.boundary_repair_attempts": 0,
            "loop.produce_optimizer_in_phase2": 0,
            "driver.rollout_max_turns": 6,
            "driver.timeout_seconds": 300,
        },
        "selected_prefill_id": prefill_id,
        "selected_language_hash": expected_hash,
        "candidate_parent_language_hash": candidate_language.get("parent_language_hash"),
        "candidate_validation": report,
        "native_rollout": rollout_evidence,
        "workspace_preflight": workspace_preflight,
        "system_prompt_file": driver_config["system_prompt_file"],
        "system_prompt_sha256": _sha256(Path(driver_config["system_prompt_file"])),
        "sandbox_wrapper_sha256": _sha256(ROOT / "scripts/codex-v4-sandbox"),
        "previous_sandbox_wrapper_sha256": contract["native_fixture_evidence"][
            "wrapper_sha256"
        ],
        "prompt_sha256": _sha256(output / "README.md") if (output / "README.md").is_file() else None,
        "tmux_session": {
            "create_command": pane_command,
            "pane_id": pane_id,
            "cleanup_command": ["tmux", "kill-session", "-t", tmux_session],
            "cleanup_return_code": cleanup.returncode,
            "cleanup_stdout": cleanup.stdout,
            "cleanup_stderr": cleanup.stderr,
        },
    }
    _write_json(output / "result.json", result)
    _write_fixture_manifest(output, run_id=run_id, status=result["status"])
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT)
    parser.add_argument("--eve-root", type=Path, default=ROOT.parent / "eve")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = run_fixture(
            args.run_id,
            contract_path=args.contract,
            eve_root=args.eve_root,
            output=args.output,
        )
    except Exception as exc:  # noqa: BLE001 - persist fixture failures for diagnosis.
        result = {
            "run_id": args.run_id,
            "status": "failed",
            "error": f"{type(exc).__name__}: {exc}",
        }
        if args.output.exists() and args.output.is_relative_to(EVIDENCE_ROOT):
            _write_json(args.output / "result.json", result)
        print(json.dumps(result, sort_keys=True))
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
