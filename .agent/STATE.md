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

- **M2 — Final preregistration and implementation pins (reopened for v8).**
  Scientific Phase 0 choices are fixed in `V4_PRIMARY_DESIGN.md`. Protocol v7
  (`fa35b0e744a659d670e73a130a871d7c0fc17411ca12e5155bd2cab06813b276`), its
  fresh 21/21 sandbox preflight, 7/7 native fixture, and five validated seed
  contracts passed. Seed 1101 then exposed a runner configuration defect:
  the actual Phase 2 workspaces had the task README only under `solver/`, while
  the evaluator requires the rendered root `README.md` to identify the selected
  prefill. Two adaptive proposals failed before context validation or scoring;
  a third partial proposal was stopped after the same terminal infrastructure
  failure. The v7 run remains incomplete and immutable under its protocol-scoped
  run root. Commit `f95fa0a` fixes the runner by materializing README, AGENTS,
  G0, and the pinned checker into a hashed per-run immutable overlay. Freeze v8
  and repeat fresh launch gates/contracts before discovery resumes.

## Next

1. Preserve protocols v1-v7, all contracts, the two failed v7 proposals, and
   the partial third-proposal transcript and token record.
2. Generate protocol v8 superseding v7 and pin the committed overlay fix.
3. Pass fresh sandbox/native-fixture gates, freeze all five seed contracts,
   and validate them before launch.

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
  Ruff and `compileall` passed. A fresh v8 native fixture remains pending.
