# V4 Phase 10 follow-up — launch and live audit

Status: **running**, with seven completed proposals at the
2026-10-14 12:00:27 UTC snapshot. This document is not a final gate audit.
The first pilot remains failed and unchanged.

## Frozen contract and execution

- Contract: `V4_FOLLOWUP_PILOT_CONTRACT.json`.
- Contract SHA-256:
  `cf2d4aa7c4cb778e35174805c53d83a09d221a9f1335d2f1f688e1e42d7b09c2`.
- Contract commit: `33a74bf`.
- LLMAO evaluator checkout: `01f6371ded33537cb93c52b27303212db0c3a054`.
- EvE checkout: `01abaa5e33c3e0936d3fe2e250d071a746f71864`.
- Structural bundle source: `468f5043548c33526d2e3238182b70a963353ebd`.
- Base protocol SHA-256:
  `e21bd6e89c8ea90629e8a07417bdb3b007d1474ce075920d358a62e69ac2234b`.
- Executed evaluator-source SHA-256:
  `4b7b3d3b2811aeccd812f1804e2838e3a7154f489c63e0f735ade026a4111ff2`.
- Run ID:
  `run-20261014_191240_049926-llmao-v4-language-followup-20261014T1052Z-313953c7e0e7`.
- Run root:
  `/Users/macbook/Library/Caches/llmao-v4-eve-runs/20261014T1052Z-llmao-v4-language-followup`.
- Runner started: 2026-10-14 11:12:39.805 UTC; PID 19108.
- Supervisor source commit: `ad5cd84`.

The last pre-launch account check at 11:12:08 UTC confirmed ChatGPT Plus,
ordinary usage allowed, 51% used in the five-hour window, 25% in the weekly
window, and paid-credit balance zero. No paid-credit or rate-limit-reset action
was requested. The native worker turn context records `gpt-6-luna`, max effort,
approval policy `never`, workspace-write sandbox policy, and network access
false. The isolated worker configuration declares no custom model provider.

## Budget and gates

The run retains exactly ten submitted proposals plus a separately evaluated
G0 seed, one worker, zero automatic repairs, 80 turns per rollout, and a
3,600-second per-rollout timeout. Invalid, failed, and repeated proposals
count. No first-pilot program, macro, population, or guidance state was imported.

All original pilot gates apply. The follow-up also requires eight distinct
valid expanded-program hashes among the ten proposals, excluding the seed.
This is structural diversity, not semantic or statistical independence.
Feedback remains the unchanged V3.2 stage-one score with discovery fitness
unavailable. Primary discovery remains closed until final preregistration.

## Observations so far

| Observation | Status | Evidence |
|---|---|---|
| Separate seed | Valid stage one | Original candidate ID; accuracy 0.493, six features, score 0.4905900505 |
| Proposal 1 | Invalid | `local_shape_signature` lacked a closed object parameter schema; score zero |
| Proposal 2 | Valid stage one | Accuracy 0.8925 and 49 features; its full original score is retained in the run artifacts |
| Proposal 3 | Valid stage one | Accuracy 0.818 and 35 features |
| Proposal 4 | Valid stage one | Accuracy 0.8815 and 69 features |
| Proposal 5 | Valid stage one | Accuracy 0.886 and 68 features; generation 2 |
| Proposal 6 | Valid stage one | Accuracy 0.8925 and 57 features |
| Proposal 7 | Valid stage one | Accuracy 0.892 and 88 features; generation 2 |

The seed accuracy and feature dimension match the original seed; its small
score difference reflects the runtime component. The partial data-free audit
verified six structurally valid proposals with six distinct expanded-program
hashes and one invalid proposal. It reconciled all seven original scores with
the telemetry and verified that checking changed no candidate or lineage
input bytes. Its source digests and observations are saved in
`results/v4/phase10_followup/live_structural_audit_20261014T120027.json`.
Three proposals remain; final gates and language utility are unestablished.

### Worker-side interpreter issue

The first native worker's shell reported `LLMAO_PYTHON` unset. It then invoked
the checker with bare `python3`, which failed to import `networkx`. Consequently
that call returned no structural validation feedback. Host-side validation had
used the explicit project interpreter successfully, so it did not establish
that the environment-variable command would work through the worker tool
transport. The later authoritative evaluator correctly rejected proposal 1's
parameter schema.

Preserve that failed proposal and its budget. The frozen run continues; no
proposal, prompt, checker, or score is repaired in place. Before another run
uses this interface, remove its dependence on an inherited shell variable and
demonstrate a successful approved checker invocation through the native worker
tool path. Audit all ten transcripts for successful and failed checker calls.

Future bundle tooling now emits a hashed launcher bound to the verified project
interpreter. Four focused tests pass without the shell variable, with a
system-only PATH and paths containing spaces. Successful invocation through
native scientific worker tools remains pending. The running bundle is unchanged.

## Durable evidence and remaining audit

`results/v4/phase10_followup/` holds the configuration validation, fresh account
snapshot, runtime source snapshot, execution record, and live launch audit.
These generated files remain Git-ignored. The launch audit verified three
materialized worker checker bundles with no detected source or inventory
change. The final boundary and official-test-access transcript audit is pending.

All 77 V4 unit tests passed after adding the bundle exporter and supervisor.
The pre-launch audit verified all 42 contract-pinned EvE files and all 86
protected prior artifact digests. Source control is separate from run
completion: the remaining proposals, raw-artifact archive, macro/lineage review,
gate results, and final report are still pending.
