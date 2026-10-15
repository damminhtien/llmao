# Current state

Updated: 2026-10-15

## Completed

- The coding-agent workflow was externalized to `.agent/` and documented in `docs/AGENT_WORKFLOW.md`.
- V4 baseline, candidate/evaluator boundaries, Phase 9 smoke, and Phase 11 lineage tooling are recorded as complete in `TODO.md`.
- The Phase 10 exploratory pilot failed its valid-candidate gate (6/10 valid; 8/10 required). The follow-up pilot also failed: it had no descendant macro use and included noncandidate temporary writes. Both outcomes remain failed exploratory evidence.
- The data-free native checker and sandbox fixtures `20261015-native-boundary-04` and `20261015-native-boundary-05` passed. They prove their own checker and OS-denial behavior, not enforcement in a later scientific pilot.
- Added a separately hashed repair contract, exact worker guidance, runtime-bound immutable overlay, G0 seed monitoring, and post-run collector evidence. The 2026-10-15 repair pilot completed ten proposal slots but failed all ten candidate-context validations; its archive and final report remain failed evidence.
- The response fixture `20261015-real-runner-lineage-04` passed all seven lineage/context checks through EvE's real `Phase2Runner`, captured a hashed JSONL transcript, and passed the strict language-only permission probe and tmux stdout/stderr capture probe.
- Contract `V4_FOLLOWUP_REPAIR_CONTRACT_20261015-03.json` was frozen but its runner exited before creating a run directory or starting a worker because Hydra resolved `configs.eve` against the wrong `sys.path`. That startup failure is preserved; it produced zero structural bundles and no proposals.
- The traced runner now preserves EvE's module and config context. Contract `V4_FOLLOWUP_REPAIR_CONTRACT_20261015-04.json` is frozen at SHA-256 `17c0697fb7ab535fb65381cf804bcb68b8bc6e7d57232569fa055bfdd6dae2c6` and passed `--validate-only`. It pins the -03 startup failure, the 208-record -02 failed archive, native fixture `20261015-native-sequential-03`, and lineage fixture `20261015-real-runner-lineage-04`.

## Current

- **M1 — Respond to the failed exploratory follow-up.** The 20261015-02 scientific pilot remains failed at 0/10 candidate-context validations. Its nine tmux errors still lack captured output and transcripts; its archive remains unchanged. Data-free lineage, transcript, and stderr-capture gates now pass. Contract -03's Hydra startup failure was pre-worker and generated no proposals. Contract -04 is frozen and validated; its ten-proposal pilot is the next step. The -02 archive manifest remains pinned at `cd059044554c7a83a26499e759c7ddcf9026d54e886c49a104c1f2f7421b9f08`.
- Phase 0 final preregistration is incomplete. The canonical protocol remains a draft; Phase 12 discovery and primary evaluation have not run.

## Next

1. Run the separately frozen 20261015-04 ten-proposal exploratory pilot with one transcript per invocation and exact stdout/stderr for every tmux failure. Use the ordinary allowance; do not upgrade, use paid credits, or reset rate limits.
2. Audit and archive every proposal, transcript, tmux trace, G0 seed, and protected-boundary result. Keep evidence classified as exploratory; the -03 startup attempt and -02 scientific failure remain failed.
3. If the pilot fails any gate, preserve the result and follow a separately documented response. If every gate passes, close M1 without promoting the pilot to discovery evidence.
4. Resolve all Phase 0 decisions and produce a verified final protocol hash before Phase 12.

## Known issues

- No pilot has established genuine macro reuse by descendants under the follow-up contract.
- Scientific pilot -02 had 0/10 valid proposals: its candidates kept the G0 seed's parent hash instead of the selected prefill's language hash. Contract -03 stopped before a worker and is not a scientific pilot.
- The 20261015-01 repair attempt's attempts 2–10 failed in `tmux respawn-pane` and had no pilot JSONL transcripts; its protected-boundary gate remains incomplete.
- The latest run repeats the parent-hash mismatch: ten archived candidates have parent hash `34053b62a917cb7f19b572a4458440972350ea800391fdeba2d3f624cc331b2f`, while the selected lineage state hash is `5ba1e2f9e0b1d45a4e0c6fa9825491f83e169bae43bde63fe03863008315e765`.
- The nine archived tmux errors retain the failing command and exit status but no stdout/stderr; the root cause remains unknown.
- No primary discovery, frozen G*, primary evaluation, or final statistical result exists yet.
- Never access official test data before the applicable frozen-language evaluation gate.

## Validation

- The focused lineage, fixture, sandbox, launcher, and collector tests pass (44 tests); Ruff, `py_compile`, and `git diff --check` pass.
- Data-free fixture `20261015-native-sequential-03` passes 21 preflight and 44 native checks and records two sequential transcripts. The earlier failed archives have 218 and 211 verified records. The 20261015-02 pilot archive has 208 verified records and a matching manifest sidecar.
- Contract `V4_FOLLOWUP_REPAIR_CONTRACT_20261015-02.json` passed `--validate-only`; it pinned the fresh run paths and was used for the ten-proposal run. The official test split remained disabled by the pinned evaluator.
- Contract -03 startup returned exit code 1 before creating its run directory; the execution record and combined console output preserve the Hydra config-module error. A data-free `v4_eve_runner.py --cfg job --resolve` probe now succeeds through the same traced entrypoint used by contract -04.
- Contract `V4_FOLLOWUP_REPAIR_CONTRACT_20261015-04.json` passed `--validate-only`; its artifact requirements contain no account/usage snapshot requirement, and the official test split remains disabled.
- Post-run boundary audit checked ten structural bundles and returned no violation; fresh G0 also matched its contract. Missing pilot transcripts leave the full boundary gate incomplete.
- For preregistration, verify the pinned sources/configuration, canonical protocol contents, common initial-program digest, and protocol SHA-256 before discovery.
- The user confirmed sufficient resources and asked to omit Plus usage checks. No live usage check was performed; retain the no-upgrade/no-paid-credit policy.
