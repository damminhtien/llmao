"""Primary launch provenance handles repositories without a uv lock file."""

import hashlib
import subprocess
import sys
from pathlib import Path

import pytest

from experiments.v4_primary_contract import (
    optional_sha256_file,
    primary_run_root,
    resolve_contract_artifact_path,
    venv_python_path,
    verify_v2_mnist_cache_preflight,
)


def test_optional_sha256_file_distinguishes_absent_from_pinned_file(tmp_path):
    path = tmp_path / "uv.lock"
    assert optional_sha256_file(path) is None

    path.write_bytes(b"dependency lock")
    assert optional_sha256_file(path) == hashlib.sha256(b"dependency lock").hexdigest()


def test_primary_run_root_is_isolated_by_seed_and_protocol(tmp_path):
    protocol_sha256 = hashlib.sha256(b"primary protocol").hexdigest()

    run_root = primary_run_root(1101, protocol_sha256, root=tmp_path)

    assert run_root == tmp_path / "results/v4/phase12/runs" / (
        f"discovery-1101-{protocol_sha256[:12]}"
    )


def test_venv_python_path_preserves_the_environment_launcher(tmp_path):
    launcher = tmp_path / ".venv/bin/python"
    launcher.parent.mkdir(parents=True)
    launcher.symlink_to(sys.executable)

    path = venv_python_path(tmp_path)

    assert path == launcher
    assert path.is_symlink()
    assert path.resolve() == Path(sys.executable).resolve()


def test_v2_cache_access_is_verified_by_the_standalone_preflight(tmp_path):
    cache_path = tmp_path / "results/v4/cache/datasets/mnist_784"
    payload = {
        "checks": {"mnist_cache_read_denied": True},
        "mnist_cache_path": "results/v4/cache/datasets/mnist_784",
    }

    assert (
        verify_v2_mnist_cache_preflight(payload, cache_path, repo_root=tmp_path)
        == cache_path
    )


def test_v2_cache_access_requires_a_denied_read_check(tmp_path):
    cache_path = tmp_path / "results/v4/cache/datasets/mnist_784"
    payload = {
        "checks": {},
        "mnist_cache_path": "results/v4/cache/datasets/mnist_784",
    }

    with pytest.raises(ValueError, match="did not deny"):
        verify_v2_mnist_cache_preflight(payload, cache_path, repo_root=tmp_path)


def test_v2_contract_paths_resolve_from_the_repository_root(tmp_path):
    artifact = tmp_path / "results/v4/primary_protocol.json"
    artifact.parent.mkdir(parents=True)
    artifact.write_text("{}\n", encoding="utf-8")

    resolved = resolve_contract_artifact_path(
        "results/v4/primary_protocol.json",
        schema_version=2,
        repo_root=tmp_path,
    )

    assert resolved == artifact.resolve()


def test_v2_contract_paths_reject_external_artifacts(tmp_path):
    outside = tmp_path.parent / "outside.json"
    outside.write_text("{}\n", encoding="utf-8")

    with pytest.raises(ValueError, match="escapes results/v4"):
        resolve_contract_artifact_path(
            outside,
            schema_version=2,
            repo_root=tmp_path,
        )


def test_contract_freezer_module_cli_imports_its_contract_helpers():
    result = subprocess.run(
        [sys.executable, "-m", "experiments.v4_freeze_primary_contract", "--help"],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "--seed" in result.stdout
