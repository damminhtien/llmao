# V4 integration handoff

**Disposition:** integrated into main and published as a frozen exploratory
research study. This handoff records verification and publication on
2026-10-23. The
[final report](../reports/v4/V4_EVOLVING_BIAS_LANGUAGE.md) leads with
the two preserved discovery trajectories, then uses E1–E4 to distinguish
targeted expression, selected representation quality, and observed adoption.
The primary language-utility comparison remains incomplete.

## Reading order and retained records

1. [README](../README.md) for the V1–V4 research narrative and the V4 pitch.
2. [V4 scientific report](../reports/v4/V4_EVOLVING_BIAS_LANGUAGE.md)
   for observations, interpretations, unsupported hypotheses, and untested claims.
3. [Evidence manifest](../reports/v4/evidence/V4_EVIDENCE_MANIFEST.json) for
   source revisions, training-data fingerprints, artifact hashes, and exclusions.
4. [Reproducibility](REPRODUCIBILITY.md#frozen-v4-exploratory-release) for
   deterministic audit commands and the release boundary.

Scientific protocols and historical result files retain their frozen content.
After publication, a layout cleanup relocated 25 root artifacts and updated
current source/test path references. The [location guide](v4/README.md) records
the new layout and explains historical references. Original source and tests
remain at the immutable tag. Unchecked primary milestones describe unfinished
research.

## Release and integration history

The annotated `v4-exploratory-final` tag points to
`36ea8f5016007455e342d387ffda00bb64666f95`, the original closure snapshot.
The later naming and spotlight documentation does not move that tag. The
current manifest identifies post-tag editorial files with
`included_in_release_tag: false`; their hashes describe the checked-out
documentation revision. Use `git show v4-exploratory-final:<path>` to inspect
the original tagged report or manifest.

Preparation checked a freshly fetched `origin/main` at `ea6e1d6`, an ancestor
of `v4-evolving-bias-language`, with no merge conflicts. Integration then
completed through merge commit
`44789d120481c5b98ee5384f219f08f80a9c6022`. Its tree matched the prepared study
branch at `f1cbaf48558b4b2c7e9855dd9a28c13e1205bd13` exactly. The merge
preserves the source revisions cited by the evidence manifest.

On 2026-10-23, main, the study branch, and the existing annotated tag were
pushed atomically to `https://github.com/damminhtien/llmao.git`. Their remote
identities were verified with `git ls-remote`, including the unchanged tag
target. Subsequent publication metadata is recorded after the merge; the
original tagged manifest remains the closure snapshot. This records a verified
Git publication, with no remote CI result claimed.

## Deterministic local verification

| Check | Result | Boundary |
|---|---|---|
| Existing focused V4 suite | 208 passed in 6.94 seconds | Mocked proposal clients and synthetic fixtures; local software verification |
| Current manifest sidecar and artifact inventory | All checksums match | Includes the current report and post-tag documentation |
| Original tagged evidence inventory | All hashes match the tagged files | Verifies that the original snapshot remains available |
| Baseline manifest against current checkout | 85/86 hashes match | Sole exception: the updated `reports/README.md` navigation index; original index verified at the recorded baseline commit |
| Preserved revision-14 trajectories | Counts, maxima, macro events, and states match the summary | Reads saved JSON/JSONL only; no rescoring |
| Original integration scope | Source, protocols, and result artifacts unchanged at publication | Subsequent layout cleanup adapts source/test paths; moved artifact bytes remain identical |
| Local links and diff whitespace | Checked | Reader-facing edited Markdown and `git diff --check` |

The focused test command is documented in
[Reproducibility](REPRODUCIBILITY.md#frozen-v4-exploratory-release). No LLM,
research search, scientific evaluation, official-test loader, or primary worker
was launched for this handoff. The entire repository test suite and remote CI
are outside this validation claim.

The historical baseline manifest includes the reports navigation index among
its 86 entries. That index was already edited when V4 was closed and is updated
again for the spotlight narrative. Every other protected entry still matches.
The baseline commit `ea6e1d6d268a10bdafc2061c73fcb2c694be9679` preserves the
original index with its expected hash. The current evidence manifest documents
this editorial exception and supersedes the unqualified `86/86` wording in the
original closure verification summary. The frozen baseline manifest and
original release tag retain their historical bytes.

The tracked integration diff contains selected research evidence; its largest
artifact is the approximately 1.15 MB seed-1101 trajectory. The 793 MB local
seed-1101 final manifest is excluded and hash-recorded. Dataset archives,
native worker workspaces, runtime caches, Graphify output, and environment
files are outside the tracked integration diff.

## Correctness defects and limits carried into the archive

**E1 final-slot defect:** the shared iterative optimizer sizes its batch with
`remaining_attempts // 2`. One remaining attempt produces an empty batch. The
preserved macro arm stopped at 19/20 attempts with
`optimizer_returned_no_attempts`. This blocks a full-budget E1 exhaustion
claim. The focused suite passes but does not cover that final-slot case. The
source was preserved under the frozen-study instruction.

**Primary candidate-lineage failures:** the spotlight trajectories record 436
and 89 candidate-context failures with a parent-language hash mismatch.
Their scored adaptive counts are 103 and 131, respectively; both are below
the required 180 adaptive unique-success horizon. The summary records the
evaluator rejection without attributing the originating defect from those
logs alone.

**Missing scientific evidence:** seed 1202 has no final manifest, and seed
1101's large local manifest is outside the release bundle. The bundled
trajectories do not include complete native per-candidate replay workspaces.
E1–E4 have the provenance and single-seed limits detailed in the report.
There is no selected `G*`, complete five-seed discovery table, or fresh-search
campaign. Generalization, causal abstraction utility, and improved search
efficiency are unsupported.

These defects and omissions constrain the scientific claims and any future
execution. The integration preserves the study with those limits explicitly
recorded; it does not certify the runner for another research campaign.
