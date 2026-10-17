"""Resolve V4-owned output paths under the repository artifact root."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
V4_ROOT = ROOT / "results/v4"


def resolve_v4_output_path(
    path: str | Path,
    *,
    allow_root: bool = False,
    repo_root: Path = ROOT,
    artifact_root: Path | None = None,
) -> Path:
    """Resolve an output argument and reject paths outside ``results/v4``.

    Relative arguments prefixed with ``results/v4`` are repository-relative;
    other relative arguments are logical paths beneath the V4 artifact root.
    Resolution occurs before containment checks so symlink escapes are rejected.
    """
    repo_root = Path(repo_root).resolve(strict=True)
    logical_artifact_root = repo_root / "results/v4"
    artifact_root = Path(artifact_root or logical_artifact_root).resolve(strict=False)
    try:
        artifact_root.relative_to(repo_root)
    except ValueError as error:
        raise ValueError("V4 artifact root resolves outside the repository") from error
    if artifact_root != logical_artifact_root:
        raise ValueError("results/v4 must not be redirected through a symlink")
    candidate = Path(path).expanduser()
    if not candidate.is_absolute():
        if candidate.parts[:2] == ("results", "v4"):
            candidate = repo_root / candidate
        else:
            candidate = artifact_root / candidate

    resolved = candidate.resolve(strict=False)
    if resolved == artifact_root:
        if allow_root:
            return resolved
        raise ValueError(f"V4 output must be below the artifact root: {path}")
    try:
        resolved.relative_to(artifact_root)
    except ValueError as error:
        raise ValueError(f"V4 output path escapes results/v4: {path}") from error
    return resolved


def v4_repo_relative_path(path: str | Path, *, repo_root: Path = ROOT) -> str:
    """Return a V4 path using the repository-relative manifest convention."""
    repo_root = Path(repo_root).resolve(strict=True)
    resolved = resolve_v4_output_path(path, repo_root=repo_root)
    return resolved.relative_to(repo_root).as_posix()


def resolve_repository_output_path(
    path: str | Path, *, repo_root: Path = ROOT
) -> Path:
    """Resolve a legacy source-artifact output inside the checkout only."""
    repo_root = Path(repo_root).resolve(strict=True)
    candidate = Path(path).expanduser()
    if not candidate.is_absolute():
        candidate = repo_root / candidate
    resolved = candidate.resolve(strict=False)
    if resolved == repo_root or repo_root not in resolved.parents:
        raise ValueError(f"V4 output path escapes the repository: {path}")
    return resolved


def resolve_v4_repo_path(path: str | Path, *, repo_root: Path = ROOT) -> Path:
    """Resolve a repo-relative or V4-root-relative artifact path."""
    repo_root = Path(repo_root).resolve(strict=True)
    candidate = Path(path).expanduser()
    return resolve_v4_output_path(candidate, repo_root=repo_root)
