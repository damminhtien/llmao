# Current state

Updated: 2026-10-15

## Completed

- The coding-agent workflow was externalized to `.agent/` and documented in `docs/AGENT_WORKFLOW.md`.
- V4 baseline, candidate/evaluator boundaries, Phase 9 smoke, and Phase 11 lineage tooling are recorded as complete in `TODO.md`.
- Earlier Phase 10 pilots and follow-ups remain failed exploratory evidence. Their candidates, budgets, transcripts, contracts, and archives were preserved without repair or rescoring.
- Data-free native checker and sandbox fixtures passed, including real-runner lineage, strict workspace permissions, and tmux-output capture.
- Contract `V4_FOLLOWUP_REPAIR_CONTRACT_20261015-04.json` was frozen at SHA-256 `17c0697fb7ab535fb65381cf804bcb68b8bc6e7d57232569fa055bfdd6dae2c6` and passed `--validate-only`.
- Pilot `20261015-04` passed every contracted exploratory gate: 10/10 valid stage-one proposals, 10 distinct expanded programs, 10/10 correct lineage links, all 3 introduced macros used by their introducers, and `path_length_histogram` used by descendants 5, 8, and 10. All ten native transcripts and 257 collector-referenced archive files verify. Runtime and post-run boundary checks found no violation. This is feasibility evidence only; it is not discovery or primary evidence.

## Current

- **M2 — Final preregistration and implementation pins (reopened for v10).**
  Scientific Phase 0 choices are fixed in `V4_PRIMARY_DESIGN.md`. Protocol v8
  (`01197b83b8f945e685e91c76f3c1f0049b6797260a7c0ad602ec952857efc4bc`), its
  fresh 21/21 sandbox preflight, 7/7 native fixture, and five validated seed
  contracts passed. Seed 1101 scored the common 20-program G0 set. Adaptive
  proposals 1 and 2 then failed before context creation or primary scoring:
  `evaluate.py` resolved the contract-pinned `.venv/bin/python` symlink to base
  Python, which lacks `networkx`. Proposal 3 was stopped as a partial attempt.
  The v8 run is preserved as incomplete under its protocol-scoped run root with
  590,544 reported input-plus-output tokens. Commit `8e61a41` changes the
  adapter to validate and retain the lexical launcher path; a focused symlink
  regression test passes. Protocol v9 was generated with SHA-256
  `d907ed68bd1e14e6b49bfe8e5c91a67620ab675f60768505d978c2ce2cb98fb6`, but
  still carried six stale `pending_preregistration_decisions` entries from the
  historical pilot draft. No v9 contract or worker was launched. Commit
  `da29fcb` makes the finalizer verify the known decision inventory and remove
  it only after the final choices are integrated. Generate v10 superseding v9,
  verify an empty pending list, then repeat fresh launch gates/contracts.

## Next

1. Preserve protocols v1-v9, their contracts and launch evidence, and all
   failed/interrupted attempts; neither v8 nor v9 may be resumed/launched.
2. Generate protocol v10 superseding v9, pinning both committed fixes and
   clearing the resolved Phase 0 decision inventory.
3. Pass fresh sandbox/native-fixture gates, freeze all five v10 seed
   contracts, and validate them before starting a fresh seed-1101 run.

## Known issues and boundaries

- Earlier Phase 10 attempts and contract `-02` remain failed exploratory evidence; contract `-03` remains a pre-worker startup failure. Contract `-04` does not replace or rewrite them.
- Pilot `-04` emitted nonfatal macOS `xcode-select` errors from worker `git status`/`git diff` calls and denied shell here-document temporary-file attempts. Candidate completion patches remained limited to the two permitted files, and the runtime boundary scan passed. Preserve this environment diagnostic if worker inspection changes are made.
- No primary discovery, frozen G*, primary evaluation, or final statistical result exists yet.
- Protocol v1-v6 are retained in versioned files with their preflight,
  fixture, or contract evidence. V5 digest is
  `eccb03b493192d05cb05fd33c83568f7b13476adc2745f2382733de5f100127d`.
  V6 digest is `9c93133d948db2d2723e0b130e019e3af1dc3cbfb43acb98c28c972a155490cd`;
  its five contracts passed validate-only. Seed 1101's v5 root records the
  `_run` helper collision. Its v6 root records the base-Python import failure
  (`networkx` missing) caused by resolving the project venv symlink. Neither
  startup produced a candidate context, proposal, or discovery evaluation.
  Protocol-scoped run roots preserve both records.
