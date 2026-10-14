"""Pinned worker check bundles exclude scoring and data-access modules."""

from __future__ import annotations

import hashlib
import json
import runpy
import subprocess
import sys
from pathlib import Path

import pytest

from bias_optimizer.dsl.ast import Expr
from bias_optimizer.v4.language import G0_LANGUAGE, extend_macro_language

ROOT = Path(__file__).resolve().parents[2]
BUILDER = runpy.run_path(str(ROOT / "experiments/v4_build_check_bundle.py"))


@pytest.fixture
def inputs(tmp_path: Path):
    protocol = tmp_path / "protocol.json"
    protocol.write_text(
        json.dumps(
            {
                "primary_design": {
                    "exact_cli_model_identifier": "gpt-6-luna",
                    "requested_reasoning_effort": "max",
                },
                "candidate_boundary": {"codex_driver": "codex_tmux"},
                "evaluator_basis": {"training_subset_seed": 42},
            }
        )
    )
    commit = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()
    return {
        "repo_root": ROOT,
        "commit": commit,
        "protocol_path": protocol,
        "protocol_sha256": hashlib.sha256(protocol.read_bytes()).hexdigest(),
    }


def test_pinned_bundle_runs_without_data_or_scoring_modules(tmp_path, inputs) -> None:
    destination = tmp_path / "bundle"
    manifest = BUILDER["build_bundle"](destination, **inputs)
    assert len(manifest["files"]) == 21
    for relative, record in manifest["files"].items():
        assert (
            hashlib.sha256((destination / relative).read_bytes()).hexdigest()
            == record["sha256"]
        )
        assert not any(
            part in relative.split("/") for part in ("ml", "data", "evaluation")
        )
    candidate = tmp_path / "candidate"
    candidate.mkdir()
    (candidate / "language.json").write_text(
        json.dumps(extend_macro_language(G0_LANGUAGE, []).to_dict())
    )
    (candidate / "program.json").write_text(
        Expr("spatial_split", (Expr("image"),), {"rows": 2, "cols": 3}).to_json()
    )
    command = [
        sys.executable,
        "-IB",
        str(destination / "experiments/v4_check_candidate.py"),
        str(candidate),
    ]
    valid = subprocess.run(command, check=True, text=True, capture_output=True)
    result = json.loads(valid.stdout)
    assert result["status"] == "valid" and result["feature_dimension"] == 6
    inspection = """
import sys
from pathlib import Path
root = Path(sys.argv[1])
sys.path.insert(0, str(root / "src"))
from bias_optimizer.v4.candidate.check import check_candidate_directory
assert check_candidate_directory(Path(sys.argv[2]))["status"] == "valid"
for name, module in tuple(sys.modules.items()):
    if not name.startswith("bias_optimizer"):
        continue
    assert Path(module.__file__).is_relative_to(root), (name, module.__file__)
    assert not name.startswith(("bias_optimizer.ml", "bias_optimizer.data",
        "bias_optimizer.evaluation", "bias_optimizer.optimizer_bench",
        "bias_optimizer.dsl.compiler", "bias_optimizer.cache")), name
"""
    subprocess.run(
        [sys.executable, "-IB", "-c", inspection, str(destination), str(candidate)],
        check=True,
    )
    assert not list(destination.rglob("__pycache__"))
    (candidate / "program.json").write_text(Expr("unknown").to_json())
    invalid = subprocess.run(command, check=False, text=True, capture_output=True)
    assert invalid.returncode == 1
    assert json.loads(invalid.stdout)["status"] == "invalid"


def test_bundle_requires_new_output_and_matching_protocol(tmp_path, inputs) -> None:
    destination = tmp_path / "bundle"
    wrong = dict(inputs, protocol_sha256="0" * 64)
    with pytest.raises(ValueError, match="digest mismatch"):
        BUILDER["build_bundle"](destination, **wrong)
    assert not destination.exists()
    BUILDER["build_bundle"](destination, **inputs)
    with pytest.raises(FileExistsError):
        BUILDER["build_bundle"](destination, **inputs)


def test_bundle_rejects_noncanonical_commit_before_writing(tmp_path, inputs) -> None:
    destination = tmp_path / "bundle"
    with pytest.raises(ValueError, match="commit"):
        BUILDER["build_bundle"](destination, **dict(inputs, commit="HEAD"))
    assert not destination.exists()
