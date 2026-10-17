"""Shared hashing and launch-contract checks for Phase 12 discovery runs."""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any

try:
    from .v4_artifact_paths import V4_ROOT, resolve_v4_repo_path
except ImportError:
    from v4_artifact_paths import V4_ROOT, resolve_v4_repo_path

ROOT = Path(__file__).resolve().parents[1]
EVE_ROOT = (ROOT.parent / "eve").resolve()
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_GIT_SHA = re.compile(r"[0-9a-f]{40}\Z")


def sha256_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def optional_sha256_file(path: Path) -> str | None:
    path = Path(path)
    if path.is_symlink():
        raise ValueError(f"expected a regular optional file, got symlink: {path}")
    if not path.exists():
        return None
    if not path.is_file():
        raise ValueError(f"expected a regular optional file: {path}")
    return sha256_file(path)


def primary_run_root(seed: int, protocol_sha256: str, *, root: Path = ROOT) -> Path:
    if type(seed) is not int or seed < 0:
        raise ValueError("primary run seed must be a non-negative integer")
    if not _SHA256.fullmatch(protocol_sha256):
        raise ValueError("primary run protocol digest must be a lowercase SHA-256")
    return Path(root).resolve(strict=True) / "results/v4/phase12/runs" / (
        f"discovery-{seed}-{protocol_sha256[:12]}"
    )


def venv_python_path(root: Path) -> Path:
    """Return the venv launcher path without resolving away its environment."""
    path = Path(root).absolute() / ".venv/bin/python"
    if not path.is_file() or not os.access(path, os.X_OK):
        raise FileNotFoundError(f"project venv Python is not executable: {path}")
    return path


