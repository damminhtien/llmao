# Current state

V4 remains closed as a frozen exploratory study. This follow-up clarifies naming
and presents preserved partial discovery evidence from primary-protocol revision
14. It adds no run, score, or protocol change.

## Findings carried forward

- The 25-run primary design specified by `v4-primary-11` is incomplete.
- Under `v4-primary-14`, seed 1101 records 103 scored adaptive proposals,
  436 candidate-context validation failures, and a best recorded discovery
  fitness of 0.907394. Seed 1202 records 131 scored proposals, 89 such failures,
  and a best recorded fitness of 0.910471. Both trajectories are incomplete and
  neither reaches the planned candidate-AUC horizon.
- The revision-14 trajectories also record candidate-context failures caused by
  a parent-language hash mismatch. The logs show the rejection, but do not
  identify which component produced the mismatch.
- The shared optimizer's one-attempt remainder bug remains the blocking
  correctness defect for E1; it is reported but not repaired or rerun.
- The local `v4-exploratory-final` tag remains at the original frozen closure
  commit. The current branch carries the post-tag documentation clarification
  and updated checksums.

## Validation

- Current evidence manifest and all 98 artifact hashes verified.
- Manifest trajectory summaries match the preserved revision-14 JSONL records.
- `git diff --check` passed. No tests or scientific evaluations were rerun for
  this documentation-only follow-up.
