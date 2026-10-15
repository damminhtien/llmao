# Current state

Updated: 2026-10-15

## Completed

- The coding-agent workflow was externalized to `.agent/` and documented in `docs/AGENT_WORKFLOW.md`.
- V4 baseline, candidate/evaluator boundaries, Phase 9 smoke, and Phase 11 lineage tooling are recorded as complete in `TODO.md`.
- The Phase 10 exploratory pilot failed its valid-candidate gate (6/10 valid; 8/10 required). The follow-up pilot also failed: it had no descendant macro use and included noncandidate temporary writes. Both outcomes remain failed exploratory evidence.
- The data-free native checker and sandbox fixture `20261015-native-boundary-04` passed. It does not prove enforcement during a later scientific pilot. Digests and limits are recorded in `V4_SANDBOX_REPAIR.md`.

## Current

- **M1 — Respond to the failed exploratory follow-up.** The fixture passed, but its launcher/runtime/profile/source digests and evidence still need to be bound into a new pilot contract. The Scalar/Vector and descendant-reuse requirements in `V4_FOLLOWUP_RESPONSE_PLAN.md` also remain launch work.
- Phase 0 final preregistration is incomplete. The canonical protocol remains a draft; Phase 12 discovery and primary evaluation have not run.

## Next

1. Read `V4_FOLLOWUP_RESPONSE_PLAN.md` and the remaining-gates section of `V4_SANDBOX_REPAIR.md`.
2. Resolve the listed checker type contracts and descendant-reuse guidance without changing either failed pilot or its records.
3. Add the required worker instruction for checker failures and create a new, separate exploratory contract binding the native fixture evidence and exact launcher/runtime/profile/source digests; verify its hash and fresh G0 initialization before any run.
4. Require a successful ten-proposal pilot with at least eight distinct valid expanded ASTs, genuine descendant macro use, all other original gates, and zero noncandidate writes. Do not replace proposals. If it fails, preserve the result and write a new response plan.
5. Resolve all Phase 0 decisions and produce a verified final protocol hash before Phase 12.

## Known issues

- No pilot has established genuine macro reuse by descendants under the follow-up contract.
- Native transcripts from the follow-up recorded writes outside the candidate-file boundary; the later data-free fixture is a remediation check, not pilot evidence.
- No primary discovery, frozen G*, primary evaluation, or final statistical result exists yet.
- Never access official test data before the applicable frozen-language evaluation gate.

## Validation

- This documentation-only workflow change passed `git diff --cached --check`; no tests were run because no code changed.
- For M1, use the data-free native integration and preflight procedure documented in `V4_SANDBOX_REPAIR.md`, then independently audit the full native transcripts and filesystem effects.
- For preregistration, verify the pinned sources/configuration, canonical protocol contents, common initial-program digest, and protocol SHA-256 before discovery.
- Recheck live account, allowance, usage, run estimate, and cleanup reserve immediately before any future model run; stop at the ordinary allowance limit.
