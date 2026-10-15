# Current state

Updated: 2026-10-15

## Completed

- The coding-agent workflow was externalized to `.agent/` and documented in `docs/AGENT_WORKFLOW.md`.
- V4 baseline, candidate/evaluator boundaries, Phase 9 smoke, and Phase 11 lineage tooling are recorded as complete in `TODO.md`.
- The Phase 10 exploratory pilot failed its valid-candidate gate (6/10 valid; 8/10 required). The follow-up pilot also failed: it had no descendant macro use and included noncandidate temporary writes. Both outcomes remain failed exploratory evidence.
- The data-free native checker and sandbox fixtures `20261015-native-boundary-04` and `20261015-native-boundary-05` passed. They prove their own checker and OS-denial behavior, not enforcement in a later scientific pilot.
- Added a separately hashed repair contract, exact worker guidance, runtime-bound immutable overlay, G0 seed monitoring, and post-run collector evidence. The 2026-10-15 repair pilot completed ten proposal slots but failed all ten candidate-context validations; its archive and final report remain failed evidence.

## Current

- **M1 — Respond to the failed exploratory follow-up.** The 20261015-02 contract was frozen and validated, then its ten-proposal exploratory pilot ran without replacements and failed 0/10 candidate-context validations. All ten candidates kept G0's parent hash. Nine later attempts failed at `tmux respawn-pane`; no pilot JSONL transcripts were captured and the error artifacts omit stdout/stderr. A post-run scan found no monitored boundary violation across ten structural bundles and no fresh-G0 mismatch, but the boundary gate remains incomplete without transcripts. The finalized archive is `results/v4/phase10_followup/archive/repair_followup_20261015-02/`; its manifest SHA-256 is `cd059044554c7a83a26499e759c7ddcf9026d54e886c49a104c1f2f7421b9f08`. Both earlier failed pilots remain unchanged.
- Phase 0 final preregistration is incomplete. The canonical protocol remains a draft; Phase 12 discovery and primary evaluation have not run.

## Next

1. Follow `V4_FOLLOWUP_REPAIR_RESPONSE_PLAN_20261015-02.md`: exercise the lineage handoff through the real EvE runner in a data-free fixture, preserve one JSONL transcript per invocation, and capture stdout/stderr for each tmux failure.
2. Preserve the nine `tmux respawn-pane` failures in the 20261015-02 archive; do not infer their cause or reuse its proposals.
3. Freeze another contract only after the new data-free gates pass. No live Plus usage check is required; do not use paid credits, plan upgrades, or rate-limit resets.
4. Resolve all Phase 0 decisions and produce a verified final protocol hash before Phase 12.

## Known issues

- No pilot has established genuine macro reuse by descendants under the follow-up contract.
- The latest repair attempt had 0/10 valid proposals: its candidates kept the G0 seed's parent hash instead of the selected prefill's language hash.
- The 20261015-01 repair attempt's attempts 2–10 failed in `tmux respawn-pane` and had no pilot JSONL transcripts; its protected-boundary gate remains incomplete.
- The latest run repeats the parent-hash mismatch: ten archived candidates have parent hash `34053b62a917cb7f19b572a4458440972350ea800391fdeba2d3f624cc331b2f`, while the selected lineage state hash is `5ba1e2f9e0b1d45a4e0c6fa9825491f83e169bae43bde63fe03863008315e765`.
- The nine archived tmux errors retain the failing command and exit status but no stdout/stderr; the root cause remains unknown.
- No primary discovery, frozen G*, primary evaluation, or final statistical result exists yet.
- Never access official test data before the applicable frozen-language evaluation gate.

## Validation

- The focused lineage, fixture, and sandbox tests pass (26 tests); Ruff, `py_compile`, and `git diff --check` pass.
- Data-free fixture `20261015-native-sequential-03` passes 21 preflight and 44 native checks and records two sequential transcripts. The earlier failed archives have 218 and 211 verified records. The 20261015-02 pilot archive has 208 verified records and a matching manifest sidecar.
- Contract `V4_FOLLOWUP_REPAIR_CONTRACT_20261015-02.json` passed `--validate-only`; it pinned the fresh run paths and was used for the ten-proposal run. The official test split remained disabled by the pinned evaluator.
- Post-run boundary audit checked ten structural bundles and returned no violation; fresh G0 also matched its contract. Missing pilot transcripts leave the full boundary gate incomplete.
- For preregistration, verify the pinned sources/configuration, canonical protocol contents, common initial-program digest, and protocol SHA-256 before discovery.
- The user confirmed sufficient resources. No live Plus usage check was performed or required; retain the no-upgrade/no-paid-credit policy.
