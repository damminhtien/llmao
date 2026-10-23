"""Freeze a seed-specific launch contract for V4 Phase 12."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path

if __package__:
    from .v4_artifact_paths import resolve_v4_output_path, v4_repo_relative_path
    from .v4_primary_contract import (
        EVE_ROOT,
        ROOT,
        git_value,
        optional_sha256_file,
        primary_run_root,
        sha256_file,
        tracked_tree_is_clean,
        venv_python_path,
        verify_source_paths,
    )
else:
    from v4_artifact_paths import resolve_v4_output_path, v4_repo_relative_path
    from v4_primary_contract import (
        EVE_ROOT,
        ROOT,
        git_value,
        optional_sha256_file,
        primary_run_root,
        sha256_file,
        tracked_tree_is_clean,
        venv_python_path,
        verify_source_paths,
    )


def _command_output(*args: str) -> str:
    result = subprocess.run(args, check=True, capture_output=True, text=True)
    return result.stdout.strip()


def _evidence(
    path: Path, *, label: str, repo_relative_paths: bool = False
) -> dict[str, str]:
    resolved = resolve_v4_output_path(path, repo_root=ROOT).resolve(strict=True)
    payload = json.loads(resolved.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TypeError(f"{label} evidence must be a JSON object")
    if payload.get("passed") is not True and payload.get("status") != "passed":
        raise ValueError(f"{label} evidence did not pass")
    record_path = (
        v4_repo_relative_path(resolved, repo_root=ROOT)
        if repo_relative_paths
        else str(resolved)
    )
    record = {"path": record_path, "sha256": sha256_file(resolved)}
    if label == "native fixture":
        manifest_path = resolved.parent / "manifest.json"
        manifest_sidecar = resolved.parent / "manifest.sha256"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        fields = manifest_sidecar.read_text(encoding="ascii").split()
        manifest_digest = sha256_file(manifest_path)
        if not fields or fields[0] != manifest_digest:
            raise ValueError("native fixture manifest digest does not verify")
        if manifest.get("status") != "passed":
            raise ValueError("native fixture manifest is not marked passed")
        for relative, item in manifest.get("files", {}).items():
            artifact = (resolved.parent / relative).resolve(strict=True)
            if resolved.parent.resolve() not in artifact.parents:
                raise ValueError(f"native fixture manifest path escapes its root: {relative}")
            if sha256_file(artifact) != item.get("sha256"):
                raise ValueError(f"native fixture artifact changed: {relative}")
        record["manifest_path"] = (
            v4_repo_relative_path(manifest_path, repo_root=ROOT)
            if repo_relative_paths
            else str(manifest_path)
        )
        record["manifest_sha256"] = manifest_digest
    return record


def freeze_contract(
    *,
    seed: int,
    protocol_path: Path,
    checker_bundle: Path,
    preflight_evidence: Path,
    native_fixture: Path,
    output: Path,
) -> dict[str, str | int]:
    protocol_path = resolve_v4_output_path(protocol_path, repo_root=ROOT).resolve(strict=True)
    protocol_raw = protocol_path.read_bytes()
    protocol_sha256 = hashlib.sha256(protocol_raw).hexdigest()
    protocol = json.loads(protocol_raw)
    if protocol.get("status") != "finalized_primary":
        raise ValueError("cannot freeze a contract against a draft protocol")
    design = protocol["primary_discovery"]
    schema_version = 2 if protocol.get("storage_layout", {}).get("version") == 2 else 1
    if schema_version == 2 and protocol.get("primary_fresh_search", {}).get("run_count") != 20:
        raise ValueError("storage-layout v2 contracts require the reduced V11 search matrix")
    if seed not in design["discovery_seeds"]:
        raise ValueError("seed is not preregistered for Phase 12")
    initial_digest = sha256_file(ROOT / "configs/v4/V4_INITIAL_PROGRAMS.json")
    if initial_digest != design["initial_programs_sha256"]:
        raise ValueError("common initial-program digest differs from the protocol")

    llmao_commit = git_value(ROOT, "rev-parse", "HEAD")
    if not tracked_tree_is_clean(ROOT):
        raise SystemExit("tracked LLMAO source files must be clean before contract freeze")
    eve_commit = git_value(EVE_ROOT, "rev-parse", "HEAD")
    if eve_commit != protocol["implementation_pins"]["eve_commit"]:
        raise ValueError("EvE checkout commit differs from the finalized protocol")
    if git_value(EVE_ROOT, "status", "--porcelain", "--untracked-files=all"):
        raise SystemExit("EvE checkout must be clean before contract freeze")
    if llmao_commit != protocol["implementation_pins"]["llmao_commit"]:
        raise ValueError("LLMAO checkout commit differs from the finalized protocol")
    verify_source_paths(ROOT, protocol["source_pins"])

    bundle = resolve_v4_output_path(checker_bundle, repo_root=ROOT).resolve(strict=True)
    bundle_manifest_path = bundle / "manifest.json"
    bundle_manifest = json.loads(bundle_manifest_path.read_text(encoding="utf-8"))
    if bundle_manifest.get("source_commit") != llmao_commit:
        raise ValueError("checker bundle was built from a different LLMAO commit")
    if bundle_manifest.get("protocol_sha256") != protocol_sha256:
        raise ValueError("checker bundle embeds a different protocol digest")
    sandbox = _evidence(
        preflight_evidence,
        label="sandbox preflight",
        repo_relative_paths=schema_version == 2,
    )
    fixture = _evidence(
        native_fixture,
        label="native fixture",
        repo_relative_paths=schema_version == 2,
    )
    sandbox_path = resolve_v4_output_path(sandbox["path"], repo_root=ROOT)
    fixture_path = resolve_v4_output_path(fixture["path"], repo_root=ROOT)
    sandbox_payload = json.loads(sandbox_path.read_text(encoding="utf-8"))
    expected_preflight_checks = 22 if schema_version == 2 else 21
    if (
        len(sandbox_payload.get("checks", {})) != expected_preflight_checks
        or not all(sandbox_payload["checks"].values())
        or (
            schema_version == 2
            and sandbox_payload["checks"].get("mnist_cache_read_denied") is not True
        )
    ):
        raise ValueError(
            f"primary contract requires the complete {expected_preflight_checks}-check sandbox preflight"
        )
    expected_cache: Path | None = None
    if schema_version == 2:
        expected_cache = resolve_v4_output_path(
            protocol["storage_layout"]["mnist_cache"], repo_root=ROOT
        )
        if resolve_v4_output_path(
            sandbox_payload.get("mnist_cache_path", ""), repo_root=ROOT
        ) != expected_cache:
            raise ValueError("sandbox preflight did not probe the contracted MNIST cache")
    fixture_payload = json.loads(fixture_path.read_text(encoding="utf-8"))
    lineage = fixture_payload.get("candidate_validation", {})
    workspace_preflight = fixture_payload.get("workspace_preflight", {})
    transcript = fixture_payload.get("native_rollout", {}).get("transcript")
    transcript_path = fixture_path.parent / str(transcript)
    if (
        lineage.get("status") != "passed"
        or not all(lineage.get("checks", {}).values())
        or workspace_preflight.get("passed") is not True
        or workspace_preflight.get("sandbox_profile_preflight", {}).get("passed") is not True
        or not transcript_path.is_file()
        or sha256_file(transcript_path)
        != fixture_payload.get("native_rollout", {}).get("transcript_sha256")
        or fixture_payload.get("tmux_session", {}).get("cleanup_return_code") != 0
    ):
        raise ValueError("primary native fixture is missing a passing lineage, sandbox, transcript, or cleanup check")
    # The standalone OS-level preflight probes the cache canary before the
    # native worker starts. The EvE lineage fixture separately checks its
    # narrower candidate-file permissions inside the actual worker workspace.
    if (
        sandbox_payload.get("bundle_manifest_sha256") != sha256_file(bundle_manifest_path)
        or fixture_payload.get("checker_bundle_manifest_sha256")
        != sha256_file(bundle_manifest_path)
        or fixture_payload.get("protocol_sha256") != protocol_sha256
    ):
        raise ValueError("sandbox or native fixture did not use the primary checker bundle")
    if fixture_payload.get("eve_commit") != eve_commit:
        raise ValueError("native fixture uses a different EvE commit")
    wrapper_sha256 = sha256_file(ROOT / "scripts/codex-v4-sandbox")
    if fixture_payload.get("sandbox_wrapper_sha256") != wrapper_sha256:
        raise ValueError("native fixture used a different sandbox wrapper")
    if fixture_payload.get("system_prompt_file") != str(
        (ROOT / "configs/v4/phase12_primary_worker.md").resolve()
    ):
        raise ValueError("native fixture did not exercise the primary worker prompt")
    if sandbox_payload.get("wrapper_sha256") != wrapper_sha256:
        raise ValueError("sandbox preflight used a different wrapper revision")

    python = venv_python_path(ROOT)
    eve_python = venv_python_path(EVE_ROOT)
    codex = _command_output("which", "codex")
    codex_version = _command_output(codex, "--version")
    runtime = {
        "llmao_python": str(python),
        "llmao_python_version": _command_output(str(python), "--version"),
        "eve_python": str(eve_python),
        "eve_python_version": _command_output(str(eve_python), "--version"),
        "codex_executable": codex,
        "codex_cli_version": codex_version,
        "tmux_version": _command_output("tmux", "-V"),
        "llmao_dependency_lock_sha256": optional_sha256_file(ROOT / "uv.lock"),
    }
    output = resolve_v4_output_path(output, repo_root=ROOT)
    run_root = primary_run_root(seed, protocol_sha256)
    if run_root.exists():
        raise FileExistsError(f"primary run root already exists: {run_root}")
    contract_source_paths = (
        "experiments/v4_primary_contract.py",
        "experiments/v4_artifact_paths.py",
        "experiments/v4_finalize_primary_protocol.py",
        "experiments/v4_freeze_primary_contract.py",
        "experiments/v4_run_primary_discovery.py",
        "experiments/v4_build_primary_context.py",
        "experiments/v4_evaluate_primary_candidate.py",
        "scripts/codex-v4-sandbox",
    )
    contract_source_pins = {
        relative: sha256_file(ROOT / relative) for relative in contract_source_paths
    }
    contract = {
        "schema_version": schema_version,
        "storage_layout_version": schema_version,
        "contract_id": f"v4-primary-discovery-{seed}-{protocol_sha256[:12]}",
        "created_at_utc": datetime.now(UTC).isoformat(),
        "seed": seed,
        "protocol_path": (
            v4_repo_relative_path(protocol_path, repo_root=ROOT)
            if schema_version == 2
            else str(protocol_path)
        ),
        "protocol_sha256": protocol_sha256,
        "llmao_commit": llmao_commit,
        "eve_commit": eve_commit,
        "initial_programs_sha256": initial_digest,
        "checker_bundle_path": (
            v4_repo_relative_path(bundle, repo_root=ROOT)
            if schema_version == 2
            else str(bundle)
        ),
        "checker_bundle_manifest_sha256": sha256_file(bundle_manifest_path),
        "data_dir": (
            protocol["storage_layout"]["mnist_cache"]
            if schema_version == 2
            else str((Path.home() / "Library/Caches/llmao-v4-phase12-mnist").resolve())
        ),
        "sandbox_preflight": sandbox,
        "native_fixture": fixture,
        "sandbox_wrapper_sha256": wrapper_sha256,
        "runtime": runtime,
        "run_root": (
            v4_repo_relative_path(run_root, repo_root=ROOT)
            if schema_version == 2
            else str(run_root)
        ),
        "contract_source_pins": contract_source_pins,
        "launch": {
            "driver": "codex_tmux",
            "model": "gpt-6-luna",
            "reasoning_effort": "max",
            "permission_profile": "llmao-v4-workspace-only",
            "workers": 1,
            "parallel_workers": 1,
            "network": False,
            "web_search": False,
            "multi_agent": False,
            "boundary_repair_attempts": 0,
        },
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    raw = (json.dumps(contract, indent=2, sort_keys=True, allow_nan=False) + "\n").encode()
    digest = hashlib.sha256(raw).hexdigest()
    with output.open("xb") as stream:
        stream.write(raw)
    with output.with_suffix(output.suffix + ".sha256").open("xb") as stream:
        stream.write(f"{digest}  {output.name}\n".encode())
    return {"path": str(output), "sha256": digest, "seed": seed}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", required=True, type=int)
    parser.add_argument(
        "--protocol",
        type=Path,
        default=ROOT / "results/v4/primary_protocol.json",
    )
    parser.add_argument("--checker-bundle", type=Path, required=True)
    parser.add_argument("--preflight-evidence", type=Path, required=True)
    parser.add_argument("--native-fixture", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(
        json.dumps(
            freeze_contract(
                seed=args.seed,
                protocol_path=args.protocol,
                checker_bundle=args.checker_bundle,
                preflight_evidence=args.preflight_evidence,
                native_fixture=args.native_fixture,
                output=args.output,
            ),
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