- Protocol v7's seed-1101 run root is
  `results/v4/phase12/runs/discovery-1101-fa35b0e744a6/`. Attempts 1 and 2
  failed with `Phase 2 workspace is missing its rendered README`; neither
  reached candidate context or evaluator scoring. Attempt 3 was retained as
  an interrupted partial proposal with 163,548 input and 2,321 output tokens;
  its transcript SHA-256 is
  `a06b99819bcb15f94bb303be05c227e6c7ca4a6cbc85f01ee962bb4a0f879c57`.
  The three attempts total 1,471,505 reported input-plus-output tokens. The
  active Codex/tmux run was terminated after the repeated infrastructure
  failure; the checkpoint remains at completed iteration 2, and the official
  test partition was not accessed. Protocol v7 cannot be resumed after the
  pinned source change; v8 is required for a new, separately versioned run.
- Protocol v8 SHA-256 is
  `01197b83b8f945e685e91c76f3c1f0049b6797260a7c0ad602ec952857efc4bc`; its
  fresh 21/21 sandbox preflight, 7/7 native fixture, and five seed contracts
  passed. Seed 1101's v8 run root is
  `results/v4/phase12/runs/discovery-1101-01197b83b8f9/`. Its common initial
  set contains 20 G0 candidates. Adaptive attempts 1 and 2 failed context
  validation with `ModuleNotFoundError: No module named 'networkx'`: the
  evaluator resolved the pinned `.venv/bin/python` symlink to base Python.
  Attempt 1 consumed 314,577 and attempt 2 consumed 236,422 reported
  input-plus-output tokens. Attempt 3 was interrupted after 38,500 input and
  1,045 output tokens; transcript SHA-256 is
  `a4bb394c941a95b6057597245b36ee50e5a5dfb4c81d3fcb7621e7d34c417650`.
  Total usage is 590,544 tokens across three consumed attempts, with two
  completed infrastructure failures and one partial attempt. The checkpoint
  remains at two completed iterations. No adaptive candidate produced a
  context or primary score, and the official test partition was not accessed.
  Commit `8e61a41` fixes the adapter and adds a symlink-preservation regression
  test; v8 cannot be resumed after that pinned source change.
- Protocol v9 SHA-256 is
  `d907ed68bd1e14e6b49bfe8e5c91a67620ab675f60768505d978c2ce2cb98fb6`; it
  supersedes v8 but retained six stale pending-decision labels from the
  historical pilot draft. The scientific choices and implementation are
  present in the protocol, but the version does not meet Phase 0's explicit
  pending-decision acceptance gate. It is preserved unchanged and was never
  used to freeze contracts or launch workers. Commit `da29fcb` corrects the
  finalizer and adds coverage that the generated protocol clears the resolved
  inventory while retaining the frozen seeds, initial-program hash, selection
  rule, AUC bounds, and primary statistics. Protocol v10 is required.
- Never access official test data before the applicable frozen-language evaluation gate.
- Launch guidance does not require account-usage snapshots or Plus allowance
  checks; do not upgrade or use paid credits.

## Validation

- Pilot contract `-04` SHA-256: `17c0697fb7ab535fb65381cf804bcb68b8bc6e7d57232569fa055bfdd6dae2c6`.
- Pilot archive manifest SHA-256: `d135dbf93ba84ed255c5b9f5c235253e9d50c3cbd708eb324430e9700b741e6b`; gate audit SHA-256: `d9ebea417087d2d4d8a321fc2f07af0b99fd818bd56ad50225b59df201e75612`.
- The original collector manifest is separately preserved and hashed; all 257 referenced records verified before finalization.
- The ten rollout telemetry rows stayed below the 3600-second cap; maximum observed rollout was 345.246619 seconds. Telemetry's `agent_turns` field remained zero and does not independently count native model turns; the driver configuration retained the 80-turn cap.
- The frozen evaluator returned only `stage_one_only` scores with `discovery_ready=false`; no discovery fitness or official-test result exists.
- The launcher runtime checks observed ten structural bundles, no `stop_reason`, no tmux failures, a passing fresh-G0 check, and no post-run protected-boundary violation.
- Do not upgrade or use paid credits.
- Current-turn implementation validation: Ruff clean; compileall clean; all
  158 `tests/unit/test_v4_*.py` checks passed; `git diff --check` clean.
- `graphify update .` completed; generated `graphify-out/` remains ignored.
- Root-README overlay fix `f95fa0a`: 7 focused primary-runner tests passed;
  Ruff and `compileall` passed. v8's fresh fixture and five contracts then
  passed before its interpreter-path failure.
- Evaluator launcher fix `8e61a41`: all 8 focused primary-runner tests passed;
  Ruff, `compileall`, `git diff --check`, and `graphify update .` passed. A fresh
  v10 sandbox preflight/native fixture and contracts remain pending.
- Preregistration finalizer fix `da29fcb`: 12 focused finalizer/runner tests
  passed; Ruff, `compileall`, `git diff --check`, and `graphify update .`
  passed. Protocol v10 has not yet been generated.
