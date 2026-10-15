"""Primary launch provenance handles repositories without a uv lock file."""

import hashlib

from experiments.v4_primary_contract import optional_sha256_file, primary_run_root


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
