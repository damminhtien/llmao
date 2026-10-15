"""Final-protocol discovery scoring and source verification helpers."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from bias_optimizer.v4.language.validator import MacroLanguage
from bias_optimizer.v4.objective import discovery_objective

_SHA256 = re.compile(r"[0-9a-f]{64}\Z")


def file_sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_finalized_protocol(
    protocol_path: Path,
    *,
    expected_sha256: str | None = None,
) -> tuple[dict[str, Any], str]:
    """Read the immutable primary protocol and verify its adjacent digest."""
    path = Path(protocol_path).resolve(strict=True)
    payload = path.read_bytes()
    digest = hashlib.sha256(payload).hexdigest()
    if expected_sha256 is not None and digest != expected_sha256:
        raise ValueError("primary protocol digest differs from the launch contract")
    sidecar = path.with_suffix(path.suffix + ".sha256")
    if sidecar.is_file():
        fields = sidecar.read_text(encoding="utf-8").split()
        if not fields or fields[0] != digest:
            raise ValueError("primary protocol sidecar digest mismatch")
    protocol = json.loads(payload)
    if not isinstance(protocol, dict) or protocol.get("status") != "finalized_primary":
        raise ValueError("V4 primary protocol is not finalized")
    if protocol.get("primary_discovery", {}).get("official_test_access") is not False:
        raise ValueError("primary protocol must keep official test access disabled")
    return protocol, digest


def verify_source_pins(repo_root: Path, protocol: dict[str, Any]) -> dict[str, str]:
    """Verify every LLMAO file digest bound into the final primary protocol."""
    pins = protocol.get("source_pins")
    if not isinstance(pins, dict) or not pins:
        raise ValueError("final primary protocol has no implementation source pins")
    actual: dict[str, str] = {}
    root = Path(repo_root).resolve(strict=True)
    for relative, expected in sorted(pins.items()):
        if not isinstance(relative, str) or not isinstance(expected, str):
            raise TypeError("source pins must map relative paths to SHA-256 strings")
        if not _SHA256.fullmatch(expected):
            raise ValueError(f"invalid source pin for {relative}")
        path = (root / relative).resolve(strict=True)
        if root not in path.parents:
            raise ValueError(f"source pin escapes LLMAO checkout: {relative}")
        observed = file_sha256(path)
        if observed != expected:
            raise ValueError(f"primary source pin mismatch: {relative}")
        actual[relative] = observed
    return actual


def apply_discovery_score(
    stage_one_artifact: dict[str, Any],
    language: MacroLanguage,
    *,
    protocol_sha256: str,
    parent_candidate_id: str | None,
) -> dict[str, Any]:
    """Upgrade one validated stage-one artifact using the frozen discovery rule."""
    evaluation = stage_one_artifact.get("evaluation")
    if stage_one_artifact.get("status") != "stage_one_only" or not isinstance(
        evaluation, dict
    ):
        raise ValueError("discovery scoring requires a successful stage-one artifact")
    objective = discovery_objective(evaluation["stage_one_fitness"], language)
    artifact = dict(stage_one_artifact)
    artifact["status"] = "discovery_scored"
    artifact["protocol_status"] = "finalized_primary"
    artifact["protocol_sha256"] = protocol_sha256
    artifact["discovery_ready"] = True
    candidate = artifact.get("candidate")
    if not isinstance(candidate, dict):
        raise TypeError("stage-one artifact is missing candidate identity")
    artifact["candidate"] = {
        **candidate,
        "parent_candidate_id": parent_candidate_id,
        "introduced_macros": list(language.introduced_macros),
        "language_macros": [macro.name for macro in language.macros],
    }
    artifact["evaluation"] = {
        **evaluation,
        "language_complexity": objective["language_complexity"],
        "language_penalty": objective["language_penalty"],
        "discovery_fitness": objective["discovery_fitness"],
    }
    complexity = artifact.get("complexity")
    if not isinstance(complexity, dict):
        raise TypeError("stage-one artifact is missing complexity diagnostics")
    artifact["complexity"] = {
        **complexity,
        "language_penalty": objective["language_penalty"],
    }
    artifact["discovery_fitness"] = objective["discovery_fitness"]
    return artifact
