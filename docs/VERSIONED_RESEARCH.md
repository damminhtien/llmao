# Versioned research documents

Version-specific documentation, reports, full records, and figures are grouped
by study. The root `README.md` and [`reports/README.md`](../reports/README.md)
remain the cross-study indexes.

| Study | Design documents | Reports and figures |
|---|---|---|
| V1 | `docs/v1/` | `reports/v1/` |
| V2 | No separate architecture document | `reports/v2/` |
| V3 | `docs/v3/` | `reports/v3/` |
| V3.1 | `docs/v3.1/` | `reports/v3.1/` |
| V3.2 | See the shared `docs/v3/` architecture and V3.2 report | `reports/v3.2/` |
| V4 | `docs/v4/` | `reports/v4/` |

Current layouts contain only the documents that exist for each study. Research
source code remains under `src/` and `experiments/`. Preserved data, protocols,
and run manifests remain under `results/`; this documentation cleanup does not
move or rewrite them.

## Relocated-file audit

[`VERSION_ARTIFACT_LOCATIONS.json`](VERSION_ARTIFACT_LOCATIONS.json) maps the
26 former document, report, and figure paths to their current paths. It records
the source commit and original Git blob hash along with the current file hash.
Some Markdown files have updated local links; those edits do not change their
scientific content. Raster figures retain their original bytes.

Run this check from the repository root to validate both sides of the mapping:

```sh
python3 - <<'PY'
import hashlib
import json
import subprocess
from pathlib import Path

index = json.loads(Path('docs/VERSION_ARTIFACT_LOCATIONS.json').read_text())
for item in index['artifacts']:
    current = Path(item['path']).read_bytes()
    original = subprocess.check_output([
        'git', 'show', f"{index['source_commit']}:{item['original_path']}"
    ])
    assert hashlib.sha256(original).hexdigest() == item['original_sha256']
    assert hashlib.sha256(current).hexdigest() == item['current_sha256']
print(f"Verified {len(index['artifacts'])} relocated documents and figures")
PY
```

Historical manifests under `results/` remain byte-for-byte unchanged. When they
name an earlier document path, use the location index to find its current
location; use the original commit recorded in the manifest for the exact
historical tree. V4's release-specific root relocation is additionally recorded
in [`v4/ARTIFACT_LOCATIONS.json`](v4/ARTIFACT_LOCATIONS.json).
