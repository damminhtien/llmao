"""Primary launch provenance handles repositories without a uv lock file."""

import hashlib

from experiments.v4_primary_contract import optional_sha256_file


def test_optional_sha256_file_distinguishes_absent_from_pinned_file(tmp_path):
    path = tmp_path / "uv.lock"
    assert optional_sha256_file(path) is None

    path.write_bytes(b"dependency lock")
    assert optional_sha256_file(path) == hashlib.sha256(b"dependency lock").hexdigest()
