"""Freeze a separate, evidence-bound contract for the Phase 10 repair pilot."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import runpy
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OLD_CONTRACT = ROOT / "V4_FOLLOWUP_PILOT_CONTRACT.json"
OLD_ARCHIVE_MANIFEST = ROOT / "results/v4/phase10_followup/archive_verified/manifest.json"
PRIOR_REPAIR_CONTRACT = ROOT / "V4_FOLLOWUP_REPAIR_CONTRACT.json"
PRIOR_REPAIR_ARCHIVE = (
    ROOT / "results/v4/phase10_followup/archive/repair_followup_20261015-01"
)
PRIOR_REPAIR_ARCHIVE_MANIFEST = PRIOR_REPAIR_ARCHIVE / "manifest.json"
PROMPT = ROOT / "configs/v4/phase10_followup_worker.md"
WRAPPER = ROOT / "scripts/codex-v4-sandbox"
HOST_FILES = (
    "V4_FOLLOWUP_PILOT_CONTRACT.json",
    "V4_FOLLOWUP_PILOT_CONTRACT.sha256",
    "V4_FOLLOWUP_REPAIR_CONTRACT.json",
    "V4_FOLLOWUP_REPAIR_CONTRACT.sha256",
    "V4_FOLLOWUP_REPAIR_CONTRACT_20261015-02.json",
    "V4_FOLLOWUP_REPAIR_CONTRACT_20261015-02.sha256",
    "V4_FOLLOWUP_REPAIR_CONTRACT_20261015-03.json",
    "V4_FOLLOWUP_REPAIR_CONTRACT_20261015-03.sha256",
    "V4_FOLLOWUP_REPAIR_REPORT.md",
    "V4_FOLLOWUP_REPAIR_REPORT_20261015-02.md",
    "V4_FOLLOWUP_REPAIR_RESPONSE_PLAN.md",
    "V4_FOLLOWUP_REPAIR_RESPONSE_PLAN_20261015-02.md",
    "V4_FOLLOWUP_RESPONSE_PLAN.md",
    "V4_PHASE10_FOLLOWUP_REPORT.md",
    "V4_SANDBOX_REPAIR.md",
    "configs/v4/native_fixture_worker.md",
    "configs/v4/phase10_followup_worker.md",
    "experiments/v4_build_check_bundle.py",
    "experiments/v4_collect_followup.py",
    "experiments/v4_eve_lineage_fixture.py",
    "experiments/v4_eve_runner.py",
    "experiments/v4_evaluate_candidate.py",
    "experiments/v4_freeze_followup_repair_contract.py",
    "experiments/v4_launch_followup.py",
    "experiments/v4_native_check_fixture.py",
    "experiments/v4_sandbox_preflight.py",
    "experiments/v4_tmux_failure_capture.py",
    "results/v4/phase10_followup/archive_verified/manifest.json",
    "results/v4/phase10_followup/archive/repair_followup_20261015-01/manifest.json",
    "results/v4/phase10_followup/archive/repair_followup_20261015-01/manifest.sha256",
    "results/v4/phase10_followup/archive/repair_followup_20261015-02/manifest.json",
    "results/v4/phase10_followup/archive/repair_followup_20261015-02/manifest.sha256",
    "results/v4/phase10_followup/evidence/repair_followup_20261015-03/configuration_validation.json",
    "results/v4/phase10_followup/evidence/repair_followup_20261015-03/execution.json",
    "results/v4/phase10_followup/evidence/repair_followup_20261015-03/launcher_combined_output.txt",
    "results/v4/protocol.json",
    "scripts/codex-v4-sandbox",
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _verify_sha256_sidecar(path: Path) -> str:
    sidecar = path.with_suffix(".sha256")
    if (
        path.is_symlink()
        or not path.is_file()
        or sidecar.is_symlink()
        or not sidecar.is_file()
    ):
        raise ValueError(f"historical artifact or SHA-256 sidecar is missing: {path}")
    digest = _sha256(path)
    if digest != sidecar.read_text(encoding="ascii").split()[0]:
        raise ValueError(f"historical artifact digest changed: {path}")
    return digest


def _has_command_pair(command: list[str], option: str, value: str) -> bool:
    return any(
        command[index] == option and command[index + 1] == value
        for index in range(len(command) - 1)
    )


def _git(root: Path, *args: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(root), *args], text=True
    ).strip()


def _write_exclusive(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")


def _verify_manifest_records(value: object) -> int:
    """Rehash every record in the immutable failed-follow-up archive manifest."""
    checked = 0
    if isinstance(value, dict):
        if {"path", "sha256", "size_bytes"} <= value.keys():
            relative = Path(str(value["path"]))
            path = ROOT / relative
            resolved = path.resolve(strict=False)
            if (
                relative.is_absolute()
                or ".." in relative.parts
                or not resolved.is_relative_to(ROOT.resolve())
                or path.is_symlink()
                or not resolved.is_file()
            ):
                raise ValueError(f"protected prior artifact is missing: {path}")
            content = resolved.read_bytes()
            if (
                len(content) != value["size_bytes"]
                or hashlib.sha256(content).hexdigest() != value["sha256"]
            ):
                raise ValueError(f"protected prior artifact changed: {path}")
            return 1
        for child in value.values():
            checked += _verify_manifest_records(child)
    elif isinstance(value, list):
        for child in value:
            checked += _verify_manifest_records(child)
    return checked


def _validate_fixture(evidence_root: Path, old_contract_digest: str) -> dict:
    result_path = evidence_root / "result.json"
    preflight_path = evidence_root / "sandbox_preflight.json"
    paths = {
        "result.json": result_path,
        "sandbox_preflight.json": preflight_path,
        "structural_check/manifest.json": evidence_root
        / "structural_check/manifest.json",
        "workspace/native_system_prompt.md": evidence_root
        / "workspace/native_system_prompt.md",
    }
    for name, path in paths.items():
        if path.is_symlink() or not path.is_file():
            raise ValueError(f"native fixture artifact is missing: {name}")

    result = json.loads(result_path.read_text())
    preflight = json.loads(preflight_path.read_text())
    invocations = result.get("native_invocations")
    lifecycle = result.get("native_run_lifecycle")
    session_cleanup = lifecycle.get("session_cleanup") if isinstance(lifecycle, dict) else None
    if not isinstance(invocations, list) or len(invocations) != 2:
        raise ValueError("native fixture must contain two sequential invocations")
    if (
        not isinstance(lifecycle, dict)
        or lifecycle.get("session_created_by") != "fixture"
        or not isinstance(lifecycle.get("session_name"), str)
        or lifecycle.get("session_create_command")
        != [
            "tmux",
            "new-session",
            "-d",
            "-s",
            lifecycle.get("session_name"),
            "-c",
            str(Path(result["workspace"]).resolve()),
            "-P",
            "-F",
            "#{pane_id}",
        ]
        or lifecycle.get("driver_class") != "CodexTmuxSessionDriver"
        or lifecycle.get("driver_instance_count") != 1
        or lifecycle.get("requested_invocations") != 2
        or not isinstance(session_cleanup, dict)
        or session_cleanup.get("command")
        != ["tmux", "kill-session", "-t", lifecycle.get("session_name")]
        or session_cleanup.get("return_code") != 0
    ):
        raise ValueError(
            "native fixture did not document reusable single-driver pane ownership"
        )
    for expected_number, invocation in enumerate(invocations, start=1):
        if (
            invocation.get("invocation") != expected_number
            or invocation.get("status") != "completed"
            or invocation.get("pane_id") != lifecycle.get("pane_id")
            or invocation.get("pane_id_before") != lifecycle.get("pane_id")
            or invocation.get("pane_id_after") != lifecycle.get("pane_id")
            or invocation.get("verification", {}).get("passed") is not True
            or not all(invocation.get("verification", {}).get("checks", {}).values())
        ):
            raise ValueError("native fixture invocation did not complete on the reused pane")
        relative = Path(invocation.get("transcript", ""))
        transcript_candidate = evidence_root / relative
        transcript_path = transcript_candidate.resolve(strict=False)
        if (
            relative.is_absolute()
            or ".." in relative.parts
            or not transcript_path.is_relative_to(evidence_root.resolve())
            or transcript_candidate.is_symlink()
            or not transcript_path.is_file()
            or _sha256(transcript_path) != invocation.get("transcript_sha256")
        ):
            raise ValueError("native fixture transcript is missing or changed")
        if relative.as_posix() in paths:
            raise ValueError("native fixture transcript path is duplicated")
        paths[relative.as_posix()] = transcript_path

        transcript_calls = []
        for line in transcript_path.read_text(encoding="utf-8").splitlines():
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue
            payload = item.get("payload")
            if (
                item.get("type") == "response_item"
                and isinstance(payload, dict)
                and payload.get("type") in {"custom_tool_call", "function_call"}
            ):
                transcript_calls.append(payload)
        recorded_calls = invocation.get("native_tool_calls", [])
        normalized_calls = [
            {
                "id": str(call.get("call_id", call.get("id", ""))),
                "name": str(call.get("name", "")),
                "input": str(call.get("input", call.get("arguments", ""))),
            }
            for call in transcript_calls
        ]
        if normalized_calls != recorded_calls:
            raise ValueError("native tool-call summary differs from its transcript")
        if not transcript_calls or any(call.get("name") != "exec" for call in transcript_calls):
            raise ValueError("native fixture used an unexpected tool path")
        execution = invocation.get("native_driver_execution", {})
        command = execution.get("command") if isinstance(execution, dict) else None
        prompt_path = lifecycle.get("system_prompt_file")
        workspace_path = str(Path(result["workspace"]).resolve())
        if (
            prompt_path != str(Path(workspace_path) / "native_system_prompt.md")
            or invocation.get("verification", {}).get("passed") is not True
            or not isinstance(command, list)
            or not command
            or not all(isinstance(argument, str) for argument in command)
            or command[0] != str(WRAPPER.resolve())
            or not _has_command_pair(command, "-s", "workspace-write")
            or not _has_command_pair(command, "-C", workspace_path)
            or not any(
                "model_instructions_file=" in argument
                and isinstance(prompt_path, str)
                and prompt_path in argument
                for argument in command
            )
        ):
            raise ValueError("native fixture did not use the system prompt-file route")

    prompt_evidence = paths["workspace/native_system_prompt.md"]
    fixture_prompt_source = ROOT / "configs/v4/native_fixture_worker.md"
    if (
        _sha256(prompt_evidence) != lifecycle.get("system_prompt_sha256")
        or lifecycle.get("system_prompt_sha256")
        != result.get("preflight", {}).get("system_prompt_sha256")
        or _sha256(prompt_evidence) != _sha256(fixture_prompt_source)
    ):
        raise ValueError("native fixture system prompt differs from its recorded pin")
    if result.get("preflight", {}).get("contract_sha256") != old_contract_digest:
        raise ValueError("native fixture structural source was not bound to the old contract")
    if (
        preflight.get("permission_profile") != "llmao-v4-workspace-only"
        or preflight.get("passed") is not True
        or len(preflight.get("checks", {})) != 21
        or not all(preflight["checks"].values())
    ):
        raise ValueError("native no-model preflight did not pass all 21 checks")
    structural_manifest = json.loads(paths["structural_check/manifest.json"].read_text())
    if (
        _sha256(paths["structural_check/manifest.json"])
        != preflight.get("bundle_manifest_sha256")
        or result.get("sandbox_preflight", {}).get("checks") != preflight["checks"]
        or result.get("preflight", {}).get("bundle_manifest_sha256")
        != preflight.get("bundle_manifest_sha256")
    ):
        raise ValueError("native fixture bundle evidence does not reconcile")
    if (
        result.get("native_check_verification", {}).get("passed") is not True
        or not all(result["native_check_verification"]["checks"].values())
        or result.get("native_changed_paths") != []
        or result.get("git_status_after") != ""
        or result.get("candidate_contents_unchanged") is not True
    ):
        raise ValueError("native fixture sequential-run or filesystem audit failed")
    if (
        result.get("sandbox", {}).get("permission_profile")
        != "llmao-v4-workspace-only"
        or result.get("sandbox", {}).get("network_access") is not False
        or result.get("sandbox", {}).get("remote_plugin_catalog") is not False
    ):
        raise ValueError("native fixture did not use the pinned isolated policy")
    return {
        "run_id": result["run_id"],
        "directory": str(evidence_root.resolve()),
        "files_sha256": {name: _sha256(path) for name, path in paths.items()},
        "permission_profile": preflight["permission_profile"],
        "preflight_check_count": len(preflight["checks"]),
        "native_check_count": len(result["native_check_verification"]["checks"]),
        "worker_prompt_source_sha256": _sha256(fixture_prompt_source),
        "bundle_manifest_sha256": preflight["bundle_manifest_sha256"],
        "wrapper_sha256": preflight["wrapper_sha256"],
        "runtime_manifest": structural_manifest,
    }


def _build_immutable_overlay(
    eve_root: Path, evidence_root: Path, destination: Path
) -> dict[str, str]:
    """Pair EvE's worker guidance with the runtime-bound tested checker bundle."""
    if destination.exists() or destination.is_symlink():
        raise FileExistsError(f"repair immutable overlay already exists: {destination}")
    eve_immutable = (
        eve_root
        / "configs/eve/optimizer/llmao_v4_language_followup/immutable"
    )
    bundle_source = evidence_root / "structural_check"
    if bundle_source.is_symlink() or not bundle_source.is_dir():
        raise ValueError("native fixture structural bundle is missing")

    destination.mkdir(parents=True)
    hashes: dict[str, str] = {}
    for name in ("AGENTS.md", "README.md"):
        source = eve_immutable / name
        if source.is_symlink() or not source.is_file():
            raise ValueError(f"pinned EvE immutable guidance is missing: {name}")
        target = destination / name
        shutil.copyfile(source, target)
        hashes[name] = _sha256(target)

    bundle_target = destination / "structural_check"
    bundle_target.mkdir()
    for source in sorted(bundle_source.rglob("*")):
        relative = source.relative_to(bundle_source)
        if source.is_symlink():
            raise ValueError(f"native checker bundle contains a symlink: {relative}")
        target = bundle_target / relative
        if source.is_dir():
            target.mkdir(parents=True, exist_ok=True)
        elif source.is_file():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
            hashes[f"structural_check/{relative.as_posix()}"] = _sha256(target)
        else:
            raise ValueError(f"native checker bundle contains a special file: {relative}")
    if "structural_check/manifest.json" not in hashes:
        raise ValueError("native checker manifest is missing from the overlay")
    return hashes


