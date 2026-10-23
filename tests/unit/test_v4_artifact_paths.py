"""V4 output paths cannot escape the repository artifact root."""

from pathlib import Path

import pytest

from experiments.v4_artifact_paths import (
    resolve_repository_output_path,
    resolve_v4_output_path,
    v4_repo_relative_path,
)


def test_resolves_logical_and_repo_relative_paths(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    (repo / "results/v4").mkdir(parents=True)

    logical = resolve_v4_output_path("phase12/runs/run-a", repo_root=repo)
    repo_relative = resolve_v4_output_path(
        "results/v4/phase12/runs/run-a", repo_root=repo
    )

    assert logical == repo / "results/v4/phase12/runs/run-a"
    assert repo_relative == logical
    assert v4_repo_relative_path(logical, repo_root=repo) == (
        "results/v4/phase12/runs/run-a"
    )


@pytest.mark.parametrize("path", ["../outside/run", "/tmp/v4-run"])
def test_rejects_paths_outside_artifact_root(tmp_path: Path, path: str) -> None:
    repo = tmp_path / "repo"
    (repo / "results/v4").mkdir(parents=True)

    with pytest.raises(ValueError, match="escapes results/v4"):
        resolve_v4_output_path(path, repo_root=repo)


def test_rejects_symlink_escape(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    artifact_root = repo / "results/v4"
    artifact_root.mkdir(parents=True)
    outside = tmp_path / "outside"
    outside.mkdir()
    (artifact_root / "escape").symlink_to(outside, target_is_directory=True)

    with pytest.raises(ValueError, match="escapes results/v4"):
        resolve_v4_output_path("escape/run.json", repo_root=repo)


def test_rejects_artifact_root_symlink(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    results = repo / "results"
    results.mkdir(parents=True)
    outside = tmp_path / "outside-v4"
    outside.mkdir()
    (results / "v4").symlink_to(outside, target_is_directory=True)

    with pytest.raises(ValueError, match="artifact root resolves outside"):
        resolve_v4_output_path("run.json", repo_root=repo)


def test_repository_output_allows_source_artifacts_but_rejects_external_paths(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    assert resolve_repository_output_path(
        "configs/v4/V4_INITIAL_PROGRAMS.json", repo_root=repo
    ) == repo / "configs/v4/V4_INITIAL_PROGRAMS.json"
    with pytest.raises(ValueError, match="escapes the repository"):
        resolve_repository_output_path(tmp_path / "outside.json", repo_root=repo)
