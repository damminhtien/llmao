# E1-PREP milestones

## M0 — Preserve prior active goal

**Complete.** Archived the previous V4 task, plan, and state under `.agent/archive/2026-10-19-e1-prep/` before changing the active objective.

## M1 — Train-only E1 data source

**Complete.** Add an explicit, pinned official-training-only IDX cache path; verify source hashes, shape, split semantics, and saved fingerprints; fail closed on unavailable or changed data. Cover the access boundary with synthetic IDX inputs.

## M2 — Minimal fixed optimizer adapter

**Complete.** Reuse the V3.2 iterative optimizer and evaluator. Restrict both proposal schemas to G0; add the three verified frozen G_pilot macros only to the treatment; expand and deduplicate by canonical G0 AST; enforce request, output, token, and proposal-attempt caps.

## M3 — Preflight and regression coverage

**Complete.** Test grammar, macro expansion, bounds, attempt accounting, common initial-score sharing, train-only access, and existing V3.2/V4 behavior. Run no-token preflight and code-only Graphify refresh. No E1 evaluation or model generation was run.

## M4 — Focused commit and stop

**Complete in this checkpoint.** The focused adapter, tests, and E1-PREP state are committed together after staged-diff review and `git diff --cached --check`. Do not run E1 as part of this task.
