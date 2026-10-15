# Current state

Updated: 2026-10-15

## Completed

- The coding-agent workflow was externalized to `.agent/` and documented in `docs/AGENT_WORKFLOW.md`.
- V4 baseline, candidate/evaluator boundaries, Phase 9 smoke, and Phase 11 lineage tooling are recorded as complete in `TODO.md`.
- The Phase 10 exploratory pilot failed its valid-candidate gate (6/10 valid; 8/10 required). The follow-up pilot also failed: it had no descendant macro use and included noncandidate temporary writes. Both outcomes remain failed exploratory evidence.
- The data-free native checker and sandbox fixtures `20261015-native-boundary-04` and `20261015-native-boundary-05` passed. They prove their own checker and OS-denial behavior, not enforcement in a later scientific pilot.
- Added a separately hashed repair contract, exact worker guidance, runtime-bound immutable overlay, G0 seed monitoring, and post-run collector evidence. The 2026-10-15 repair pilot completed ten proposal slots but failed all ten candidate-context validations; its archive and final report remain failed evidence.

## Current

- **M1 — Respond to the failed exploratory follow-up.** Contract and native fixture gates passed, but the new pilot failed 0/10 proposal validations and did not capture pilot JSONL transcripts. See `V4_FOLLOWUP_REPAIR_REPORT.md` and `V4_FOLLOWUP_REPAIR_RESPONSE_PLAN.md`. M1 remains open.
- Phase 0 final preregistration is incomplete. The canonical protocol remains a draft; Phase 12 discovery and primary evaluation have not run.

## Next

1. Read `V4_FOLLOWUP_REPAIR_REPORT.md` and `V4_FOLLOWUP_REPAIR_RESPONSE_PLAN.md`; keep the archived run immutable.
2. Clarify that `parent_language_hash` must equal the selected prefill's `lineage_state.json["language_hash"]`, then add a data-free context-construction check for that handoff.
3. Reproduce two sequential native driver launches in a data-free fixture, capture the exact `tmux respawn-pane` failure details, and require one JSONL transcript per invocation before considering another pilot.
4. Do not launch another scientific pilot automatically. A later run needs all response-plan gates, a new contract, unused paths, and fresh ordinary-allowance verification.
5. Resolve all Phase 0 decisions and produce a verified final protocol hash before Phase 12.

## Known issues

- No pilot has established genuine macro reuse by descendants under the follow-up contract.
- The latest repair attempt had 0/10 valid proposals: its candidates kept the G0 seed's parent hash instead of the selected prefill's language hash.
- Attempts 2–10 failed in `tmux respawn-pane`; no pilot JSONL transcripts were captured, so the protected-boundary gate is incomplete despite no supervisor-reported forbidden marker.
- No primary discovery, frozen G*, primary evaluation, or final statistical result exists yet.
- Never access official test data before the applicable frozen-language evaluation gate.

## Validation

- Repair-contract source changes passed Ruff, `py_compile`, `git diff --check`, Hydra resolved-config validation, and the launcher's `--validate-only` gate. The unit suite was not run in this pass.
- The data-free native fixture passed all 21 preflight and 15 native checks. The failed pilot archive has 211 manifest-referenced records whose sizes and SHA-256 hashes were verified.
- For M1, correct the exact lineage handoff and resolve sequential tmux launch plus transcript capture in a data-free fixture before freezing another pilot contract.
- For preregistration, verify the pinned sources/configuration, canonical protocol contents, common initial-program digest, and protocol SHA-256 before discovery.
- Recheck live account, allowance, usage, run estimate, and cleanup reserve immediately before any future model run; stop at the ordinary allowance limit.
