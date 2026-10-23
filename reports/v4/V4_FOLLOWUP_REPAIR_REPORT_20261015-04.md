# V4 follow-up repair pilot 20261015-04 — passed exploratory gates

## Outcome

The separately frozen ten-proposal pilot passed every contracted follow-up
feasibility gate. It completed all ten slots without replacements and exited
normally. This closes M1, but the run remains **exploratory feasibility
evidence only**. It does not establish a discovery result or primary finding.

- Contract: `V4_FOLLOWUP_REPAIR_CONTRACT_20261015-04.json`
- Contract SHA-256: `17c0697fb7ab535fb65381cf804bcb68b8bc6e7d57232569fa055bfdd6dae2c6`
- Run ID: `run-20261015_163055_010666-repair_followup_20261015-04-07a4cdaf3320`
- Run interval: 2026-10-15 08:30:54–08:57:17 UTC
- Archive: `results/v4/phase10_followup/archive/repair_followup_20261015-04/`

## Contracted gate audit

| Gate | Evidence | Result |
|---|---|---|
| Ten submitted proposals, no replacements | Checkpoint reached 10/10; contract replacement budget is zero | Pass |
| Valid stage-one proposals | 10/10 have `status=stage_one_only` and no candidate validation error; 8 required | Pass |
| Distinct expanded programs | 10 distinct `expanded_program_sha256` values; 8 required | Pass |
| Selected-prefill lineage | 10/10 child parent hashes match the selected parent's evaluator-owned language hash | Pass |
| Introducer macro use | All 3 introduced macros appear in their introducing proposal's program AST | Pass |
| Descendant macro use | `path_length_histogram`, introduced by proposal 4, is called by descendants 5, 8, and 10 | Pass |
| Expansion and feature limits | Maximum depth 6, 31 expanded nodes, and 44 features; limits are 6, 127, and 128 | Pass |
| Native worker transcripts | Exactly one parseable JSONL transcript for each of 10 proposals | Pass |
| Protected boundary and fresh G0 | Runtime monitor observed 10 structural bundles; fresh-G0 and post-run boundary scans returned no violation | Pass |
| Tmux failures | No `respawn-pane` failure; execution trace records zero failures | Pass |
| Rollout runtime | 10 telemetry rows; longest rollout was 345.246619 seconds against a 3600-second cap | Pass |
| Official-test boundary | Contract pins zero allowed official-test accesses; all outputs remain stage-one only with `discovery_ready=false` | Pass |

Every archived completion patch lists only `solver/candidate/language.json`
and `solver/candidate/program.json`. The contract and runtime used the strict
workspace boundary. The collector's 257 referenced file records passed hash and
size verification.

## Observed environment diagnostics

Some worker `git status` or `git diff` commands emitted the macOS
`xcode-select` error because command-line developer tools were unavailable.
The worker still emitted completion patches limited to the two permitted
candidate files. Shell here-document attempts to create temporary files were
denied by the sandbox. Neither diagnostic stopped a proposal, and the runtime
boundary scan found no protected change.

EvE telemetry reports `agent_turns=0` for all solver rows, so that field does
not independently measure native model turns. The native driver retained its
configured 80-turn cap; this telemetry limitation is preserved in the machine
readable audit.

## Interpretation and preserved evidence

The pinned evaluator was still the draft V3.2 stage-one evaluator. Each score
has `protocol_status=draft_before_discovery` and `discovery_ready=false`. No
discovery fitness or official-test result was produced. Do not compare these
stage-one scores as primary outcomes.

The finalized archive manifest SHA-256 is
`d135dbf93ba84ed255c5b9f5c235253e9d50c3cbd708eb324430e9700b741e6b` and is
pinned by `manifest.sha256`. The gate audit JSON is
`gate_audit.json`, SHA-256
`d9ebea417087d2d4d8a321fc2f07af0b99fd818bd56ad50225b59df201e75612`. The
collector's original pending-audit manifest is preserved as
`collection_manifest.json`; its SHA-256 is
`867a411a4b7fff121feda43c70e7afdb5ec44491a35a6e53f016ced1b883e840`.

The earlier failed pilots remain failed exploratory evidence. Contract `-03`
remains a separate pre-worker Hydra startup failure and contributed no proposal
to this run. The official test split remains unavailable until the frozen
language evaluation gate.
