"""Common starting ASTs are deterministic, score-free, and G0 eligible."""

from __future__ import annotations

import hashlib
import json
import runpy
import subprocess
from pathlib import Path

import pytest

from bias_optimizer.dsl.ast import Expr

ROOT = Path(__file__).resolve().parents[2]
BUILDER = runpy.run_path(str(ROOT / "experiments/v4_freeze_initial_programs.py"))


@pytest.fixture
def source() -> bytes:
    return subprocess.check_output(
        ["git", "show", f"{BUILDER['SOURCE_COMMIT']}:{BUILDER['SOURCE_PATH']}"],
        cwd=ROOT,
    )


def test_frozen_initial_manifest_is_deterministic_and_score_free(source) -> None:
    manifest = BUILDER["build_manifest"](source)
    output = ROOT / "V4_INITIAL_PROGRAMS.json"
    assert manifest == json.loads(output.read_text())
    assert (
        hashlib.sha256(output.read_bytes()).hexdigest()
        == (ROOT / "V4_INITIAL_PROGRAMS.sha256").read_text().strip()
    )
    assert manifest == BUILDER["build_manifest"](source)
    seeds = manifest["programs"]
    assert len(seeds) == len({seed["ast_sha256"] for seed in seeds}) == 20
    assert [seed["index"] for seed in seeds] == list(range(20))
    for seed in seeds:
        assert set(seed) == {
            "index",
            "historical_candidate_id",
            "ast_sha256",
            "program",
            "feature_dimension",
            "expanded_depth",
            "expanded_nodes",
            "used_primitives",
        }
        assert seed["feature_dimension"] <= 128
        assert seed["expanded_depth"] <= 6
        assert seed["expanded_nodes"] <= 127
    assert seeds[0]["historical_candidate_id"] != seeds[0]["ast_sha256"]


@pytest.mark.parametrize("change", ["count", "duplicate", "digest", "operation"])
def test_initial_manifest_rejects_invalid_starting_sets(source, change) -> None:
    protocol = json.loads(source)
    seeds = protocol["frozen_search_space"]["seed_programs"]
    if change == "count":
        seeds.pop()
    elif change == "duplicate":
        seeds[1] = seeds[0]
    elif change == "digest":
        seeds[0]["ast_sha256"] = "0" * 64
    else:
        program = Expr("spatial_condition", (Expr("image"),))
        seeds[0]["bias"]["program"] = program.to_dict()
        seeds[0]["ast_sha256"] = hashlib.sha256(program.to_json().encode()).hexdigest()
    with pytest.raises(ValueError):
        BUILDER["build_manifest"](json.dumps(protocol).encode())
