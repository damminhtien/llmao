"""Export pinned structural validation sources for a read-only EvE worker."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shlex
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE_PATHS = (
    "experiments/v4_check_candidate.py",
    "src/bias_optimizer/__init__.py",
    "src/bias_optimizer/dsl/ast.py",
    "src/bias_optimizer/dsl/primitives.py",
    "src/bias_optimizer/dsl/types.py",
    "src/bias_optimizer/dsl/validator.py",
    "src/bias_optimizer/features/skeleton_graph.py",
    "src/bias_optimizer/v4/__init__.py",
    "src/bias_optimizer/v4/candidate/__init__.py",
    "src/bias_optimizer/v4/candidate/check.py",
    "src/bias_optimizer/v4/candidate/context.py",
    "src/bias_optimizer/v4/candidate/loader.py",
    "src/bias_optimizer/v4/candidate/provenance.py",
    "src/bias_optimizer/v4/candidate/schema.py",
    "src/bias_optimizer/v4/language/__init__.py",
    "src/bias_optimizer/v4/language/base_language.py",
    "src/bias_optimizer/v4/language/macro.py",
    "src/bias_optimizer/v4/language/validator.py",
)
PACKAGE_SHIMS = (
    "src/bias_optimizer/dsl/__init__.py",
    "src/bias_optimizer/features/__init__.py",
)


def build_bundle(
    destination: Path,
    *,
    repo_root: Path,
    commit: str,
    protocol_path: Path,
    protocol_sha256: str,
    python_executable: Path | None = None,
) -> dict:
    """Read source from Git objects, never from a possibly dirty working tree."""
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise ValueError("commit must be a full lowercase Git commit SHA")
    protocol = protocol_path.read_bytes()
    if hashlib.sha256(protocol).hexdigest() != protocol_sha256:
        raise ValueError("checker protocol digest mismatch")
    json.loads(protocol)
    # Resolving this symlink would select the base interpreter and lose the venv.
    python = Path(python_executable or sys.executable).expanduser().absolute()
    if not python.is_file() or not os.access(python, os.X_OK):
        raise ValueError("structural checker needs an executable project Python")
    probe = subprocess.run(
        [
            str(python),
            "-IB",
            "-c",
            (
                "import json,sys,networkx,numpy,scipy,skimage; "
                "from importlib.metadata import version; "
                "print(json.dumps({'version':list(sys.version_info[:3]), "
                "'dependencies':{name:version(name) for name in "
                "('networkx','numpy','scipy','scikit-image')}}))"
            ),
        ],
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )
    if probe.returncode:
        raise ValueError(
            f"project Python cannot import checker dependencies: {probe.stderr.strip()}"
        )
    runtime = json.loads(probe.stdout)
    if runtime["version"][:2] != [3, 14]:
        raise ValueError("structural checker requires project Python 3.14")
    contents = {}
    for relative in SOURCE_PATHS:
        result = subprocess.run(
            ["git", "-C", str(repo_root), "show", f"{commit}:{relative}"],
            check=True,
            capture_output=True,
        )
        contents[relative] = (result.stdout, "pinned_source")
    for relative in PACKAGE_SHIMS:
        contents[relative] = (
            b'"""Structural bundle: omit execution-only convenience imports."""\n',
            "package_initializer_shim",
        )
    contents["results/v4/protocol.json"] = (protocol, "checker_protocol")
    launcher = (
        "#!/bin/sh\nset -eu\n"
        'bundle_root=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)\n'
        f'exec {shlex.quote(str(python))} -IB "$bundle_root/experiments/v4_check_candidate.py" "$@"\n'
    )
    contents["run_check.sh"] = (launcher.encode(), "interpreter_launcher")
    manifest = {
        "schema_version": 1,
        "source_commit": commit,
        "protocol_sha256": protocol_sha256,
        "python_executable": str(python),
        "python_runtime": runtime,
        "worker_command": "sh structural_check/run_check.sh",
        "purpose": "data-free structural validation; no accuracy evaluation",
        "files": {
            relative: {
                "sha256": hashlib.sha256(content).hexdigest(),
                "size_bytes": len(content),
                "kind": kind,
            }
            for relative, (content, kind) in sorted(contents.items())
        },
    }
    destination.mkdir(parents=True, exist_ok=False)
    for relative, (content, _) in contents.items():
        path = destination / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
    (destination / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination", type=Path)
    parser.add_argument("--repo-root", type=Path, default=ROOT)
    parser.add_argument("--commit", required=True)
    parser.add_argument(
        "--protocol", type=Path, default=ROOT / "results/v4/protocol.json"
    )
    parser.add_argument("--protocol-sha256", required=True)
    parser.add_argument("--python-executable", type=Path, default=Path(sys.executable))
    args = parser.parse_args()
    manifest = build_bundle(
        args.destination,
        repo_root=args.repo_root,
        commit=args.commit,
        protocol_path=args.protocol,
        protocol_sha256=args.protocol_sha256,
        python_executable=args.python_executable,
    )
    print(
        json.dumps(
            {
                "source_commit": manifest["source_commit"],
                "files": len(manifest["files"]),
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
