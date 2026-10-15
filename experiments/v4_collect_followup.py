"""Collect the terminal frozen follow-up without rescoring any proposal."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import runpy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
METADATA = ROOT / "results/v4/phase10_followup"


def _json(path: Path):
    return json.loads(path.read_text())


def _write(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x") as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")


def _record(path: Path) -> dict:
    content = path.read_bytes()
    return {
        "path": str(path.relative_to(ROOT)),
        "sha256": hashlib.sha256(content).hexdigest(),
        "size_bytes": len(content),
    }


def _copy(source: Path, destination: Path) -> dict:
    if source.is_symlink() or not source.is_file():
        raise ValueError(f"archive source must be a regular file: {source}")
    content = source.read_bytes()
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("xb") as stream:
        stream.write(content)
    if source.read_bytes() != content:
        raise ValueError(f"archive source changed while copying: {source}")
    return _record(destination)


def collect(
    destination: Path,
    *,
    contract_path: Path | None = None,
    execution_path: Path | None = None,
) -> dict:
    """Require terminal completion and preserve raw evidence plus replay inputs."""
    destination = destination.resolve()
    if not destination.is_relative_to(ROOT) or destination.exists():
        raise ValueError("archive must be a new directory inside the repository")
    contract_path = contract_path or ROOT / "V4_FOLLOWUP_REPAIR_CONTRACT.json"
    if not contract_path.is_absolute():
        contract_path = ROOT / contract_path
    contract_path = contract_path.resolve()
    if not contract_path.is_relative_to(ROOT.resolve()):
        raise ValueError("contract must be inside the repository")
    contract = _json(contract_path)
    digest = hashlib.sha256(contract_path.read_bytes()).hexdigest()
    if digest != contract_path.with_suffix(".sha256").read_text().split()[0]:
        raise ValueError("follow-up contract digest changed")
    execution_path = execution_path or METADATA / "execution.json"
    if not execution_path.is_absolute():
        execution_path = ROOT / execution_path
    execution_path = execution_path.resolve()
    if not execution_path.is_relative_to(ROOT.resolve()):
        raise ValueError("execution record must be inside the repository")
    metadata_root = execution_path.parent
    execution = _json(execution_path)
    if (
        execution["status"] != "runner_exited"
        or execution["exit_code"] != 0
        or execution.get("stop_reason")
        or execution["contract_sha256"] != digest
    ):
        raise ValueError("collection requires a normally exited frozen run")
    run_root = Path(execution["run_root"])
    if str(run_root) != contract["launch"]["run_root"]:
        raise ValueError("executed run root differs from frozen contract")
    source = _json(metadata_root / "evaluator_source_snapshot.json")
    if source["sha256"] != contract["source_pins"]["evaluator_source_sha256"]:
        raise ValueError("evaluator source snapshot differs from the frozen contract")
    if (
        hashlib.sha256((ROOT / "results/v4/protocol.json").read_bytes()).hexdigest()
        != contract["source_pins"]["base_protocol_sha256"]
    ):
        raise ValueError("pilot protocol differs from the frozen contract")
    checkpoint = _json(run_root / "checkpoint.json")
    budget = contract["budget"]["submitted_proposals"]
    if (
        checkpoint["last_completed_iteration"] != budget
        or checkpoint["max_iterations"] != budget
    ):
        raise ValueError("checkpoint does not prove the full proposal count")
    with (run_root / "telemetry/phase2_solvers.csv").open(newline="") as stream:
        rows = list(csv.DictReader(stream))
    if [int(row["iteration"]) for row in rows] != list(range(1, budget + 1)):
        raise ValueError("telemetry does not cover each proposal exactly once")
    supervisor = runpy.run_path(str(ROOT / "experiments/v4_launch_followup.py"))
    violation = supervisor["_boundary_violation"](
        run_root, contract["source_pins"]["structural_bundle_manifest_sha256"], set()
    )
    if violation:
        raise ValueError(violation)
    seed_workspaces = list((run_root / "evaluation_workspaces").glob("*_seed"))
    if len(seed_workspaces) != 1:
        raise ValueError("run must have one separate seed evaluation")

    overlay = Path(contract["launch"]["immutable_overlay"])
    overlay_files = contract["source_pins"]["worker_immutable_files_sha256"]
    if overlay.is_symlink() or not overlay.is_dir():
        raise ValueError("frozen worker immutable overlay is missing or unsafe")
    overlay_paths = list(overlay.rglob("*"))
    if any(path.is_symlink() for path in overlay_paths):
        raise ValueError("frozen worker immutable overlay contains a symlink")
    overlay_actual = {
        path.relative_to(overlay).as_posix()
        for path in overlay_paths
        if path.is_file()
    }
    if overlay_actual != set(overlay_files):
        raise ValueError("frozen worker immutable overlay inventory changed")
    overlay_sources = {}
    for relative, expected in overlay_files.items():
        source_path = overlay / relative
        if _record(source_path)["sha256"] != expected:
            raise ValueError(f"frozen worker immutable file changed: {relative}")
        overlay_sources[relative] = source_path

    native_fixture = contract["native_fixture_evidence"]
    native_sources = {}
    for name, expected in native_fixture["files_sha256"].items():
        source_path = Path(native_fixture["directory"]) / name
        if source_path.is_symlink() or not source_path.is_file():
            raise ValueError(f"native fixture evidence is missing: {name}")
        if _record(source_path)["sha256"] != expected:
            raise ValueError(f"native fixture evidence changed before collection: {name}")
        native_sources[name] = source_path

    destination.mkdir(parents=True)
    evidence = {}
    for relative in (
        "checkpoint.json",
        "telemetry/summary.json",
        "telemetry/phase2_solvers.csv",
        "telemetry/phase2_optimizers.csv",
        "telemetry/iteration_metrics.csv",
    ):
        evidence[relative] = _copy(
            run_root / relative, destination / "run_evidence" / relative
        )
    for name in (
        "execution.json",
        "evaluator_source_snapshot.json",
        "configuration_validation.json",
        "prelaunch_usage.json",
        contract_path.with_suffix(".sha256").name,
    ):
        source_path = (
            execution_path
            if name == "execution.json"
            else contract_path.with_suffix(".sha256")
            if name.endswith(".sha256")
            else metadata_root / name
        )
        evidence[name] = _copy(source_path, destination / "run_evidence" / name)
    evidence[contract_path.name] = _copy(
        contract_path, destination / "run_evidence" / contract_path.name
    )
    for name, fixture_path in native_sources.items():
        evidence[f"native_fixture/{name}"] = _copy(
            fixture_path, destination / "run_evidence" / "native_fixture" / name
        )
    for relative, overlay_path in overlay_sources.items():
        evidence[f"worker_immutable_overlay/{relative}"] = _copy(
            overlay_path,
            destination / "run_evidence" / "worker_immutable_overlay" / relative,
        )
    observations = []
    for index, row in enumerate([None, *rows]):
        workspace = (
            seed_workspaces[0]
            if row is None
            else run_root / "evaluation_workspaces" / row["workspace_id"]
        )
        target = destination / (
            "seed" if row is None else f"attempts/iteration_{index:02d}"
        )
        logs = workspace / "logs/evaluate"
        score = _json(logs / "score.yaml")
        if row is not None and score != json.loads(row["score_json"]):
            raise ValueError("evaluator score differs from terminal telemetry")
        files = {}
        for name in ("language.json", "program.json"):
            files[name] = _copy(workspace / "solver/candidate" / name, target / name)
        if row is None:
            expected_seed = {
                "language.json": contract["initialization"]["seed_language_sha256"],
                "program.json": contract["initialization"]["seed_program_sha256"],
            }
            if any(files[name]["sha256"] != expected_seed[name] for name in expected_seed):
                raise ValueError("archived seed differs from the fresh G0 contract")
        for name in ("lineage_parent.json", "lineage_state.json"):
            files[name] = _copy(logs / name, target / name)
        error = (
            (logs / "error.txt").read_text() if (logs / "error.txt").exists() else None
        )
        _write(target / "evaluation.json", {"score": score, "validation_error": error})
        files["evaluation.json"] = _record(target / "evaluation.json")
        raw = {}
        for path in sorted(logs.rglob("*")):
            if path.is_file():
                relative = path.relative_to(logs)
                raw[f"evaluate/{relative}"] = _copy(
                    path, target / "raw/evaluate" / relative
                )
        if row is not None:
            worker = run_root / "solver_workspaces" / row["workspace_id"]
            transcripts = sorted((worker / ".codex-driver-transcripts").glob("*"))
            if not any(path.suffix == ".jsonl" for path in transcripts):
                raise ValueError("completed worker has no archived native transcript")
            for path in transcripts:
                if path.is_file():
                    raw[f"native/{path.name}"] = _copy(
                        path, target / "raw/native" / path.name
                    )
            for relative in (
                "README.md",
                ".scaling_evolve/worker.yaml",
                "structural_check/manifest.json",
            ):
                raw[relative] = _copy(
                    worker / relative, target / "raw/worker" / relative
                )
        observations.append(
            {
                "iteration": index,
                "workspace_id": workspace.name,
                "files": files,
                "raw_files": raw,
            }
        )
    manifest = {
        "schema_version": 1,
        "phase": 10,
        "pilot_status": "completed_pending_gate_audit",
        "interpretation": "exploratory feasibility only; no discovery result",
        "run": {
            "run_id": checkpoint["run_id"],
            "run_root": str(run_root),
            "evidence_files": evidence,
        },
        "environment": {
            "account_plan": "ChatGPT Plus",
            "protocol_sha256": contract["source_pins"]["base_protocol_sha256"],
            "llmao_commit": contract["source_pins"]["llmao_runtime_commit"],
            "evaluator_version_sha256": source["sha256"],
        },
        "seed": observations[0],
        "attempts": observations[1:],
    }
    _write(destination / "manifest.json", manifest)
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination", type=Path)
    parser.add_argument("--contract", type=Path)
    parser.add_argument("--record", type=Path)
    args = parser.parse_args()
    manifest = collect(
        args.destination,
        contract_path=args.contract,
        execution_path=args.record,
    )
    print(
        json.dumps(
            {
                "run_id": manifest["run"]["run_id"],
                "proposals": len(manifest["attempts"]),
                "archive": str(args.destination),
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
