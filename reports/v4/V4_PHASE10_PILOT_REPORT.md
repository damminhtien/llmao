# V4 Phase 10 Language Pilot

## Outcome

The exploratory pilot completed on 2026-10-14. It produced the preregistered
ten proposals plus a separately evaluated seed. Six proposals received valid
V3.2 stage-one scores; four failed candidate-context validation. The minimum
gate was eight valid proposals, so the pilot **failed its acceptance gate**.

All scores below are stage-one-only. `discovery_fitness` remains null. The run
does not establish that language evolution improves search or that any macro
defines a generally useful inductive-bias vocabulary.

## Run record

- Run ID: `run-20261014_174959_098256-llmao-v4-language-pilot-20261014T0935Z-b9330fcb80d3`
- Run root: `/Users/macbook/Library/Caches/llmao-v4-eve-runs/20261014T0935Z-llmao-v4-language-pilot`
- Completed iterations: 10/10; solver evaluations: 11 including the seed
- Account plan: ChatGPT Plus; pre-worker snapshot at 09:50:21 UTC showed 41%
  five-hour usage, 12% weekly usage, and no paid credits
- Worker: `gpt-6-luna`, max reasoning, `codex_tmux`, workspace-write sandbox,
  network disabled, web search disabled, multi-agent disabled
- LLMAO commit: `0ba422b8904b9d2d0dd33170f3e47b4d7f8ec106`
- EvE commit: `eb30d4f467780d9fbfa5c0389d9ffa40dbff0fb4`
- Protocol SHA-256: `e21bd6e89c8ea90629e8a07417bdb3b007d1474ce075920d358a62e69ac2234b`
- Evaluator SHA-256: `b18c3f3e3adc4c1ac3c0c41f22aff1148f2e7edce465f41b2c37f83183813755`

EvE telemetry recorded 3,026,011 input tokens, 2,553,600 cache-read tokens,
97,054 output tokens, and 1,100.94 seconds of cumulative wall time. These are
runner telemetry fields, not account billing totals. The checkpoint and solver
and iteration telemetry CSVs record ten proposal evaluations. No Phase 3 Elo
update markers appeared because the optimizer guidance did not change and no
optimizer candidate was produced.

## Seed

The separate seed was `candidate-508d0c5800a1e2f12873`, with stage-one score
0.4905797185, accuracy 0.493, and six features. It is not included in the ten
proposal attempts.

## Proposal ledger

| Iteration | Result | Candidate ID | Lineage | Score / accuracy / features or rejection |
| --- | --- | --- | --- | --- |
| 1 | Invalid | — | Parent: seed; generation 1 | `regional_orientation_profile` had malformed nested `input_types`; rejected as an unknown signature type. |
| 2 | Stage one | `candidate-622dad5617d8cace633e` | Parent: seed; generation 1 | 0.8535856193 / 0.8575 / 24; introduced `regional_ink_angle_profile`. |
| 3 | Stage one | `candidate-d44dd5a6119e94b1e9fc` | Parent: iteration 2; generation 2 | 0.8521603928 / 0.8565 / 36; introduced `spatial_stroke_structure_profile`. |
| 4 | Invalid | — | Parent: iteration 2; generation 2 | `regional_ink_turn_profile` expanded to depth 7; limit is 6. |
| 5 | Invalid | — | Parent: iteration 2; generation 2 | Expanded program depth was 7; limit is 6. |
| 6 | Invalid | — | Parent: iteration 2; generation 2 | `multiscale_ink_angle_profile` language was not canonically represented. |
| 7 | Stage one | `candidate-5dffda15a942084dc4c4` | Parent: iteration 2; generation 2 | 0.8687684443 / 0.873 / 33; used inherited `regional_ink_angle_profile`. |
| 8 | Stage one | `candidate-83cfc1c1dcc102e1c8dd` | Parent: seed; generation 1 | 0.8687722139 / 0.873 / 33; reintroduced the iteration 2 macro definition. |
| 9 | Stage one | `candidate-83cfc1c1dcc102e1c8dd` | Parent: seed; generation 1 | 0.8687732694 / 0.873 / 33; exact candidate-ID repeat of iteration 8. |
| 10 | Stage one | `candidate-5dffda15a942084dc4c4` | Parent: iteration 2; generation 2 | 0.8687721187 / 0.873 / 33; exact candidate-ID repeat of iteration 7. |

## Gate review

- **Valid stage-one minimum:** failed, 6/10 versus 8/10 required.
- **Invalid rate:** 4/10 (40%); all four attempts and their reasons are retained.
- **Macro use:** every proposed macro was referenced by the proposing program;
  the iteration 2 macro was reused by valid descendant iteration 7.
- **Macro and feature caps:** accepted languages had at most two macros and 36
  features, below the limits of eight macros and 128 features. Iterations 4 and
  5 attempted depth 7 and were rejected before admission.
- **Dead primitives:** no introduced macro was globally unused. The accepted
  iteration 3 language retained an inherited macro that its own program did not
  call; a descendant used that macro.
- **Duplicates:** iterations 8 and 9 reintroduced the same macro definition
  from separate G0 branches. Iterations 9 and 10 repeated the candidate IDs
  from iterations 8 and 7, leaving four unique valid candidate IDs.
- **Renaming:** the reviewed macros composed multiple G0 operations; none was
  an alias for a single existing operation.
- **Search effect:** not established. This single-seed, ten-proposal pilot has
  no controlled comparison for a causal language-evolution effect.
- **Boundaries:** no data, label, official-test, or workspace-boundary
  violation was found. Candidate-context validation failures are recorded as
  invalid attempts, not boundary violations.

## Evidence and next step

This report is version-controlled. In this checkout, the ignored
`results/v4/phase10_pilot/` directory retains the candidate language and program
JSON, all per-attempt lineage states, evaluation summaries, the seed artifacts,
checkpoint, and telemetry CSVs. Its `manifest.json` records SHA-256 hashes for
those files. The raw EvE run remains at the run root above.

Do not run another language pilot or start Phase 12 yet. Record a separate
response plan for depth-invalid proposals, duplicate candidates and macros, the
40% invalid rate, and the stage-one-only evidence limit; then complete and hash
the pending Phase 0 preregistration.
