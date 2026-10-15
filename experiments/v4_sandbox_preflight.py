"""Exercise the actual V4 OS sandbox without starting a model or using data."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import runpy
import shutil
import socket
import subprocess
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
WRAPPER = ROOT / "scripts/codex-v4-sandbox"

# Executed by the resolved Python runtime inside the sandbox. Every assertion
# contributes to the final exit status, including expected command failures.
PROBE = r"""
import errno, json, os, socket, subprocess, sys
from pathlib import Path
workspace, outside, outside_write, slash_tmp, tmpdir, port = sys.argv[1:]
os.chdir(workspace)
checks = {}
def denied(name, operation):
    try:
        operation()
    except OSError as exc:
        checks[name] = exc.errno in (errno.EPERM, errno.EACCES)
    else:
        checks[name] = False

def write_access(path):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT, 0o600)
    os.close(fd)

for fixture, expected_code, expected_status in (("valid", 0, "valid"), ("invalid", 1, "invalid")):
    result = subprocess.run(["/bin/sh", "structural_check/run_check.sh", "candidate/" + fixture],
                            capture_output=True, text=True)
    try:
        payload = json.loads(result.stdout)
    except ValueError:
        payload = {}
    checks[fixture + "_checker"] = result.returncode == expected_code and payload.get("status") == expected_status
for relative in ("candidate/program.json", "candidate/language.json",
                 "solver/candidate/program.json", "solver/candidate/language.json"):
    path = Path(relative)
    try:
        path.write_text("{}\n")
        checks[relative + "_writable"] = path.read_text() == "{}\n"
    except OSError:
        checks[relative + "_writable"] = False
    finally:
        if path.exists():
            path.unlink()
for relative in ("structural_check/run_check.sh", "structural_check/results/v4/protocol.json",
                 "candidate/valid/program.json", ".codex/config.toml", "evaluator.py"):
    denied(relative + "_immutable", lambda path=relative: write_access(path))
denied("outside_read_denied", lambda: Path(outside).read_bytes())
for name, path in (("outside_write_denied", outside_write), ("slash_tmp_denied", slash_tmp), ("tmpdir_denied", tmpdir)):
    denied(name, lambda path=path: write_access(path))
with socket.socket() as connection:
    connection.settimeout(2)
    denied("network_denied", lambda: connection.connect(("127.0.0.1", int(port))))
