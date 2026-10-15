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
  pins, and contract tooling are implemented. Protocols v1-v4 and their
  evidence are retained. V1 exposed an OmegaConf configuration-key collision;
  v2 exposed a missing context-builder `--protocol` option; v3 lost the pinned
  README/AGENTS overlay. Those three stopped before worker/model or data
  access. V4 passed both 21-check preflight and the native lineage fixture
  (7/7 checks); contract freezing then exposed an assumption that `uv.lock`
  exists. The optional-lock fix is in the current implementation; protocol v5
  and fresh contract-launch evidence remain to be frozen and validated.

## Next

1. Preserve protocols v1-v4 and their evidence as versioned records.
2. Generate versioned protocol v5 with implementation/configuration hashes,
   its common initial-program digest, and an explicit supersedes link.
3. Pass fresh v5 sandbox and native-fixture gates, freeze one contract for
   each preregistered seed, and validate all contracts before launch.

## Known issues and boundaries

- Earlier Phase 10 attempts and contract `-02` remain failed exploratory evidence; contract `-03` remains a pre-worker startup failure. Contract `-04` does not replace or rewrite them.
- Pilot `-04` emitted nonfatal macOS `xcode-select` errors from worker `git status`/`git diff` calls and denied shell here-document temporary-file attempts. Candidate completion patches remained limited to the two permitted files, and the runtime boundary scan passed. Preserve this environment diagnostic if worker inspection changes are made.
- No primary discovery, frozen G*, primary evaluation, or final statistical result exists yet.
- Protocol v1 digest `ac70e832f6475f134f390bf2ac8fb64ea0814becbb71380d46277db56f4200c4`
  and v2 digest `a84839af3984b232485ed00e3d27e6d8d844ffd1cdd089fef7f3733802fc7c69`
  and v3 digest `c694fc27634a93a0096581f4631ce8b3893d22830bc719495b415ebd5c9967f6`
  and v4 digest `f50e59920eccb66527ad9847c4485b7796d0b58533149f76ef3cd04686a12ed6`
  are retained. V1-v3 stopped before a native worker/model call. V4 passed
  21/21 sandbox checks and all 7 lineage checks with a single synthetic native
  handoff and no dataset evaluation. Contract freezing created no contracts:
  it stopped because this repository has no `uv.lock`, which the freezer
  incorrectly treated as required.
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
  155 `tests/unit/test_v4_*.py` checks passed; `git diff --check` clean.
- `graphify update .` completed; generated `graphify-out/` remains ignored.
