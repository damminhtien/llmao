# Current state

Completed: grouped versioned research documentation and reports under `docs/vN/`
and `reports/vN/` on main. The changes are recorded in the current cleanup
commit.

- Moved five root historical V1/V3 design, plan, checklist, and protocol files.
- Grouped the V1–V4 scientific reports, supplementary records, and figures under
  their version directories. The root `reports/README.md` remains the index.
- Added `docs/VERSIONED_RESEARCH.md` and a 26-entry
  `docs/VERSION_ARTIFACT_LOCATIONS.json` mapping original paths and hashes to
  current locations and hashes.
- Adapted only report/figure output or input paths in six scripts; no search,
  scoring, statistical criteria, or scientific logic changed.
- Updated the current V4 evidence manifest and checksum lists for the new report
  paths. The immutable tag remains unchanged.
- Validation: 139 Markdown links checked; relocation map 26/26; current V4
  inventory 133/133; original V4 tag inventory 98/98; baseline remains 85/86
  with the documented `reports/README.md` exception. Six edited scripts parse.
- `graphify update .` completed using code extraction only. The working graph
  remains ignored.
- No tests, research runs, figure generation, evaluation, or official-test
  loading were performed. Nothing under `results/` was modified.

No V1/V3 historical documents remain at repository root. Current V4 `ARCHITECTURE.md`
and `TODO.md` remain in the root as its active sources of truth.