def git_value(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def tracked_tree_is_clean(repo: Path) -> bool:
    result = subprocess.run(
        ["git", "-C", str(repo), "diff", "--quiet", "HEAD", "--"],
        check=False,
    )
    return result.returncode == 0


def read_hashed_json(path: Path) -> tuple[dict[str, Any], str]:
    path = Path(path).resolve(strict=True)
    raw = path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    sidecar = path.with_suffix(path.suffix + ".sha256")
    fields = sidecar.read_text(encoding="utf-8").split()
    if not fields or fields[0] != digest:
        raise ValueError(f"SHA-256 sidecar mismatch: {sidecar}")
    payload = json.loads(raw)
    if not isinstance(payload, dict):
        raise TypeError(f"expected an object in {path}")
    return payload, digest


def verify_source_paths(root: Path, pins: dict[str, str]) -> None:
    resolved_root = Path(root).resolve(strict=True)
    if not isinstance(pins, dict) or not pins:
        raise ValueError("contract has no source file pins")
    for relative, expected in sorted(pins.items()):
        if not isinstance(relative, str) or not isinstance(expected, str):
            raise TypeError("source file pins must contain path/hash strings")
        if not _SHA256.fullmatch(expected):
            raise ValueError(f"invalid source SHA-256 for {relative}")
        path = (resolved_root / relative).resolve(strict=True)
        if resolved_root not in path.parents:
            raise ValueError(f"source file pin escapes its checkout: {relative}")
        if sha256_file(path) != expected:
            raise ValueError(f"source file changed after contract freeze: {relative}")


def verify_evidence_record(
    record: dict[str, Any], *, label: str, repo_relative: bool = False
) -> Path:
    if not isinstance(record, dict):
        raise TypeError(f"{label} evidence record must be an object")
    raw_path = str(record.get("path", ""))
    path = (
        resolve_v4_repo_path(raw_path)
        if repo_relative
        else Path(raw_path).expanduser().resolve(strict=True)
    )
    path = path.resolve(strict=True)
    expected = record.get("sha256")
    if not isinstance(expected, str) or not _SHA256.fullmatch(expected):
        raise ValueError(f"{label} evidence record has an invalid digest")
    if sha256_file(path) != expected:
        raise ValueError(f"{label} evidence changed after contract freeze")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("passed") is not True and payload.get("status") != "passed":
        raise ValueError(f"{label} evidence did not pass")
    manifest_path_value = record.get("manifest_path")
    manifest_sha256 = record.get("manifest_sha256")
    if manifest_path_value is not None:
        manifest_path = (
            resolve_v4_repo_path(str(manifest_path_value))
            if repo_relative
            else Path(str(manifest_path_value)).resolve(strict=True)
        ).resolve(strict=True)
        if sha256_file(manifest_path) != manifest_sha256:
            raise ValueError(f"{label} manifest digest mismatch")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        for relative, item in manifest.get("files", {}).items():
            artifact = (manifest_path.parent / relative).resolve(strict=True)
            if manifest_path.parent.resolve() not in artifact.parents:
                raise ValueError(f"{label} manifest path escapes its root: {relative}")
            if sha256_file(artifact) != item.get("sha256"):
                raise ValueError(f"{label} artifact changed: {relative}")
    return path


def validate_contract(
    contract_path: Path,
    *,
    expected_seed: int | None = None,
    allow_existing_run_root: bool = False,
) -> dict[str, Any]:
    contract, contract_sha256 = read_hashed_json(contract_path)
    schema_version = contract.get("schema_version")
    if schema_version not in (1, 2):
        raise ValueError("unsupported primary discovery contract version")
    seed = contract.get("seed")
    if type(seed) is not int or (expected_seed is not None and seed != expected_seed):
        raise ValueError("primary discovery contract seed mismatch")

    protocol_path = (
        resolve_v4_repo_path(contract["protocol_path"])
        if schema_version == 2
        else Path(contract["protocol_path"]).resolve(strict=True)
    ).resolve(strict=True)
    protocol, protocol_sha256 = read_hashed_json(protocol_path)
    if protocol_sha256 != contract.get("protocol_sha256"):
        raise ValueError("primary discovery protocol differs from its contract")
    if protocol.get("status") != "finalized_primary":
        raise ValueError("primary protocol is not finalized")
    if seed not in protocol["primary_discovery"]["discovery_seeds"]:
        raise ValueError("contract seed is not in the preregistered discovery seed list")

    if git_value(ROOT, "rev-parse", "HEAD") != contract.get("llmao_commit"):
        raise ValueError("LLMAO commit differs from the primary contract")
    if not tracked_tree_is_clean(ROOT):
        raise ValueError("tracked LLMAO files changed after contract freeze")
    if git_value(EVE_ROOT, "rev-parse", "HEAD") != contract.get("eve_commit"):
        raise ValueError("EvE commit differs from the primary contract")
    if git_value(EVE_ROOT, "status", "--porcelain", "--untracked-files=all"):
        raise ValueError("EvE checkout must be clean for primary discovery")
    verify_source_paths(ROOT, protocol["source_pins"])
    verify_source_paths(ROOT, contract["contract_source_pins"])

    initial_path = ROOT / "V4_INITIAL_PROGRAMS.json"
    initial_digest = sha256_file(initial_path)
    if initial_digest != contract.get("initial_programs_sha256"):
        raise ValueError("common initial-program digest differs from the contract")
    if initial_digest != protocol["primary_discovery"]["initial_programs_sha256"]:
        raise ValueError("common initial-program digest differs from the protocol")

    preflight_path = verify_evidence_record(
        contract["sandbox_preflight"],
        label="sandbox preflight",
        repo_relative=schema_version == 2,
    )
    native_path = verify_evidence_record(
        contract["native_fixture"],
        label="native fixture",
        repo_relative=schema_version == 2,
    )
    native_payload = json.loads(native_path.read_text(encoding="utf-8"))
    if native_payload.get("sandbox_wrapper_sha256") != contract.get("sandbox_wrapper_sha256"):
        raise ValueError("native fixture was produced by a different sandbox wrapper")
    if native_payload.get("system_prompt_file") != str(
        (ROOT / "configs/v4/phase12_primary_worker.md").resolve()
    ):
        raise ValueError("native fixture did not exercise the primary worker prompt")
    if native_payload.get("system_prompt_sha256") != sha256_file(
        ROOT / "configs/v4/phase12_primary_worker.md"
    ):
        raise ValueError("native fixture primary worker prompt digest differs")
    preflight_payload = json.loads(preflight_path.read_text(encoding="utf-8"))
    if preflight_payload.get("wrapper_sha256") != contract.get("sandbox_wrapper_sha256"):
        raise ValueError("sandbox preflight used a different wrapper revision")
    if schema_version == 2 and (
        preflight_payload.get("checks", {}).get("mnist_cache_read_denied") is not True
    ):
        raise ValueError("worker sandbox preflight did not deny MNIST cache reads")
    bundle_path = (
        resolve_v4_repo_path(contract["checker_bundle_path"])
        if schema_version == 2
        else Path(contract["checker_bundle_path"]).resolve(strict=True)
    ).resolve(strict=True)
    bundle_manifest_path = bundle_path / "manifest.json"
    bundle_manifest = json.loads(bundle_manifest_path.read_text(encoding="utf-8"))
    if bundle_manifest.get("protocol_sha256") != protocol_sha256:
        raise ValueError("structural checker bundle embeds a different protocol")
    if sha256_file(bundle_manifest_path) != contract.get("checker_bundle_manifest_sha256"):
        raise ValueError("structural checker bundle manifest changed")
    if (
        preflight_payload.get("bundle_manifest_sha256")
        != contract.get("checker_bundle_manifest_sha256")
        or native_payload.get("checker_bundle_manifest_sha256")
        != contract.get("checker_bundle_manifest_sha256")
        or native_payload.get("protocol_sha256") != protocol_sha256
    ):
        raise ValueError("preflight or native fixture used a different primary bundle")
    for relative, record in bundle_manifest.get("files", {}).items():
        path = (bundle_path / relative).resolve(strict=True)
        if bundle_path not in path.parents:
            raise ValueError(f"checker bundle path escapes its root: {relative}")
        if sha256_file(path) != record.get("sha256"):
            raise ValueError(f"checker bundle source changed: {relative}")
    if sha256_file(ROOT / "scripts/codex-v4-sandbox") != contract.get("sandbox_wrapper_sha256"):
        raise ValueError("V4 sandbox wrapper differs from the contract")
    if schema_version == 1:
        data_dir = Path(contract["data_dir"]).expanduser().resolve(strict=False)
        if data_dir == ROOT or ROOT in data_dir.parents:
            raise ValueError("legacy MNIST cache must be outside the LLMAO checkout")
        run_root = Path(contract["run_root"]).expanduser().resolve(strict=False)
    else:
        storage_layout = protocol.get("storage_layout", {})
        if (
            storage_layout.get("version") != 2
            or storage_layout.get("artifact_root") != "results/v4"
            or storage_layout.get("candidate_worker_can_read_mnist_cache") is not False
            or storage_layout.get("output_paths_must_resolve_inside_artifact_root")
            is not True
            or storage_layout.get("reject_symlink_escape") is not True
            or contract.get("storage_layout_version") != 2
        ):
            raise ValueError("schema v2 contract requires storage-layout version 2")
        data_dir = resolve_v4_repo_path(contract["data_dir"])
        expected_data_dir = resolve_v4_repo_path(storage_layout["mnist_cache"])
        if data_dir != expected_data_dir or data_dir == V4_ROOT:
            raise ValueError("MNIST cache differs from the contracted V4 cache path")
        run_root = resolve_v4_repo_path(contract["run_root"])
        preflight_cache = resolve_v4_repo_path(
            preflight_payload.get("mnist_cache_path", "")
        )
        native_preflight = native_payload.get("workspace_preflight", {})
        native_cache = resolve_v4_repo_path(
            native_preflight.get("mnist_cache_path", "")
        )
        if preflight_cache != data_dir or (
            native_preflight.get("checks", {}).get("mnist_cache_read_denied")
            is not True
            or native_cache != data_dir
        ):
            raise ValueError("sandbox evidence does not protect the contracted MNIST cache")

    expected_run_root = primary_run_root(seed, protocol_sha256)
    if run_root != expected_run_root:
        raise ValueError("primary contract run root is outside its seed-specific path")
    if run_root.exists() and not allow_existing_run_root:
        raise FileExistsError(f"primary run root already exists: {run_root}")
    contract["verified_protocol"] = protocol
    contract["verified_protocol_sha256"] = protocol_sha256
    contract["verified_contract_sha256"] = contract_sha256
    contract["verified_preflight_path"] = str(preflight_path)
    contract["verified_native_fixture_path"] = str(native_path)
    contract["verified_run_root"] = str(run_root)
    contract["verified_data_dir"] = str(data_dir)
    return contract
