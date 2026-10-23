# Current state

Completed: V4 repository layout cleanup on main, recorded in the containing
cleanup commit. Previous publication state is archived under
.agent/archive/2026-10-23-v4-layout-cleanup/.

- Relocated 25 root V4 artifacts into docs/v4, reports/v4, configs/v4, and
  configs/v4/contracts. No V4-prefixed files remain at root.
- Preserved all 25 artifact bytes; original tag paths and hashes are indexed
  in docs/v4/ARTIFACT_LOCATIONS.json and the current evidence manifest.
- Updated ten experiment scripts, four test modules, and current navigation.
  Ten source ASTs match the previous commit after mapped path normalization.
- Focused local suite: 208 passed in 6.93 seconds. Current inventory: 133/133;
  original tagged inventory: 98/98. Checked 77 current local link targets.
- Baseline remains 85/86, with the previously documented reports/README.md
  navigation exception verified at its original baseline commit.
- graphify update . completed using code extraction only; output stays ignored.
- Annotated v4-exploratory-final tag object remains
  22a000237e1a7656ffed742787b69f674447fc93, targeting
  36ea8f5016007455e342d387ffda00bb64666f95.

Known issues: the documented E1 final-slot defect and incomplete primary
campaign remain. Historical contracts retain their embedded paths and strict
source pins; reproduce them in the original tag checkout. No scientific
protocol contents, results, or statistical criteria changed. No model, search,
scientific evaluation, or official-test loader was invoked.

Next: no research work. Cleanup is committed locally; a separate push of this
cleanup has not been performed. Original published tag remains immutable.
