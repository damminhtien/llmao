# Current state

Updated: 2026-10-15

## Completed

- The coding-agent workflow was externalized to `.agent/` and documented in `docs/AGENT_WORKFLOW.md`.
- V4 baseline, candidate/evaluator boundaries, Phase 9 smoke, and Phase 11 lineage tooling are recorded as complete in `TODO.md`.
- The Phase 10 exploratory pilot failed its valid-candidate gate (6/10 valid; 8/10 required). The follow-up pilot also failed: it had no descendant macro use and included noncandidate temporary writes. Both outcomes remain failed exploratory evidence.
- The data-free native checker and sandbox fixtures `20261015-native-boundary-04` and `20261015-native-boundary-05` passed. They prove their own checker and OS-denial behavior, not enforcement in a later scientific pilot.
- Added a separately hashed repair contract, exact worker guidance, runtime-bound immutable overlay, G0 seed monitoring, and post-run collector evidence. The 2026-10-15 repair pilot completed ten proposal slots but failed all ten candidate-context validations; its archive and final report remain failed evidence.

## Current

- **M1 — Respond to the failed exploratory follow-up.** The selected-prefill lineage check and sequential native fixture now pass. The fixture uses one tmux pane and one driver for two calls, captures both JSONL transcripts, and passes 21 preflight plus 44 native checks. The freezer and launcher now pin this fixture and verify both immutable failed archives. The new contract has not yet been frozen; no new scientific pilot has been launched. Keep both historical pilots failed and unchanged.
- Phase 0 final preregistration is incomplete. The canonical protocol remains a draft; Phase 12 discovery and primary evaluation have not run.

## Next

1. Freeze a new, separately hashed contract from the committed source, passing native fixture, and fresh unused paths; do not run a scientific pilot as part of freezing.
2. Preserve the original repair pilot's nine `tmux respawn-pane` failures as unresolved historical evidence; the passing fixture did not reproduce them.
3. After contract freeze, request explicit authorization before any separately contracted exploratory pilot. Do not require live Plus usage checks or use paid credits, plan upgrades, or rate-limit resets.
4. Resolve all Phase 0 decisions and produce a verified final protocol hash before Phase 12.

## Known issues

- No pilot has established genuine macro reuse by descendants under the follow-up contract.
- The latest repair attempt had 0/10 valid proposals: its candidates kept the G0 seed's parent hash instead of the selected prefill's language hash.
- Attempts 2–10 failed in `tmux respawn-pane`; no pilot JSONL transcripts were captured, so the protected-boundary gate is incomplete despite no supervisor-reported forbidden marker.
- No primary discovery, frozen G*, primary evaluation, or final statistical result exists yet.
- Never access official test data before the applicable frozen-language evaluation gate.

## Validation

- The focused lineage, fixture, and sandbox tests pass (26 tests); Ruff, `py_compile`, and `git diff --check` pass.
- Data-free fixture `20261015-native-sequential-03` passes 21 preflight and 44 native checks and records two sequential transcripts. The earlier failed archive has 218 verified records; the failed repair archive has 211 verified records. Escaping manifest paths are rejected.
- Freeze the new contract only after the implementation commit; this operation resolves configuration and evidence but does not launch a worker or access official test data.
- For preregistration, verify the pinned sources/configuration, canonical protocol contents, common initial-program digest, and protocol SHA-256 before discovery.
- The user confirmed sufficient resources. No live Plus usage check has been performed or is required; retain the no-upgrade/no-paid-credit policy.
