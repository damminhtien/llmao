# Current state

Completed:

- V4's README and final report lead with the two partial discovery spotlights.
  E1–E4 remain separate pilot-language diagnostics with no causal efficacy claim.
- Added docs/V4_MERGE_READINESS.md and corrected reproduction/navigation text.
- Updated the evidence inventory to 99 artifacts and documented the baseline
  index exception. The original tagged inventory remains intact (98/98).
- Preserved source code, tests, scientific protocols, datasets, historical run
  artifacts, and v4-exploratory-final at 36ea8f5016007455e342d387ffda00bb64666f95.

Validation:

- Existing focused deterministic suite: 208 passed in 6.94 seconds.
- Six protocol hashes match; trajectory counts, score maxima, macro introduction
  events, and states match the saved revision-14 JSONL records.
- Baseline protection: 85/86 current hashes match. The sole change is the reports
  navigation index; its original bytes match at baseline commit ea6e1d6.
- The excluded 793,506,639-byte seed-1101 final manifest matches its recorded hash.
- 84 local edited Markdown link targets exist; diff whitespace check passed.
- Freshly fetched origin/main at ea6e1d6 is an ancestor; merge-tree found no
  conflicts. No full-suite or remote CI result is claimed.

Known issues:

- E1 stopped at 19/20 attempts because of the final-slot batch defect.
- Both spotlight trajectories are incomplete, with recorded parent-language
  hash failures; seed 1202 has no final manifest. No G* or fresh-search result.
- The release contains summary evidence, not every native worker replay bundle.

Current: spotlight narrative and integration preparation complete. All 99
current artifact hashes and the manifest sidecar match. The task is committed
as one editorial change with the integration handoff.
Next: integrate this branch into main when requested; preserve source history
and the existing tag. No merge or remote publication is claimed here.
No LLM, research run, new scientific evaluation, or official-test loader was
invoked. V4 remains frozen; no research continuation is scheduled.
