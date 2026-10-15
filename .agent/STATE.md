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

- **M2 — Final preregistration and implementation pins.** M1 is complete and
  the scientific Phase 0 choices are fixed in `V4_PRIMARY_DESIGN.md`. The
  primary evaluator, discovery runner, five-seed lineage collector, source
  pins, and contract tooling are implemented. The canonical primary protocol
  and Phase 12 launch evidence still need to be frozen and validated.

## Next

1. Finish source review, targeted validation, and the focused implementation
   commit.
2. Generate the versioned primary protocol with implementation/configuration
   hashes and the common initial-program digest; keep the historical pilot
   protocol unchanged.
3. Pass the 21-check sandbox preflight and the Phase 12 native lineage fixture,
   freeze one contract for each preregistered seed, and run all contracts in
   validate-only mode before launch.

## Known issues and boundaries

- Earlier Phase 10 attempts and contract `-02` remain failed exploratory evidence; contract `-03` remains a pre-worker startup failure. Contract `-04` does not replace or rewrite them.
- Pilot `-04` emitted nonfatal macOS `xcode-select` errors from worker `git status`/`git diff` calls and denied shell here-document temporary-file attempts. Candidate completion patches remained limited to the two permitted files, and the runtime boundary scan passed. Preserve this environment diagnostic if worker inspection changes are made.
- No primary discovery, frozen G*, primary evaluation, or final statistical result exists yet.
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
  148 `tests/unit/test_v4_*.py` checks passed; `git diff --check` clean.
- `graphify update .` completed; generated `graphify-out/` remains ignored.
