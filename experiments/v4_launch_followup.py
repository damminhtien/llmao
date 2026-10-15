"""Launch the frozen exploratory follow-up and watch protected file boundaries."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import signal
import subprocess
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONTRACT = ROOT / "V4_FOLLOWUP_REPAIR_CONTRACT_20261015-03.json"
PRIOR_REPAIR_CONTRACT = ROOT / "V4_FOLLOWUP_REPAIR_CONTRACT.json"
PRIOR_REPAIR_ARCHIVE_MANIFEST = (
    ROOT / "results/v4/phase10_followup/archive/repair_followup_20261015-01/manifest.json"
)
LATEST_FAILED_REPAIR_CONTRACT = ROOT / "V4_FOLLOWUP_REPAIR_CONTRACT_20261015-02.json"
LATEST_FAILED_REPAIR_ARCHIVE_MANIFEST = (
    ROOT / "results/v4/phase10_followup/archive/repair_followup_20261015-02/manifest.json"
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


def _verify_manifest_records(value: object) -> int:
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


def _verify_latest_failed_repair_artifacts() -> dict:
    contract_digest = _verify_sha256_sidecar(LATEST_FAILED_REPAIR_CONTRACT)
    failed_contract = json.loads(LATEST_FAILED_REPAIR_CONTRACT.read_text())
    archive_digest = _verify_sha256_sidecar(LATEST_FAILED_REPAIR_ARCHIVE_MANIFEST)
    archive_manifest = json.loads(LATEST_FAILED_REPAIR_ARCHIVE_MANIFEST.read_text())
    record_count = _verify_manifest_records(archive_manifest)
    wrapper_digest = failed_contract.get("source_pins", {}).get(
        "host_files_sha256", {}
    ).get("scripts/codex-v4-sandbox")
    if (
        failed_contract.get("phase") != "10_followup_boundary_repair"
        or failed_contract.get("status") != "frozen_before_repair_launch"
        or not isinstance(wrapper_digest, str)
        or archive_manifest.get("phase") != 10
        or archive_manifest.get("pilot_status") != "failed"
        or record_count != 208
    ):
        raise ValueError("latest failed repair contract or archive changed")
    return {
        "latest_failed_repair_contract_sha256": contract_digest,
        "latest_failed_repair_archive_manifest_sha256": archive_digest,
        "latest_failed_repair_archive_records_verified": record_count,
        "latest_failed_repair_wrapper_sha256": wrapper_digest,
    }


def _runtime_snapshot(python_entrypoint: Path) -> dict:
    """Identify the project interpreter, resolved binary, package root, and versions."""
    entrypoint = python_entrypoint.expanduser().absolute()
    probe = subprocess.check_output(
        [
            str(entrypoint),
            "-IB",
            "-c",
            (
                "import json,sys,sysconfig; from importlib.metadata import version; "
                "print(json.dumps({'version':list(sys.version_info[:3]), "
                "'site_packages':sysconfig.get_path('purelib'), 'dependencies':{"
                "name:version(name) for name in "
                "('networkx','numpy','scipy','scikit-image')}}))"
            ),
        ],
        text=True,
    )
    info = json.loads(probe)
    resolved = entrypoint.resolve(strict=True)
    runtime = {
        "project_python_entrypoint": str(entrypoint),
        "entrypoint_is_symlink": entrypoint.is_symlink(),
        "entrypoint_link_target": (
            str(entrypoint.readlink()) if entrypoint.is_symlink() else None
        ),
        "resolved_python_executable": str(resolved),
        "python_executable_sha256": _sha256(resolved),
        "site_packages": str(Path(info["site_packages"]).resolve(strict=True)),
        "python_version": info["version"],
        "dependencies": info["dependencies"],
    }
    canonical = json.dumps(runtime, sort_keys=True, separators=(",", ":"))
    runtime["sha256"] = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return runtime


def _eve_runner_command(eve_root: Path, arguments: list[str]) -> list[str]:
    return [
        str(eve_root / ".venv/bin/python"),
        "-u",
        str(ROOT / "experiments/v4_eve_runner.py"),
        *arguments,
    ]


def _tmux_failure_trace_summary(path: Path) -> dict:
    if path.is_symlink():
        raise ValueError("tmux failure trace may not be a symlink")
    if not path.exists():
        return {
            "path": str(path),
            "exists": False,
            "record_count": 0,
            "sha256": None,
            "records": [],
        }
    if not path.is_file():
        raise ValueError("tmux failure trace must be a regular file")
    records = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid tmux trace JSONL at line {line_number}") from exc
        if not isinstance(record, dict) or not {
            "command",
            "return_code",
            "stdout",
            "stderr",
            "cwd",
            "pane_id",
        }.issubset(record):
            raise ValueError(f"incomplete tmux trace record at line {line_number}")
        if (
            not isinstance(record["command"], list)
            or not all(isinstance(argument, str) for argument in record["command"])
            or not isinstance(record["return_code"], int)
            or any(
                record[key] is not None and not isinstance(record[key], str)
                for key in ("stdout", "stderr")
            )
            or not isinstance(record["cwd"], str)
            or not isinstance(record["pane_id"], str)
        ):
            raise ValueError(f"invalid tmux trace field at line {line_number}")
        records.append(record)
    if not records:
        raise ValueError("tmux failure trace exists but contains no records")
    return {
        "path": str(path),
        "exists": True,
        "record_count": len(records),
        "sha256": _sha256(path),
        "records": records,
    }


def _verify_real_runner_lineage_fixture(
    fixture: dict,
    *,
    expected_wrapper_sha256: str,
) -> dict:
    evidence_root = Path(fixture["directory"]).resolve(strict=True)
    manifest_path = evidence_root / "manifest.json"
    sidecar_path = evidence_root / "manifest.sha256"
    for path in (manifest_path, sidecar_path):
        if path.is_symlink() or not path.is_file():
            raise ValueError("real-runner lineage fixture manifest is missing")
    manifest_sha256 = _sha256(manifest_path)
    if sidecar_path.read_text(encoding="ascii").split()[0] != manifest_sha256:
        raise ValueError("real-runner lineage fixture manifest digest mismatch")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("schema_version") != 1 or manifest.get("status") != "passed":
        raise ValueError("real-runner lineage fixture manifest is not a passing fixture")
    files = manifest.get("files")
    if not isinstance(files, dict) or not files:
        raise ValueError("real-runner lineage fixture manifest has no files")
    files_sha256 = {}
    for relative, record in files.items():
        path = evidence_root / relative
        resolved = path.resolve(strict=False)
        if (
            Path(relative).is_absolute()
            or ".." in Path(relative).parts
            or not resolved.is_relative_to(evidence_root)
            or path.is_symlink()
            or not path.is_file()
            or _sha256(path) != record.get("sha256")
            or path.stat().st_size != record.get("size_bytes")
        ):
            raise ValueError(f"real-runner fixture evidence changed: {relative}")
        files_sha256[relative] = record["sha256"]
    actual_files = {
        path.relative_to(evidence_root).as_posix()
        for path in evidence_root.rglob("*")
        if path.is_file() and path.name not in {"manifest.json", "manifest.sha256"}
    }
    if actual_files != set(files):
        raise ValueError("real-runner fixture evidence inventory changed")
    result_path = evidence_root / "result.json"
    if "result.json" not in files:
        raise ValueError("real-runner fixture result is not manifested")
    result = json.loads(result_path.read_text(encoding="utf-8"))
    required_checks = {
        "candidate_language_unchanged_except_parent",
        "candidate_parent_matches_selected_language_hash",
        "candidate_program_unchanged",
        "real_context_builder_recorded_lineage",
        "real_context_builder_validated_candidate",
        "selected_prefill_rendered_in_readme",
        "selected_state_read_from_evE_workspace",
    }
    checks = result.get("candidate_validation", {}).get("checks", {})
    if (
        result.get("status") != "passed"
        or manifest.get("run_id") != result.get("run_id")
        or result.get("scope")
        != "data-free Phase2Runner integration; evaluator context only; no dataset scoring"
        or not required_checks.issubset(checks)
        or not all(checks[name] is True for name in required_checks)
        or result.get("candidate_parent_language_hash")
        != result.get("selected_language_hash")
        or result.get("sandbox_wrapper_sha256") != expected_wrapper_sha256
    ):
        raise ValueError("real-runner lineage fixture did not pass its gates")
    rollout = result.get("native_rollout", {})
    transcript_relative = Path(rollout.get("transcript", ""))
    transcript_path = (evidence_root / transcript_relative).resolve(strict=False)
    if (
        transcript_relative.is_absolute()
        or ".." in transcript_relative.parts
        or not transcript_path.is_relative_to(evidence_root)
        or transcript_path.is_symlink()
        or not transcript_path.is_file()
        or files_sha256.get(transcript_relative.as_posix())
        != rollout.get("transcript_sha256")
        or _sha256(transcript_path) != rollout.get("transcript_sha256")
    ):
        raise ValueError("real-runner fixture transcript is missing or unpinned")
    completed = False
    for line in transcript_path.read_text(encoding="utf-8").splitlines():
        item = json.loads(line)
        payload = item.get("payload")
        if (
            item.get("type") == "event_msg"
            and isinstance(payload, dict)
            and payload.get("type") == "task_complete"
        ):
            completed = True
            break
    if not completed:
        raise ValueError("real-runner fixture transcript has no task-complete event")
    preflight = result.get("workspace_preflight", {}).get(
        "sandbox_profile_preflight", {}
    )
    expected_permission_checks = {
        "solver/candidate/language.json": True,
        "solver/candidate/program.json": True,
    }
    if (
        result.get("workspace_preflight", {}).get("passed") is not True
        or preflight.get("passed") is not True
        or preflight.get("checks") != expected_permission_checks
    ):
        raise ValueError("real-runner language-only sandbox preflight failed")
    failures = rollout.get("tmux_failures")
    if not isinstance(failures, list):
        raise TypeError("real-runner fixture tmux failures are malformed")
    required_failure_fields = {
        "command",
        "return_code",
        "stdout",
        "stderr",
        "cwd",
        "pane_id",
    }
    if any(
        not isinstance(failure, dict)
        or not required_failure_fields.issubset(failure)
        for failure in failures
    ):
        raise ValueError("real-runner fixture omitted tmux failure details")
    probe_path = evidence_root / "tmux_failure_probe.json"
    probe_trace = evidence_root / "tmux_failure_probe.jsonl"
    if not {"tmux_failure_probe.json", "tmux_failure_probe.jsonl"}.issubset(files):
        raise ValueError("real-runner fixture omitted its tmux capture probe")
    probe = json.loads(probe_path.read_text(encoding="utf-8"))
    probe_record = json.loads(probe_trace.read_text(encoding="utf-8").splitlines()[0])
    if (
        probe.get("passed") is not True
        or probe.get("failure") != probe_record
        or probe_record.get("return_code") != 37
        or "fixture stdout marker" not in (probe_record.get("stdout") or "")
        or "fixture stderr marker" not in (probe_record.get("stderr") or "")
    ):
        raise ValueError("tmux capture probe did not retain exact subprocess output")
    return {
        "run_id": result["run_id"],
        "directory": str(evidence_root),
        "manifest_sha256": manifest_sha256,
        "files_sha256": files_sha256,
        "sandbox_wrapper_sha256": expected_wrapper_sha256,
        "selected_language_hash": result["selected_language_hash"],
        "candidate_parent_language_hash": result["candidate_parent_language_hash"],
        "transcript": transcript_relative.as_posix(),
        "transcript_sha256": rollout["transcript_sha256"],
        "preflight_checks": len(preflight["checks"]),
        "tmux_failure_probe": probe_record,
    }


def _git(checkout: Path, *arguments: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(checkout), *arguments],
        text=True,
    ).strip()


def _has_command_pair(command: list[str], option: str, value: str) -> bool:
    return any(
        command[index] == option and command[index + 1] == value
        for index in range(len(command) - 1)
    )


def _validate_repair_contract(contract: dict, eve_root: Path) -> None:
    """Verify the independent repair contract, fixture, launcher, and G0 seed."""
    schema_version = contract.get("schema_version")
    if (
        schema_version not in {3, 4}
        or contract.get("phase") != "10_followup_boundary_repair"
        or contract.get("status") != "frozen_before_repair_launch"
    ):
        raise ValueError("launch requires a separately frozen repair contract")

    source_pins = contract["source_pins"]
    for relative, expected in source_pins["host_files_sha256"].items():
        candidate = ROOT / relative
        path = candidate.resolve()
        if (
            not path.is_relative_to(ROOT.resolve())
            or candidate.is_symlink()
            or not path.is_file()
        ):
            raise ValueError(f"pinned host source is missing or unsafe: {relative}")
        if _sha256(path) != expected:
            raise ValueError(f"pinned host source changed: {relative}")

    prior_repair_digest = _verify_sha256_sidecar(PRIOR_REPAIR_CONTRACT)
    prior_repair_manifest_digest = _verify_sha256_sidecar(
        PRIOR_REPAIR_ARCHIVE_MANIFEST
    )
    prior_repair_manifest = json.loads(PRIOR_REPAIR_ARCHIVE_MANIFEST.read_text())
    prior_repair_record_count = _verify_manifest_records(prior_repair_manifest)
    if (
        source_pins.get("previous_repair_contract_sha256") != prior_repair_digest
        or source_pins.get("previous_repair_archive_manifest_sha256")
        != prior_repair_manifest_digest
        or source_pins.get("previous_repair_archive_records_verified")
        != prior_repair_record_count
        or prior_repair_record_count != 211
        or prior_repair_manifest.get("phase") != 10
        or prior_repair_manifest.get("pilot_status") != "failed"
    ):
        raise ValueError("the previous failed repair archive no longer matches its pins")

    prompt_path = str((ROOT / "configs/v4/phase10_followup_worker.md").resolve())
    wrapper_path = str((ROOT / "scripts/codex-v4-sandbox").resolve())
    launch = contract["launch"]
    driver = contract["driver"]
    account = contract["account"]
    budget = contract["budget"]
    initialization = contract["initialization"]
    if schema_version == 4:
        latest_failed_repair = _verify_latest_failed_repair_artifacts()
        if any(
            source_pins.get(key) != value
            for key, value in latest_failed_repair.items()
        ):
            raise ValueError("latest failed repair archive no longer matches its pins")
        required_runner_sources = {
            "experiments/v4_eve_runner.py",
            "experiments/v4_tmux_failure_capture.py",
            "experiments/v4_eve_lineage_fixture.py",
        }
        requirements = contract.get("artifact_requirements", [])
        if (
            not required_runner_sources.issubset(source_pins["host_files_sha256"])
            or any(
                "account snapshot" in str(requirement).lower()
                or "usage snapshot" in str(requirement).lower()
                for requirement in requirements
            )
        ):
            raise ValueError(
                "repair contract must pin transcript capture without account usage snapshots"
            )
        runner_entrypoint = str((ROOT / "experiments/v4_eve_runner.py").resolve())
        expected_trace = str(Path(launch["run_root"]) / "tmux_failures.jsonl")
        if (
            launch.get("runner_entrypoint") != runner_entrypoint
            or launch.get("tmux_failure_trace") != expected_trace
        ):
            raise ValueError("repair contract does not pin the failure-capture runner")
    if (
        account.get("required_plan") != "ChatGPT Plus"
        or "verify_before_worker_launch" in account
        or account.get("use_ordinary_codex_allowance_only") is not True
        or account.get("use_paid_credits") is not False
        or account.get("use_rate_limit_resets") is not False
        or account.get("stop_on_ordinary_rate_limit") is not True
    ):
        raise ValueError("repair contract must retain its declared account restrictions")
    if (
        budget.get("submitted_proposals") != 10
        or budget.get("replacement_proposals") != 0
        or budget.get("workers") != 1
        or budget.get("parallel_workers") != 1
    ):
        raise ValueError("repair contract changed the original proposal budget")
    if (
        initialization.get("resume_previous_run") is not False
        or initialization.get("import_prior_program") is not False
        or initialization.get("import_prior_macros") is not False
        or initialization.get("import_prior_guidance_state") is not False
        or initialization.get("import_prior_population") is not False
        or initialization.get("import_prior_winner") is not False
    ):
        raise ValueError("repair contract must start from fresh G0 state")
    gates = contract["gates"]
    if (
        gates.get("minimum_valid_stage_one_proposals") != 8
        or gates.get("minimum_distinct_valid_expanded_program_hashes") != 8
        or gates.get("at_least_one_macro_used_by_descendant") is not True
        or gates.get("maximum_protected_boundary_violations") != 0
    ):
        raise ValueError("repair contract changed the original validity gates")
    if driver.get("executable") != wrapper_path:
        raise ValueError("repair contract must route Codex through the pinned wrapper")
    if driver.get("system_prompt_file") != prompt_path:
        raise ValueError("repair contract must use the pinned worker instructions")
    if driver.get("sandbox_profile") != "llmao-v4-workspace-only":
        raise ValueError("repair contract must pin the workspace-only profile")
    if (
        driver.get("driver") != "codex_tmux"
        or driver.get("allow_network") is not False
        or driver.get("web_search") != "disabled"
        or driver.get("enable_multi_agent") is not False
    ):
        raise ValueError("repair worker configuration weakens the required policy")
    required_overrides = {
        f"driver.executable={wrapper_path}",
        f"driver.system_prompt_file={prompt_path}",
        "driver.allow_network=false",
        "driver.web_search=disabled",
        "driver.enable_multi_agent=false",
        f"optimizer.workers.items.0.immutable={launch['immutable_overlay']}",
    }
    if not required_overrides.issubset(set(launch["hydra_arguments"])):
        raise ValueError("repair launch arguments do not match the pinned policy")
    configuration_path = Path(launch["configuration_validation"])
    if (
        configuration_path.is_symlink()
        or not configuration_path.is_file()
        or _sha256(configuration_path)
        != source_pins["configuration_validation_sha256"]
    ):
        raise ValueError("resolved launch configuration differs from its contract pin")
    configuration = json.loads(configuration_path.read_text())
    resolved_config = configuration.get("resolved_config", "")
    if (
        configuration.get("status") != "resolved_without_worker_launch"
        or configuration.get("command_arguments") != launch["hydra_arguments"]
        or hashlib.sha256(resolved_config.encode()).hexdigest()
        != configuration.get("resolved_config_sha256")
    ):
        raise ValueError("resolved launch configuration is incomplete or inconsistent")
    snapshot_path = Path(launch["evaluator_source_snapshot"])
    if (
        snapshot_path.is_symlink()
        or not snapshot_path.is_file()
        or _sha256(snapshot_path)
        != source_pins["evaluator_source_snapshot_file_sha256"]
    ):
        raise ValueError("evaluator source snapshot differs from its contract pin")
    snapshot = json.loads(snapshot_path.read_text())
    if snapshot.get("sha256") != source_pins["evaluator_source_sha256"]:
        raise ValueError("evaluator runtime digest differs from its source snapshot")
    runtime = _runtime_snapshot(Path(launch["python"]))
    if runtime != contract["runtime"] or runtime["sha256"] != source_pins[
        "runtime_sha256"
    ]:
        raise ValueError("project Python runtime differs from its contract pin")
    overlay_path = Path(launch["immutable_overlay"])
    if overlay_path.is_symlink():
        raise ValueError("repair worker immutable overlay may not be a symlink")
    overlay = overlay_path.resolve()
    if not overlay.is_relative_to(ROOT.resolve()) or not overlay.is_dir():
        raise ValueError("repair worker immutable overlay is missing or unsafe")
    expected_overlay = source_pins["worker_immutable_files_sha256"]
    if any(path.is_symlink() for path in overlay.rglob("*")):
        raise ValueError("repair worker immutable overlay contains a symlink")
    actual_overlay = {
        path.relative_to(overlay).as_posix()
        for path in overlay.rglob("*")
        if path.is_file()
    }
    if actual_overlay != set(expected_overlay):
        raise ValueError("repair worker immutable overlay inventory changed")
    for relative, expected in expected_overlay.items():
        path = overlay / relative
        if path.is_symlink() or _sha256(path) != expected:
            raise ValueError(f"repair worker immutable file changed: {relative}")
    structural_manifest_path = overlay / "structural_check/manifest.json"
    structural_manifest = json.loads(structural_manifest_path.read_text())
    if (
        _sha256(structural_manifest_path)
        != source_pins["structural_bundle_manifest_sha256"]
        or structural_manifest.get("source_commit")
        != source_pins["structural_bundle_source_commit"]
        or structural_manifest.get("python_executable")
        != runtime["project_python_entrypoint"]
        or structural_manifest.get("launcher_python_executable")
        != runtime["resolved_python_executable"]
        or structural_manifest.get("python_site_packages") != runtime["site_packages"]
        or structural_manifest.get("python_runtime", {}).get("version")
        != runtime["python_version"]
        or structural_manifest.get("python_runtime", {}).get("dependencies")
        != runtime["dependencies"]
    ):
        raise ValueError("worker bundle does not pin the current project runtime")

    fixture = contract["native_fixture_evidence"]
    if fixture.get("worker_prompt_source_sha256") != source_pins[
        "host_files_sha256"
    ].get("configs/v4/native_fixture_worker.md"):
        raise ValueError("native fixture worker prompt source differs from its pin")
    evidence_root = Path(fixture["directory"])
    evidence_paths = {
        name: evidence_root / name for name in fixture["files_sha256"]
    }
    for name, path in evidence_paths.items():
        if path.is_symlink() or not path.is_file():
            raise ValueError(f"native fixture evidence is missing: {name}")
        if _sha256(path) != fixture["files_sha256"][name]:
            raise ValueError(f"native fixture evidence changed: {name}")
    result = json.loads(evidence_paths["result.json"].read_text())
    preflight = json.loads(evidence_paths["sandbox_preflight.json"].read_text())
    structural_manifest = json.loads(
        evidence_paths["structural_check/manifest.json"].read_text()
    )
    if result.get("run_id") != fixture["run_id"]:
        raise ValueError("native fixture run ID does not match the contract")
    if (
        preflight.get("permission_profile") != "llmao-v4-workspace-only"
        or preflight.get("passed") is not True
        or not preflight.get("checks")
        or not all(preflight["checks"].values())
        or len(preflight["checks"]) != 21
        or result.get("sandbox_preflight", {}).get("checks") != preflight["checks"]
        or result.get("preflight", {}).get("bundle_manifest_sha256")
        != preflight.get("bundle_manifest_sha256")
        or _sha256(evidence_paths["structural_check/manifest.json"])
        != preflight.get("bundle_manifest_sha256")
    ):
        raise ValueError("native sandbox preflight did not pass every check")
    wrapper_digest = source_pins["host_files_sha256"]["scripts/codex-v4-sandbox"]
    if schema_version == 3:
        if preflight.get("wrapper_sha256") != wrapper_digest:
            raise ValueError("native preflight did not exercise the pinned launcher")
    else:
        previous_wrapper_digest = source_pins.get(
            "previous_sandbox_wrapper_sha256"
        )
        if (
            fixture.get("wrapper_sha256") != previous_wrapper_digest
            or preflight.get("wrapper_sha256") != previous_wrapper_digest
        ):
            raise ValueError("historical native fixture no longer matches its wrapper pin")
        lineage_fixture = contract.get("real_runner_lineage_fixture_evidence")
        if not isinstance(lineage_fixture, dict):
            raise ValueError("repair contract omitted the real-runner lineage fixture")
        verified_lineage_fixture = _verify_real_runner_lineage_fixture(
            lineage_fixture,
            expected_wrapper_sha256=wrapper_digest,
        )
        if verified_lineage_fixture != lineage_fixture:
            raise ValueError("real-runner lineage fixture differs from its contract pin")
    if preflight.get("command", [None])[0] != wrapper_path:
        raise ValueError("native preflight did not use the pinned sandbox wrapper")
    native_checks = result.get("native_check_verification", {})
    if (
        native_checks.get("passed") is not True
        or not native_checks.get("checks")
        or not all(native_checks["checks"].values())
        or result.get("native_changed_paths") != []
        or result.get("git_status_after") != ""
        or result.get("candidate_contents_unchanged") is not True
    ):
        raise ValueError("native worker verification or workspace audit failed")
    invocations = result.get("native_invocations")
    lifecycle = result.get("native_run_lifecycle")
    session_cleanup = lifecycle.get("session_cleanup") if isinstance(lifecycle, dict) else None
    transcript_names = {
        name
        for name in fixture["files_sha256"]
        if name.startswith("native_transcripts/") and name.endswith(".jsonl")
    }
    if (
        not isinstance(invocations, list)
        or len(invocations) != 2
        or not isinstance(lifecycle, dict)
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
        raise ValueError("native fixture does not prove two sequential driver launches")
    reported_transcripts = set()
    for expected_number, invocation in enumerate(invocations, start=1):
        name = invocation.get("transcript")
        reported_transcripts.add(name)
        execution = invocation.get("native_driver_execution", {})
        command = execution.get("command") if isinstance(execution, dict) else None
        system_prompt = lifecycle.get("system_prompt_file")
        workspace_path = str(Path(result["workspace"]).resolve())
        if (
            invocation.get("invocation") != expected_number
            or invocation.get("status") != "completed"
            or invocation.get("pane_id") != lifecycle.get("pane_id")
            or invocation.get("pane_id_before") != lifecycle.get("pane_id")
            or invocation.get("pane_id_after") != lifecycle.get("pane_id")
            or invocation.get("verification", {}).get("passed") is not True
            or not all(
                invocation.get("verification", {}).get("checks", {}).values()
            )
            or not isinstance(name, str)
            or name not in transcript_names
            or fixture["files_sha256"].get(name)
            != invocation.get("transcript_sha256")
            or not isinstance(command, list)
            or not command
            or not all(isinstance(argument, str) for argument in command)
            or command[0] != wrapper_path
            or system_prompt
            != str(Path(workspace_path) / "native_system_prompt.md")
            or not _has_command_pair(command, "-s", "workspace-write")
            or not _has_command_pair(command, "-C", workspace_path)
            or not any(
                isinstance(argument, str)
                and "model_instructions_file=" in argument
                and isinstance(system_prompt, str)
                and system_prompt in argument
                for argument in command
            )
        ):
            raise ValueError(
                "native fixture transcript, pane reuse, or sandbox command changed"
            )
    if reported_transcripts != transcript_names or len(transcript_names) != 2:
        raise ValueError("native fixture must pin one transcript per invocation")
    runtime = contract["runtime"]
    if (
        fixture.get("runtime_sha256") != runtime.get("sha256")
        or structural_manifest.get("python_executable")
        != runtime.get("project_python_entrypoint")
        or structural_manifest.get("launcher_python_executable")
        != runtime.get("resolved_python_executable")
        or structural_manifest.get("python_site_packages") != runtime.get("site_packages")
        or structural_manifest.get("python_runtime", {}).get("version")
        != runtime.get("python_version")
        or structural_manifest.get("python_runtime", {}).get("dependencies")
        != runtime.get("dependencies")
    ):
        raise ValueError("native fixture runtime differs from the pinned checker runtime")

    seed_files = initialization["seed_files_sha256"]
    for relative, expected in seed_files.items():
        candidate = eve_root / relative
        path = candidate.resolve()
        if not path.is_relative_to(eve_root.resolve()) or candidate.is_symlink():
            raise ValueError(f"G0 seed path is unsafe: {relative}")
        if _sha256(path) != expected:
            raise ValueError(f"fresh G0 seed changed: {relative}")
    language_path = eve_root / next(
        relative for relative in seed_files if relative.endswith("/language.json")
    )
    language = json.loads(language_path.read_text())
    if language.get("macros") != [] or language.get("introduced_macros") != []:
        raise ValueError("repair pilot must initialize from macro-free G0")
    if language.get("base_language_hash") != language.get("parent_language_hash"):
        raise ValueError("fresh G0 seed must have no prior language parent")


def _initial_seed_violation(run_root: Path, initialization: dict) -> str | None:
    """Stop if EvE materializes a starting candidate other than the pinned G0."""
    workspaces = run_root / "evaluation_workspaces"
    if not workspaces.is_dir():
        return None
    seeds = list(workspaces.glob("*_seed"))
    if not seeds:
        return None
    if len(seeds) != 1:
        return "repair run did not initialize exactly one fresh G0 seed"
    expected = {
        Path(relative).name: digest
        for relative, digest in initialization["seed_files_sha256"].items()
        if relative.endswith(("/language.json", "/program.json"))
    }
    candidate_dir = seeds[0] / "solver/candidate"
    paths = {name: candidate_dir / name for name in expected}
    if not all(path.is_file() for path in paths.values()):
        return None
    if any(
        path.is_symlink() or _sha256(path) != expected[name]
        for name, path in paths.items()
    ):
        return "repair run seed differs from the pinned fresh G0 candidate"
    return None


def _boundary_violation(
    run_root: Path, manifest_digest: str, seen: set[Path]
) -> str | None:
    if any(run_root.rglob("forbidden_changes.txt")):
        return "EvE recorded a forbidden workspace change"
    workspaces = run_root / "solver_workspaces"
    bundles = set(seen)
    if workspaces.is_dir():
        bundles.update(
            workspace / "structural_check"
            for workspace in workspaces.iterdir()
            if (workspace / ".scaling_evolve/worker.yaml").is_file()
        )
    for bundle in bundles:
        manifest = bundle / "manifest.json"
        if bundle.is_symlink() or manifest.is_symlink() or not manifest.is_file():
            return "worker removed or replaced the pinned structural manifest"
        if hashlib.sha256(manifest.read_bytes()).hexdigest() != manifest_digest:
            return "worker changed the pinned structural manifest"
        files = json.loads(manifest.read_text())["files"]
        seen.add(bundle)
        inventory = {
            str(path.relative_to(bundle))
            for path in bundle.rglob("*")
            if path.is_file()
        }
        if inventory != set(files) | {"manifest.json"}:
            return "worker changed the pinned structural file inventory"
        for path, record in files.items():
            source = bundle / path
            if (
                source.is_symlink()
                or not source.is_file()
                or hashlib.sha256(source.read_bytes()).hexdigest() != record["sha256"]
            ):
                return "worker changed a pinned structural source or protocol"
    return None


def _stop_runner(process: subprocess.Popen) -> int:
    """Stop only the owned process group, allowing EvE to clean up its workers."""
    for sig, timeout in ((signal.SIGINT, 10), (signal.SIGTERM, 5), (signal.SIGKILL, 2)):
        if process.poll() is not None:
            return process.returncode
        os.killpg(process.pid, sig)
        try:
            return process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            continue
    raise RuntimeError("owned runner did not terminate")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--contract", type=Path, default=DEFAULT_CONTRACT
    )
    parser.add_argument("--record", type=Path, required=True)
    parser.add_argument("--eve-root", type=Path, default=ROOT.parent / "eve")
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()
    content = args.contract.read_bytes()
    digest = hashlib.sha256(content).hexdigest()
    if digest != args.contract.with_suffix(".sha256").read_text().split()[0]:
        raise ValueError("follow-up contract digest mismatch")
    contract = json.loads(content)
    eve_root = args.eve_root.resolve(strict=True)
    _validate_repair_contract(contract, eve_root)
    launch = contract["launch"]
    checkout = Path(launch["evaluator_checkout"])
    for path, expected in (
        (eve_root, contract["source_pins"]["eve_commit"]),
        (checkout, contract["source_pins"]["llmao_runtime_commit"]),
    ):
        if _git(path, "rev-parse", "HEAD") != expected or _git(
            path, "status", "--porcelain", "--untracked-files=all"
        ):
            raise ValueError(
                f"pinned checkout must be clean at its declared commit: {path}"
            )
    for relative, expected in contract["eve_file_sha256"].items():
        if (
            hashlib.sha256((args.eve_root / relative).read_bytes()).hexdigest()
            != expected
        ):
            raise ValueError(f"pinned EvE file changed: {relative}")
    if (
        hashlib.sha256((checkout / "results/v4/protocol.json").read_bytes()).hexdigest()
        != contract["source_pins"]["base_protocol_sha256"]
    ):
        raise ValueError("runtime protocol digest mismatch")
    run_root = Path(launch["run_root"])
    if run_root.exists() or args.record.exists():
        raise ValueError("new follow-up requires unused run and execution-record paths")
    if args.validate_only:
        print(
            json.dumps({"status": "validated_before_launch", "contract_sha256": digest})
        )
        return 0
    if contract.get("schema_version") != 4:
        raise ValueError("legacy repair contracts cannot be launched by the traced runner")
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
            "LLMAO_PROJECT_ROOT": str(checkout),
            "LLMAO_EXPECTED_COMMIT": contract["source_pins"]["llmao_runtime_commit"],
            "LLMAO_PYTHON": launch["python"],
            "LLMAO_DATA_DIR": launch["data_dir"],
            "LLMAO_EVE_SOURCE_ROOT": str((eve_root / "src").resolve(strict=True)),
            "LLMAO_V4_TMUX_TRACE_PATH": launch["tmux_failure_trace"],
            "LLMAO_V4_FIXTURE_LANGUAGE_ONLY": "0",
        }
    )
    command = _eve_runner_command(eve_root, launch["hydra_arguments"])
    args.record.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "status": "launching",
        "contract_sha256": digest,
        "run_root": str(run_root),
        "command": command,
    }
    with args.record.open("x") as stream:
        json.dump(record, stream, indent=2, sort_keys=True, allow_nan=False)
    process = subprocess.Popen(
        command, cwd=eve_root, env=environment, start_new_session=True
    )
    record.update(
        status="running",
        runner_pid=process.pid,
        started_at_utc=datetime.now(UTC).isoformat(),
    )
    args.record.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
    print(
        json.dumps({"runner_pid": process.pid, "run_root": str(run_root)}), flush=True
    )
    seen: set[Path] = set()
    try:
        while True:
            try:
                code = process.wait(timeout=5)
                break
            except subprocess.TimeoutExpired:
                violation = _boundary_violation(
                    run_root,
                    contract["source_pins"]["structural_bundle_manifest_sha256"],
                    seen,
                )
                if violation is None:
                    violation = _initial_seed_violation(
                        run_root, contract["initialization"]
                    )
                if violation:
                    record["stop_reason"] = violation
                    code = _stop_runner(process)
                    break
    except BaseException:
        record.setdefault("stop_reason", "supervision interrupted")
        if process.poll() is None:
            _stop_runner(process)
        raise
    finally:
        try:
            record["tmux_failure_trace"] = _tmux_failure_trace_summary(
                Path(launch["tmux_failure_trace"])
            )
        except (OSError, TypeError, ValueError) as exc:
            record["tmux_failure_trace_error"] = f"{type(exc).__name__}: {exc}"
            record.setdefault("stop_reason", "tmux failure trace was invalid")
        record.update(
            status="stopped" if record.get("stop_reason") else "runner_exited",
            exit_code=process.poll(),
            finished_at_utc=datetime.now(UTC).isoformat(),
            structural_bundles_observed=len(seen),
        )
        args.record.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
    return code if code else (1 if record.get("stop_reason") else 0)


if __name__ == "__main__":
    raise SystemExit(main())
