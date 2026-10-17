# Current state

Updated: 2026-10-17

## Completed

- The coding-agent workflow was externalized to `.agent/` and documented in `docs/AGENT_WORKFLOW.md`.
- V4 baseline, candidate/evaluator boundaries, Phase 9 smoke, and Phase 11 lineage tooling are recorded as complete in `TODO.md`.
- Earlier Phase 10 pilots and follow-ups remain failed exploratory evidence. Their candidates, budgets, transcripts, contracts, and archives were preserved without repair or rescoring.
- Data-free native checker and sandbox fixtures passed, including real-runner lineage, strict workspace permissions, and tmux-output capture.
- Contract `V4_FOLLOWUP_REPAIR_CONTRACT_20261015-04.json` was frozen at SHA-256 `17c0697fb7ab535fb65381cf804bcb68b8bc6e7d57232569fa055bfdd6dae2c6` and passed `--validate-only`.
- Pilot `20261015-04` passed every contracted exploratory gate: 10/10 valid stage-one proposals, 10 distinct expanded programs, 10/10 correct lineage links, all 3 introduced macros used by their introducers, and `path_length_histogram` used by descendants 5, 8, and 10. All ten native transcripts and 257 collector-referenced archive files verify. Runtime and post-run boundary checks found no violation. This is feasibility evidence only; it is not discovery or primary evidence.
- Protocol v10 (SHA-256 `ef4050aa854baa0aefd0273c5ed5077b2f9ba6e4200dff7084d10668da54610d`) and five seed contracts were frozen; the five Phase 12 runs were started.
- The V4 artifact-storage audit and target design are documented in `docs/V4_ARTIFACT_STORAGE_ARCHITECTURE.md`.
- `V4_PRIMARY_DESIGN_V11.md` reduces the planned search count from 135 to 25 while retaining five independent seeds and existing per-run budgets. It omits semantic ablation, cross-dataset transfer, and Level B synthesis; protocol/contracts are still pending.
- The shared V4 artifact-path resolver now constrains the V4 writer CLIs and fixture entry points; new fixture scratch and the V11 MNIST cache are rooted under `results/v4/`. Unit coverage rejects out-of-root and symlink-escape paths. Live sandbox and native-fixture evidence is still pending.

## Current

- **M2.1 — V4 artifact storage cutover (implementation complete; live sandbox
  and fixture gates pending).** Primary Phase 12 run roots, contracts, and
  evidence are under the LLMAO checkout. Historical native checker/EvE fixture
  caches and the v10 MNIST cache remain in place. New fixture scratch,
  persistent V4 outputs, and the V11 MNIST cache use `results/v4/`; the
  sandbox must prove that workers cannot read the dataset. The pinned EvE
  checkout/runtime and user-managed credentials remain external inputs. See
  `docs/V4_ARTIFACT_STORAGE_ARCHITECTURE.md` for the path contract.
- **M2.2 — Reduced V11 scope (design complete; protocol/contracts pending).**
  Keep five discovery seeds and the original per-run budgets; run four matched
  Phase 14 conditions across five seeds. The total falls from 135 to 25 search
  runs. Semantic ablation, transfer, and Level B are omitted; Phases 16, 18,
  and 19 use existing results only.
- All five v10 run roots record `run_state.json` status `running` and have no
  final `run_manifest.json`. No Phase 12 runner or tmux server is currently
  active. Treat these runs as incomplete; do not collect them or infer a
  completed result from the stale state field. Their contracts pin LLMAO commit
  `8d0944f231b8882159f16248bc752014bc343341`; resuming them requires that exact
  checkout and the original paths.

## Next

1. Run the final unit, lint, compile, and Graphify checks; inspect and commit
   the path cutover plus the V11 design amendment.
2. Generate protocol v11 from the clean commit, build its checker bundle, and
   run the 22-check sandbox preflight plus the data-free native fixture.
3. Freeze and validate five new V11 seed contracts, then launch Phase 12 under
   protocol-scoped roots. Do not resume or pool incomplete v10 runs.

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
  rule, AUC bounds, and primary statistics. Protocol v10 was subsequently
  generated with SHA-256
  `ef4050aa854baa0aefd0273c5ed5077b2f9ba6e4200dff7084d10668da54610d`.
- Never access official test data before the applicable frozen-language evaluation gate.
- Launch guidance does not require account-usage snapshots or Plus allowance
  checks; do not upgrade or use paid credits.
- V10 seed run states are stale `running` snapshots without final manifests or
  live runner processes. Preserve their partial files and close their status
  only after a separate filesystem/trajectory audit.

## Validation

- Pilot contract `-04` SHA-256: `17c0697fb7ab535fb65381cf804bcb68b8bc6e7d57232569fa055bfdd6dae2c6`.
- Pilot archive manifest SHA-256: `d135dbf93ba84ed255c5b9f5c235253e9d50c3cbd708eb324430e9700b741e6b`; gate audit SHA-256: `d9ebea417087d2d4d8a321fc2f07af0b99fd818bd56ad50225b59df201e75612`.
- The original collector manifest is separately preserved and hashed; all 257 referenced records verified before finalization.
- The ten rollout telemetry rows stayed below the 3600-second cap; maximum observed rollout was 345.246619 seconds. Telemetry's `agent_turns` field remained zero and does not independently count native model turns; the driver configuration retained the 80-turn cap.
- The frozen evaluator returned only `stage_one_only` scores with `discovery_ready=false`; no discovery fitness or official-test result exists.
- The launcher runtime checks observed ten structural bundles, no `stop_reason`, no tmux failures, a passing fresh-G0 check, and no post-run protected-boundary violation.
- The v10 contract audit confirmed five contracts share the protocol hash above.
  Their run-state snapshots report 407–418 adaptive attempts, but all remain
  `running` without final manifests; no runner process or tmux server is live.
- The storage audit found two persistent fixture workspace caches and the v10
  MNIST cache outside the checkout. New fixtures and MNIST cache use
  `results/v4/`; no historical cache contents were moved or deleted.
- Do not upgrade or use paid credits.
- Current-turn implementation validation: Ruff clean; compileall clean; all
  168 `tests/unit/test_v4_*.py` checks passed; `git diff --check` clean.
- `graphify update .` completed; generated `graphify-out/` remains ignored.
- Root-README overlay fix `f95fa0a`: 7 focused primary-runner tests passed;
  Ruff and `compileall` passed. v8's fresh fixture and five contracts then
  passed before its interpreter-path failure.
- Evaluator launcher fix `8e61a41`: all 8 focused primary-runner tests passed;
  Ruff, `compileall`, `git diff --check`, and `graphify update .` passed.
  Protocol v10's fresh sandbox/native-fixture gates passed before its contracts
  and runs were started.
- Preregistration finalizer fix `da29fcb`: 12 focused finalizer/runner tests
  passed; Ruff, `compileall`, `git diff --check`, and `graphify update .`
  passed. Protocol v10 was generated and its five seed runs remain incomplete.
