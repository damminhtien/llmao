# V4 artifact locations

V4 is a frozen exploratory research study. Start with the
[scientific report](../../reports/v4/V4_EVOLVING_BIAS_LANGUAGE.md)
and [reproducibility guide](../REPRODUCIBILITY.md#frozen-v4-exploratory-release).

## Repository layout

| Location | Contents moved from the repository root |
|---|---|
| `docs/v4/` | Four protocol, design, and sandbox documents |
| `reports/v4/` | Nine historical pilot reports and response plans |
| `configs/v4/contracts/` | Five frozen contracts and their five checksum sidecars |
| `configs/v4/` | Initial-program manifest and checksum sidecar |

Library code remains in `src/bias_optimizer/v4/`; orchestration scripts remain
in `experiments/v4_*.py`. Current script defaults and test fixtures use the new
locations. This organization does not authorize another research run.

## Historical paths and independent audit

The original 25 root files retain their exact bytes. The
[release relocation index](ARTIFACT_LOCATIONS.json) records their original paths,
current paths, sizes, and SHA-256 hashes. Later cross-version document moves are
tracked in [`../VERSION_ARTIFACT_LOCATIONS.json`](../VERSION_ARTIFACT_LOCATIONS.json). The current
[evidence manifest](../../reports/v4/evidence/V4_EVIDENCE_MANIFEST.json) uses
`path` for the current checkout and `release_tag_path` for relocated files in
the original release.

The 25 release artifacts retain their original bytes. Historical documents and
contracts retain their recorded paths, source hashes, and commit pins. Resolve
those references in the original checkout at `v4-exploratory-final`; use the
release index or the cross-version document index to find relocated files. Current path adapters do not make the current checkout
satisfy historical source pins; their validators remain strict.

From the repository root, verify every relocation without loading data or
running an experiment:

```sh
python3 - <<'PY'
import hashlib
import json
import subprocess
from pathlib import Path

index = json.loads(Path('docs/v4/ARTIFACT_LOCATIONS.json').read_text())
for item in index['artifacts']:
    current = Path(item['path']).read_bytes()
    original = subprocess.check_output([
        'git', 'show', f"{index['original_tag']}:{item['original_path']}"
    ])
    assert current == original, item['path']
    assert len(current) == item['size_bytes'], item['path']
    assert hashlib.sha256(current).hexdigest() == item['sha256'], item['path']
print(f"Verified {len(index['artifacts'])} unchanged relocated artifacts")
PY
```

The immutable tag still points to `36ea8f5016007455e342d387ffda00bb64666f95`.
Its original layout, report, manifest, and source remain available through Git.