print(json.dumps({"passed": all(checks.values()), "checks": checks}, sort_keys=True))
sys.exit(0 if all(checks.values()) else 1)
"""


def _exercise_preflight(workspace: Path) -> dict:
    """Run enforcement probes and remove only fixture-owned files."""
    workspace = workspace.resolve()
    if not os.environ.get("TMPDIR"):
        raise ValueError("TMPDIR is required for the sandbox preflight")
    wrapper = runpy.run_path(str(WRAPPER))
    wrapper["_validate_workspace"](workspace)
    allowed_paths = [
        workspace / relative
        for relative in (
            "candidate/program.json",
            "candidate/language.json",
            "solver/candidate/program.json",
            "solver/candidate/language.json",
        )
    ]
    if any(path.exists() or path.is_symlink() for path in allowed_paths):
        raise ValueError("preflight requires synthetic fixture with empty probe paths")
    home = workspace / ".codex-driver-home" / f"preflight-{uuid4().hex}"
    home.mkdir(parents=True)
    config = home / "config.toml"
    config.write_text('approval_policy = "never"\nweb_search = "disabled"\n')
    wrapper["_install_profile"](config)
    manifest_path = workspace / "structural_check/manifest.json"
    manifest = json.loads(manifest_path.read_text())
    immutable_paths = [
        workspace / "structural_check" / path for path in manifest["files"]
    ]
    immutable_paths += [manifest_path, workspace / ".codex/config.toml"]
    immutable_paths += sorted((workspace / "candidate").rglob("*.json"))
    before = {
        str(path): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in immutable_paths
    }
    # Both allowed roots exist before execution; creating arbitrary directories
    # is intentionally outside the worker's permissions.
    solver = workspace / "solver/candidate"
    solver.mkdir(parents=True, exist_ok=True)
    name = f"v4-preflight-{uuid4().hex}"
    outside = workspace.parent / f"{name}-read"
    probes = [
        workspace.parent / f"{name}-write",
        Path("/tmp") / name,
        Path(os.environ["TMPDIR"]) / name,
        workspace / "evaluator.py",
    ]
    if any(path.exists() for path in [outside, *probes]):
        raise ValueError("preflight probe path already exists")
    outside.write_text("synthetic sandbox canary\n")
    executable = shutil.which("codex")
    if not executable:
        outside.unlink()
        raise FileNotFoundError("Codex CLI unavailable")
    result = {"passed": False, "checks": {}}
    env = dict(os.environ, CODEX_HOME=str(home), HOME=str(home.parent))
    try:
        with socket.socket() as listener:
            listener.bind(("127.0.0.1", 0))
            listener.listen(1)
            command = [
                str(WRAPPER),
                "sandbox",
                "-C",
                str(workspace),
                "--",
                manifest["launcher_python_executable"],
                "-IB",
                "-c",
                PROBE,
                str(workspace),
                str(outside),
                *(str(path) for path in probes[:3]),
                str(listener.getsockname()[1]),
            ]
            completed = subprocess.run(
                command,
                env=env,
                capture_output=True,
                text=True,
                timeout=60,
                check=False,
            )
        try:
            result = json.loads(completed.stdout)
        except ValueError:
            result = {"passed": False, "checks": {}}
        if not isinstance(result, dict) or not isinstance(
            result.get("checks", {}), dict
        ):
            raise TypeError("sandbox probe returned a malformed report")
        expected = {
            "valid_checker",
            "invalid_checker",
            "outside_read_denied",
            "outside_write_denied",
            "slash_tmp_denied",
            "tmpdir_denied",
            "network_denied",
            *(
                path.relative_to(workspace).as_posix() + "_writable"
                for path in allowed_paths
            ),
            *(
                path + "_immutable"
                for path in (
                    "structural_check/run_check.sh",
                    "structural_check/results/v4/protocol.json",
                    "candidate/valid/program.json",
                    ".codex/config.toml",
                    "evaluator.py",
                )
            ),
        }
        checks = result.get("checks", {})
        complete = set(checks) == expected and all(
            value is True for value in checks.values()
        )
        checks["complete_probe_report"] = complete
        result["checks"] = checks
        checks["sandbox_command_succeeded"] = completed.returncode == 0
        checks["immutable_files_unchanged"] = all(
            path.is_file()
            and hashlib.sha256(path.read_bytes()).hexdigest() == before[str(path)]
            for path in immutable_paths
        )
        checks["outside_canary_unchanged"] = (
            outside.read_text() == "synthetic sandbox canary\n"
        )
        checks["no_probe_writes"] = not any(
            path.exists() for path in [*probes, *allowed_paths]
        )
        result.update(
            passed=bool(checks) and all(checks.values()),
            command=command,
            exit_code=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
            codex_version=subprocess.check_output(
                [executable, "--version"], text=True
            ).strip(),
            permission_profile=wrapper["PROFILE"],
            config_sha256=hashlib.sha256(config.read_bytes()).hexdigest(),
            bundle_manifest_sha256=hashlib.sha256(
                manifest_path.read_bytes()
            ).hexdigest(),
            wrapper_sha256=hashlib.sha256(WRAPPER.read_bytes()).hexdigest(),
        )
    except (OSError, TypeError, ValueError, subprocess.SubprocessError) as exc:
        result = {
            "passed": False,
            "checks": {},
            "error": f"{type(exc).__name__}: {exc}",
        }
    finally:
        outside.unlink(missing_ok=True)
        for path in [*probes, *allowed_paths]:
            path.unlink(missing_ok=True)
    return result


def run_preflight(workspace: Path, evidence: Path) -> dict:
    """Persist setup failures as well as probe failures; never start a model."""
    evidence = evidence.absolute()
    if evidence.exists():
        raise ValueError("preflight evidence must be new")
    try:
        result = _exercise_preflight(workspace)
    except (
        OSError,
        TypeError,
        ValueError,
        KeyError,
        subprocess.SubprocessError,
    ) as exc:
        result = {
            "passed": False,
            "checks": {},
            "error": f"{type(exc).__name__}: {exc}",
        }
    evidence.parent.mkdir(parents=True, exist_ok=True)
    evidence.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--workspace", required=True, type=Path)
    parser.add_argument("--evidence", required=True, type=Path)
    args = parser.parse_args()
    from experiments.v4_native_check_fixture import EVIDENCE_ROOT, _build_workspace

    workspace = args.workspace.expanduser().absolute()
    evidence = args.evidence.expanduser().absolute()
    if not evidence.is_relative_to(EVIDENCE_ROOT) or evidence.exists():
        raise ValueError("evidence must be new and inside the ignored V4 evidence root")
    _build_workspace(workspace, args.run_id)
    result = run_preflight(workspace, evidence)
    print(json.dumps({key: result[key] for key in ("passed", "checks")}))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
