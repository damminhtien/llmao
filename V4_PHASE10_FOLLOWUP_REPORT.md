# V4 Phase 10 follow-up — final gate audit

Status: **completed, gate failed**. All ten proposals and the separate seed
were evaluated. The supervisor recorded exit code zero at
2026-10-14 12:17:29.587 UTC. Normal process completion is not a scientific pass.
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
| Proposal 8 | Valid stage one | Accuracy 0.8215 and 48 features; introduces `spatial_stroke_profile` |
| Proposal 9 | Invalid | An operation requiring Vector received the wrong type; score zero |
| Proposal 10 | Valid stage one | Accuracy 0.889 and 93 features; inherits but does not use `spatial_stroke_profile` |

The seed accuracy and feature dimension match the original seed; its small
score difference reflects the runtime component. Final structural replay
verifies eight valid and two invalid proposals, eight distinct valid expanded
representations, and 65 core evidence records. No score was recomputed.
The best stage-one score is 0.8878539110180067 at proposal two, with accuracy
0.8925 and 49 features. These observations establish no primary language utility.

## Gate results

| Gate | Result | Evidence |
|---|---|---|
| Ten proposals plus separate seed | Pass | Terminal checkpoint, telemetry, and eleven solver evaluations |
| At least eight valid stage-one proposals | Pass | Eight valid scores; failures one and nine retained |
| At least eight distinct valid expanded ASTs | Pass | Eight hashes, excluding the seed |
| Each validated new macro used by its introducer | Pass | Four validated births, all used |
| At least one macro used by a descendant | **Fail** | Zero descendant uses across all four macro behaviors |
| Accepted candidates within resource caps | Pass | Depth at most 6, nodes at most 71, dimensions at most 93; at most one macro per accepted language |
| Zero noncandidate write deviations | **Fail** | Temporary environment/package links in proposal three; temporary JSON writes in proposal nine |
| Zero official-test access | No access observed | Review of all ten native transcripts and 210 tool calls found no dataset, label, or official-test content read |

The lineage archive has eight language nodes including G0, seven edges, four
macro behaviors, and eleven observations including the seed. All four behaviors
have zero descendant use. The inherited `spatial_stroke_profile` is unused in
proposal ten. Worker/run identities do not establish independent discovery.

### Worker-side interpreter issue

The first native worker's shell reported `LLMAO_PYTHON` unset. It then invoked
the checker with bare `python3`, which failed to import `networkx`. Consequently
that call returned no structural validation feedback. Host-side validation had
used the explicit project interpreter successfully, so it did not establish
that the environment-variable command would work through the worker tool
transport. The later authoritative evaluator correctly rejected proposal 1's
parameter schema.

Preserve that failed proposal and its budget. The frozen run is complete; no
proposal, prompt, checker, or score is repaired in place. Before another run
uses this interface, remove its dependence on an inherited shell variable and
demonstrate a successful approved checker invocation through the native worker
tool path. Audit all ten transcripts for successful and failed checker calls.

The completed audit found 32 direct checker invocation attempts and zero
structured valid/invalid feedback results. Alternative Python executables
failed on dependencies, syntax support, or executable resolution. Workers
spent part of their original budget on these failures; no attempts are replaced.

Future bundle tooling now emits a hashed launcher bound to the verified project
interpreter. Four focused tests pass without the shell variable, with a
system-only PATH and paths containing spaces. Successful invocation through
native scientific worker tools remains pending. The running bundle is unchanged.

## Boundary findings and response

Worker three created `/private/tmp/llmao-structural-check-env` and linked cached
packages into it. Its later `rm -rf` cleanup was rejected by automatic approval
review because that command style was disallowed. The remaining environment
was inventoried and moved into the ignored archive's `runtime_deviation/` area;
external package symlink targets were not changed. Worker five also attempted
offline dependency resolution with `/private/tmp/llmao-uv-cache` as its cache
directory; resolution failed because `networkx` was unavailable. A later
read-only check found that named directory absent, which does not prove that no
transient writes occurred during the run. Worker nine used `/tmp/language.json`
as an editing intermediate. These deviate from the two-file edit rule.

The supervisor checked immutable bundles and forbidden workspace diffs; it
did not detect host temporary-write effects, so it did not stop at the first
deviation. No protected source or dataset-content read was found. Native
transcripts show host interpreter and package-directory searches/listings
outside the workspace. Recorded sandbox settings plus a clean workspace diff
do not prove complete filesystem isolation.

`V4_FOLLOWUP_RESPONSE_PLAN.md` records the required interpreter integration,
explicit prohibition of dependency repairs, stronger temporary-write policy,
type guidance, and inherited-macro reuse guidance before another fresh pilot.

## Durable evidence

`results/v4/phase10_followup/` holds the configuration validation, fresh account
snapshot, runtime source snapshot, execution record, and live launch audit.
These generated files remain Git-ignored. The supervisor observed all ten
worker bundles; final bundle verification found no source or inventory change.
The terminal archive is `results/v4/phase10_followup/archive_verified/`.
Its manifest covers 218 artifact records, all hash-verified, including original
evaluator logs, candidate and lineage files, telemetry, and ten native transcripts.
It excludes Codex authentication files. Structural replay, lineage JSON/Mermaid,
native checker audit, gate audit, and temporary-environment cleanup evidence
are saved alongside the manifest. Earlier partial live audits remain preserved.

All 77 V4 unit tests passed after adding the bundle exporter and supervisor.
The pre-launch audit verified all 42 contract-pinned EvE files and all 86
protected prior artifact digests. Source control is separate from run
completion. Ten focused collector/lineage tests now pass, including live-run
rejection, path containment, replacement/symlink rejection, and original failure
preservation. The follow-up audit is complete and failed; native-worker
interpreter integration and another correctly bounded pilot remain pending.
