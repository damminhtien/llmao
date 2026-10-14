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


def _git(checkout: Path, *arguments: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(checkout), *arguments],
        text=True,
    ).strip()


def _validate_usage(usage: dict) -> None:
    checked = datetime.strptime(
        usage["checked_at_utc"], "%Y-%m-%d %H:%M:%S UTC"
    ).replace(tzinfo=UTC)
    age = (datetime.now(UTC) - checked).total_seconds()
    if not 0 <= age <= 600:
        raise ValueError("Plus usage snapshot must be less than ten minutes old")
    if usage["plan"] != "plus" or usage["ordinary_usage_allowed"] is not True:
        raise ValueError("follow-up requires available ordinary ChatGPT Plus usage")
    for key in ("five_hour_window_used_percent", "weekly_window_used_percent"):
        if type(usage[key]) not in (int, float) or not 0 <= usage[key] < 100:
            raise ValueError("ordinary usage must be available in both windows")


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
        "--contract", type=Path, default=ROOT / "V4_FOLLOWUP_PILOT_CONTRACT.json"
    )
    parser.add_argument("--usage-snapshot", type=Path, required=True)
    parser.add_argument("--record", type=Path, required=True)
    parser.add_argument("--eve-root", type=Path, default=ROOT.parent / "eve")
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()
    content = args.contract.read_bytes()
    digest = hashlib.sha256(content).hexdigest()
    if digest != args.contract.with_suffix(".sha256").read_text().split()[0]:
        raise ValueError("follow-up contract digest mismatch")
    contract = json.loads(content)
    usage = json.loads(args.usage_snapshot.read_text())
    _validate_usage(usage)
    launch = contract["launch"]
    checkout = Path(launch["evaluator_checkout"])
    for path, expected in (
        (args.eve_root, contract["source_pins"]["eve_commit"]),
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
        }
    )
    command = [
        str(args.eve_root / ".venv/bin/python"),
        "-u",
        "-m",
        "scaling_evolve.algorithms.eve.runner",
        *launch["hydra_arguments"],
    ]
    args.record.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "status": "launching",
        "contract_sha256": digest,
        "usage_snapshot": usage,
        "run_root": str(run_root),
        "command": command,
    }
    with args.record.open("x") as stream:
        json.dump(record, stream, indent=2, sort_keys=True, allow_nan=False)
    process = subprocess.Popen(
        command, cwd=args.eve_root, env=environment, start_new_session=True
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
