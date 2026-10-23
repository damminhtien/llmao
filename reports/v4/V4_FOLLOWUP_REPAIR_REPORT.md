# V4 Phase 10 repair attempt report — 2026-10-15

## Outcome

The separately contracted exploratory repair run consumed exactly ten
proposal slots and exited normally, but all ten proposals failed candidate
context validation. The scientific gate failed. No discovery or primary result
was produced, and M1 remains open.

- Repair contract: `V4_FOLLOWUP_REPAIR_CONTRACT.json`, SHA-256
  `536d83a06baabe4acac3f91b58e6fb6512fb453d567286c1843e900ea05b3040`.
- Frozen LLMAO source commit: `1f84774b4c4f6d3c59d2104151ab71362ab87337`.
- Run ID: `run-20261015_142735_928795-llmao-v4-language-followup-repair-20261015T0626Z-53e590e6b58f`.
- Run duration: 9.836 seconds; checkpoint `10/10`; zero replacement proposals;
  supervisor stop reason was empty.
- Archive: `results/v4/phase10_followup/archive/repair_followup_20261015-01/`.
  Final manifest SHA-256:
  `b0ba212c44917c4f880be859a911175dae82d7603fdc277056338f19097200d7`.

## Gate audit

| Gate | Evidence | Result |
|---|---|---|
| Ten proposals, no replacements | Checkpoint and ten telemetry rows | Pass |
| At least eight valid stage-one proposals | 0/10; every score status was `failed` with `candidate context validation failed` | Fail |
| Eight distinct valid expanded programs | 0/8; none reached valid expanded-program evaluation | Fail |
| Genuine descendant macro reuse | No proposal passed context validation; all ten candidate files were byte-identical to the G0 seed | Fail |
| Fresh G0 initialization | Seed language and program hashes match the frozen contract | Pass |
| Protected worker boundary | No forbidden-change marker was reported and one pinned structural bundle was observed, but no pilot JSONL transcript was captured | Incomplete; gate not established |
| Native checker integration fixture | `20261015-native-boundary-05`: 21/21 no-model preflight checks and 15/15 native checks passed | Pass for the fixture only |

## Failure evidence

The seed's evaluator-owned `lineage_state.json` records
`language_hash=5ba1e2f9e0b1d45a4e0c6fa9825491f83e169bae43bde63fe03863008315e765`.
Every submitted `language.json` instead kept
`parent_language_hash=34053b62a917cb7f19b572a4458440972350ea800391fdeba2d3f624cc331b2f`,
the seed language's own parent/base hash. The evaluator consequently rejected
each unchanged seed candidate as a child of the current prefill. Future worker
instructions must name the exact value to copy:
`parent_language_hash = selected_prefill/logs/evaluate/lineage_state.json["language_hash"]`.

The native-driver evidence is also incomplete. Attempt one has a completion
record (`status=ok`, `changed_files=[]`) and an empty diff patch, but no JSONL
transcript. Attempts two through ten have no transcript artifacts and each has
an `agent_error.txt` showing `CalledProcessError` from `tmux respawn-pane` with
exit status 1. The exact tmux failure cause is not present in the captured
error. The archive preserves the runner log, all available per-attempt errors,
completion artifacts, evaluator logs, candidates, telemetry, pinned collector
source, contract, and worker overlay. Missing transcripts are recorded as
missing; none were synthesized.

Because the pilot transcripts are absent, the supervisor's clean workspace
result cannot prove what every native worker attempted. The boundary gate
therefore remains unverified even though the supervisor observed no forbidden
marker. The separate data-free fixture proves its own OS denials and checker
behavior, not this pilot's full worker behavior.

## Usage and interpretation

The prelaunch live usage snapshot showed Plus ordinary usage enabled, 5% of the
five-hour window and 1% of the weekly window used, zero paid-credit balance,
and three reset credits available. The post-run snapshot showed 6% and 1%,
zero paid-credit balance, and the same three resets available; no reset was
used. Pending usage is not exposed by the usage limits tool. EvE telemetry for
the pilot reports zero worker turns, tokens, and model cost. The seed returned
only a draft V3.2 stage-one score; no proposal produced an accepted score and
no discovery fitness or official-test result exists.

The first collection manifest is preserved as
`collection_manifest.json`; `manifest.json` is the final gate audit and its
adjacent `manifest.sha256` pins it. The collector version pinned by the repair
contract and the post-run collector that archived missing-transcript evidence
are both included under `run_evidence/`.

The next response is recorded in `V4_FOLLOWUP_REPAIR_RESPONSE_PLAN.md`. No
additional scientific pilot was launched after this failed attempt.