def _render_config(
    eve_root: Path,
    arguments: list[str],
    *,
    project_root: Path,
    trace_path: Path,
) -> tuple[str, list[str]]:
    command = [
        str(eve_root / ".venv/bin/python"),
        "-u",
        str((ROOT / "experiments/v4_eve_runner.py").resolve()),
        *arguments,
        "--cfg",
        "job",
        "--resolve",
    ]
    environment = os.environ.copy()
    environment.update(
        {
            "LLMAO_PROJECT_ROOT": str(project_root.resolve(strict=True)),
            "LLMAO_EVE_SOURCE_ROOT": str((eve_root / "src").resolve(strict=True)),
            "LLMAO_V4_TMUX_TRACE_PATH": str(trace_path),
        }
    )
    completed = subprocess.run(
        command,
        cwd=eve_root,
        env=environment,
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout, command


def freeze(
    *,
    eve_root: Path,
    runtime_checkout: Path,
    evidence_root: Path,
    lineage_evidence_root: Path,
    run_root: Path,
    execution_record: Path,
    label: str,
    contract_path: Path,
) -> dict:
    """Build and hash a new pilot contract without changing prior evidence."""
    eve_root = eve_root.resolve(strict=True)
    runtime_checkout = runtime_checkout.resolve(strict=True)
    evidence_root = evidence_root.resolve(strict=True)
    lineage_evidence_root = lineage_evidence_root.resolve(strict=True)
    if _git(ROOT, "status", "--porcelain", "--untracked-files=all"):
        raise ValueError("freeze from a clean, committed LLMAO source tree")
    runtime_commit = _git(ROOT, "rev-parse", "HEAD")
    if _git(runtime_checkout, "rev-parse", "HEAD") != runtime_commit:
        raise ValueError("runtime checkout must use the committed LLMAO source")
    if _git(runtime_checkout, "status", "--porcelain", "--untracked-files=all"):
        raise ValueError("runtime checkout must be clean")
    original = json.loads(OLD_CONTRACT.read_text())
    old_digest = _verify_sha256_sidecar(OLD_CONTRACT)
    prior_repair_digest = _verify_sha256_sidecar(PRIOR_REPAIR_CONTRACT)
    prior_repair_contract = json.loads(PRIOR_REPAIR_CONTRACT.read_text())
    if (
        prior_repair_contract.get("phase") != "10_followup_boundary_repair"
        or prior_repair_contract.get("status") != "frozen_before_repair_launch"
    ):
        raise ValueError("previous repair contract is not the preserved failed contract")
    if _git(eve_root, "rev-parse", "HEAD") != original["source_pins"]["eve_commit"]:
        raise ValueError("EvE checkout differs from the preserved pilot pin")
    if _git(eve_root, "status", "--porcelain", "--untracked-files=all"):
        raise ValueError("EvE checkout must be clean")
    for relative, expected in original["eve_file_sha256"].items():
        if _sha256(eve_root / relative) != expected:
            raise ValueError(f"pinned EvE file changed: {relative}")

    archive_manifest = json.loads(OLD_ARCHIVE_MANIFEST.read_text())
    protected_record_count = _verify_manifest_records(archive_manifest)
    if protected_record_count != 218:
        raise ValueError("protected failed-pilot archive record count changed")
    prior_repair_manifest_digest = _verify_sha256_sidecar(
        PRIOR_REPAIR_ARCHIVE_MANIFEST
    )
    prior_repair_manifest = json.loads(PRIOR_REPAIR_ARCHIVE_MANIFEST.read_text())
    if (
        prior_repair_manifest.get("phase") != 10
        or prior_repair_manifest.get("pilot_status") != "failed"
    ):
        raise ValueError("previous repair archive no longer records a failed pilot")
    prior_repair_record_count = _verify_manifest_records(prior_repair_manifest)
    if prior_repair_record_count != 211:
        raise ValueError("protected prior repair archive record count changed")
    fixture = _validate_fixture(evidence_root, old_digest)
    launcher = runpy.run_path(str(ROOT / "experiments/v4_launch_followup.py"))
    latest_failed_repair = launcher["_verify_latest_failed_repair_artifacts"]()
    failed_startup = launcher["_verify_failed_startup_contract_03"]()
    previous_wrapper_sha256 = latest_failed_repair[
        "latest_failed_repair_wrapper_sha256"
    ]
    if fixture["wrapper_sha256"] != previous_wrapper_sha256:
        raise ValueError("native fixture no longer matches the latest failed contract")
    lineage_fixture = launcher["_verify_real_runner_lineage_fixture"](
        {"directory": str(lineage_evidence_root)},
        expected_wrapper_sha256=_sha256(WRAPPER),
    )
    lineage_result = json.loads(
        (lineage_evidence_root / "result.json").read_text(encoding="utf-8")
    )
    if (
        lineage_result.get("previous_sandbox_wrapper_sha256")
        != previous_wrapper_sha256
        or lineage_result.get("sandbox_wrapper_sha256") != _sha256(WRAPPER)
    ):
        raise ValueError("real-runner fixture wrapper lineage is inconsistent")
    runtime = launcher["_runtime_snapshot"](ROOT / ".venv/bin/python")
    runtime_manifest = fixture["runtime_manifest"]
    if (
        runtime_manifest.get("python_executable")
        != runtime["project_python_entrypoint"]
        or runtime_manifest.get("launcher_python_executable")
        != runtime["resolved_python_executable"]
        or runtime_manifest.get("python_site_packages") != runtime["site_packages"]
        or runtime_manifest.get("python_runtime", {}).get("version")
        != runtime["python_version"]
        or runtime_manifest.get("python_runtime", {}).get("dependencies")
        != runtime["dependencies"]
    ):
        raise ValueError("native fixture did not exercise the current Python runtime")
    fixture.pop("runtime_manifest")
    fixture["runtime_sha256"] = runtime["sha256"]

    if run_root.exists() or execution_record.exists():
        raise ValueError("repair run root and execution record must be unused")
    if not execution_record.is_absolute():
        execution_record = ROOT / execution_record
    if not execution_record.resolve().is_relative_to(ROOT.resolve()):
        raise ValueError("execution record must be inside this repository")
    if not contract_path.is_absolute():
        contract_path = ROOT / contract_path
    contract_path = contract_path.resolve()
    if not contract_path.is_relative_to(ROOT.resolve()):
        raise ValueError("new repair contract must be inside this repository")
    if contract_path.exists() or contract_path.with_suffix(".sha256").exists():
        raise FileExistsError("repair contract and digest must be new files")

    seed_root = eve_root / "examples/llmao_v4_language_followup/task/candidate"
    seed_files = {
        "examples/llmao_v4_language_followup/task/candidate/language.json": _sha256(
            seed_root / "language.json"
        ),
        "examples/llmao_v4_language_followup/task/candidate/program.json": _sha256(
            seed_root / "program.json"
        ),
        "examples/llmao_v4_language_followup/task/g0_reference.json": _sha256(
            eve_root / "examples/llmao_v4_language_followup/task/g0_reference.json"
        ),
    }
    seed_language = json.loads((seed_root / "language.json").read_text())
    if seed_language.get("macros") != [] or seed_language.get("introduced_macros") != []:
        raise ValueError("repair seed must be the original macro-free G0 language")
    if seed_language.get("base_language_hash") != seed_language.get("parent_language_hash"):
        raise ValueError("repair seed must have no prior language parent")

    host_hashes = {relative: _sha256(ROOT / relative) for relative in HOST_FILES}
    prompt_path = str(PROMPT.resolve())
    wrapper_path = str(WRAPPER.resolve())
    run_root = run_root.resolve()
    execution_record = execution_record.resolve()
    evidence_dir = execution_record.parent
    config_path = evidence_dir / "configuration_validation.json"
    snapshot_path = evidence_dir / "evaluator_source_snapshot.json"
    immutable_overlay = evidence_dir / "immutable"
    if config_path.exists() or snapshot_path.exists():
        raise FileExistsError("repair validation evidence paths must be new")
    overlay_hashes = _build_immutable_overlay(
        eve_root, evidence_root, immutable_overlay
    )
    pinned_collector = evidence_dir / "collector_contract_pinned.py"
    collector_bytes = (ROOT / "experiments/v4_collect_followup.py").read_bytes()
    collector_digest = hashlib.sha256(collector_bytes).hexdigest()
    if collector_digest != host_hashes["experiments/v4_collect_followup.py"]:
        raise ValueError("collector source changed while freezing its evidence")
    with pinned_collector.open("xb") as stream:
        stream.write(collector_bytes)
    overlay_manifest_path = immutable_overlay / "structural_check/manifest.json"
    overlay_manifest = json.loads(overlay_manifest_path.read_text())
    if (
        overlay_manifest
        != runtime_manifest
        or _sha256(overlay_manifest_path) != fixture["bundle_manifest_sha256"]
    ):
        raise ValueError("repair overlay is not the exact tested runtime-bound bundle")

    hydra_arguments = [
        "--config-name=llmao_v4",
        "application=llmao_v4_language_followup",
        "optimizer=llmao_v4_language_followup",
        "evaluation=llmao_v4_language_pilot",
        "loop.max_iterations=10",
        "loop.n_workers_phase2=1",
        "loop.n_parallel_phase2=1",
        "loop.n_solver_examples_phase2=32",
        "loop.boundary_repair_attempts=0",
        "driver.system_prompt_file=" + prompt_path,
        "driver.executable=" + wrapper_path,
        "driver.driver=codex_tmux",
        "driver.sandbox_mode=workspace-write",
        "driver.approval_policy=never",
        "driver.allow_network=false",
        "driver.web_search=disabled",
        "driver.enable_multi_agent=false",
        f"optimizer.workers.items.0.immutable={immutable_overlay}",
        "label=" + label,
        "run_root=" + str(run_root),
    ]
    config_text, config_command = _render_config(
        eve_root,
        hydra_arguments,
        project_root=runtime_checkout,
        trace_path=evidence_dir / "config_validation_tmux_failures.jsonl",
    )
    configuration = {
        "status": "resolved_without_worker_launch",
        "command_arguments": hydra_arguments,
        "runner_command": config_command,
        "resolved_config_sha256": hashlib.sha256(config_text.encode()).hexdigest(),
        "resolved_config": config_text,
    }
    _write_exclusive(config_path, configuration)

    snapshot_code = (
        "import json,sys; from pathlib import Path; "
        "sys.path.insert(0, str(Path(sys.argv[1]) / 'src')); "
        "from bias_optimizer.v4.evaluator import evaluator_source_snapshot; "
        "print(json.dumps(evaluator_source_snapshot(Path(sys.argv[1])), "
        "sort_keys=True))"
    )
    snapshot_output = subprocess.check_output(
        [str(ROOT / ".venv/bin/python"), "-c", snapshot_code, str(runtime_checkout)],
        cwd=ROOT,
        text=True,
    )
    evaluator_snapshot = json.loads(snapshot_output)
    _write_exclusive(snapshot_path, evaluator_snapshot)

    contract = json.loads(json.dumps(original))
    contract["account"].pop("verify_before_worker_launch", None)
    contract["artifact_requirements"] = [
        requirement
        for requirement in contract.get("artifact_requirements", [])
        if "current account snapshot" not in str(requirement).lower()
        and "usage snapshot" not in str(requirement).lower()
    ]
    contract.update(
        {
            "schema_version": 5,
            "phase": "10_followup_boundary_repair",
            "status": "frozen_before_repair_launch",
        }
    )
    contract["driver"].update(
        {
            "executable": wrapper_path,
            "sandbox_profile": "llmao-v4-workspace-only",
            "system_prompt_file": prompt_path,
            "sandbox_mode": "workspace-write",
            "driver": "codex_tmux",
            "allow_network": False,
            "web_search": "disabled",
            "enable_multi_agent": False,
        }
    )
    contract["launch"].update(
        {
            "evaluator_checkout": str(runtime_checkout),
            "run_root": str(run_root),
            "label": label,
            "python": str(ROOT / ".venv/bin/python"),
            "hydra_arguments": hydra_arguments,
            "configuration_validation": str(config_path),
            "evaluator_source_snapshot": str(snapshot_path),
            "execution_record": str(execution_record),
            "immutable_overlay": str(immutable_overlay),
            "runner_entrypoint": str(
                (ROOT / "experiments/v4_eve_runner.py").resolve()
            ),
            "tmux_failure_trace": str(run_root / "tmux_failures.jsonl"),
        }
    )
    contract["initialization"].update(
        {
            "source": "fresh macro-free G0 seed; no prior run state imported",
            "fresh_g0_initialization": True,
            "resume_previous_run": False,
            "import_prior_program": False,
            "import_prior_macros": False,
            "import_prior_guidance_state": False,
            "import_prior_population": False,
            "import_prior_winner": False,
            "seed_files_sha256": seed_files,
            "seed_language_sha256": seed_files[
                "examples/llmao_v4_language_followup/task/candidate/language.json"
            ],
            "seed_program_sha256": seed_files[
                "examples/llmao_v4_language_followup/task/candidate/program.json"
            ],
        }
    )
    contract["source_pins"].update(
        {
            "llmao_runtime_commit": runtime_commit,
            "evaluator_source_sha256": evaluator_snapshot["sha256"],
            "evaluator_source_snapshot_file_sha256": _sha256(snapshot_path),
            "configuration_validation_sha256": _sha256(config_path),
            "runtime_sha256": runtime["sha256"],
            "worker_immutable_files_sha256": overlay_hashes,
            "structural_bundle_manifest_sha256": _sha256(overlay_manifest_path),
            "structural_bundle_source_commit": overlay_manifest["source_commit"],
            "host_files_sha256": host_hashes,
            "previous_sandbox_wrapper_sha256": previous_wrapper_sha256,
            "real_runner_lineage_fixture_manifest_sha256": lineage_fixture[
                "manifest_sha256"
            ],
            "failed_followup_contract_sha256": old_digest,
            "failed_followup_archive_manifest_sha256": _sha256(OLD_ARCHIVE_MANIFEST),
            "previous_repair_contract_sha256": prior_repair_digest,
            "previous_repair_archive_manifest_sha256": prior_repair_manifest_digest,
            "previous_repair_archive_records_verified": prior_repair_record_count,
            **latest_failed_repair,
            **failed_startup,
            "initial_program_sha256": contract["initialization"]["seed_program_sha256"],
            "native_fixture_bundle_manifest_sha256": fixture[
                "bundle_manifest_sha256"
            ],
        }
    )
    contract["native_fixture_evidence"] = fixture
    contract["real_runner_lineage_fixture_evidence"] = lineage_fixture
    contract["runtime"] = runtime
    contract["stop_rules"].append(
        "verify the fresh G0 seed immediately after run initialization and stop on any mismatch"
    )

    launcher["_validate_repair_contract"](contract, eve_root)
    _write_exclusive(contract_path, contract)
    digest = _sha256(contract_path)
    with contract_path.with_suffix(".sha256").open("x", encoding="ascii") as stream:
        stream.write(f"{digest}  {contract_path.name}\n")
    return {
        "contract": str(contract_path),
        "contract_sha256": digest,
        "protected_archive_records_verified": protected_record_count,
        "previous_repair_archive_records_verified": prior_repair_record_count,
        **latest_failed_repair,
        **failed_startup,
        "native_fixture_run_id": fixture["run_id"],
        "native_fixture_preflight_checks": fixture["preflight_check_count"],
        "native_fixture_checks": fixture["native_check_count"],
        "real_runner_fixture_id": lineage_fixture["run_id"],
        "real_runner_fixture_manifest_sha256": lineage_fixture["manifest_sha256"],
        "runtime_commit": runtime_commit,
        "run_root": str(run_root),
        "configuration_validation_sha256": contract["source_pins"][
            "configuration_validation_sha256"
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--eve-root", type=Path, default=ROOT.parent / "eve")
    parser.add_argument("--runtime-checkout", type=Path, required=True)
    parser.add_argument("--native-evidence", type=Path, required=True)
    parser.add_argument("--lineage-evidence", type=Path, required=True)
    parser.add_argument("--run-root", type=Path, required=True)
    parser.add_argument("--execution-record", type=Path, required=True)
    parser.add_argument("--label", required=True)
    parser.add_argument(
        "--contract",
        type=Path,
        default=ROOT / "V4_FOLLOWUP_REPAIR_CONTRACT_20261015-04.json",
    )
    args = parser.parse_args()
    result = freeze(
        eve_root=args.eve_root,
        runtime_checkout=args.runtime_checkout,
        evidence_root=args.native_evidence,
        lineage_evidence_root=args.lineage_evidence,
        run_root=args.run_root,
        execution_record=args.execution_record,
        label=args.label,
        contract_path=args.contract,
    )
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
