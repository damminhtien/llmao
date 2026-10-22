# LLMAO V4 — Evolving the Language of Inductive Bias

**Status: frozen exploratory research study.** This report closes V4 using the
preserved evidence available on 2026-10-22. It adds no search, evaluation,
model request, or protocol amendment. V4 did not complete its reduced primary
campaign, so this report makes no primary-language efficacy claim.

The evidence inventory is in
[`V4_EVIDENCE_MANIFEST.json`](V4_EVIDENCE_MANIFEST.json). It records source
revisions, dataset fingerprints, artifact hashes, missing evidence, and the
scope of the release bundle.

**Naming:** V4 is the research study. Its primary-protocol IDs include
`v4-primary-11` and `v4-primary-14`; “protocol revision 14” is a revision within
V4, not a separate V14 study or branch. This post-tag documentation follow-up
clarifies that naming and summarizes preserved revision-14 trajectory records.
It changes no protocol, source code, data, or historical run artifact; the local
release tag remains unchanged.

## Study scope

E1–E4 were bounded, exploratory MNIST studies around the three frozen
`G_pilot` macros. They answer different questions and are not a single
confirmatory experiment:

- **E1** compared one seed-101 G0 search with one G_pilot search using the
  then-current V3.2 iterative optimizer.
- **E2** made six targeted, no-score requests to test whether a model could
  express each named macro when explicitly asked.
- **E3** evaluated the three unique expanded programs already obtained by E2.
- **E4** compared one seed-202 search with G0 recipe guidance against one with
  typed G_pilot macros available.

The frozen `G_pilot` language is not the officially selected primary language
`G*`. No `G*` selection or five-seed primary analysis exists.

## Confirmed observations

### E1 — One bounded, pre-correction search pair

E1 evaluated the same 20 starting programs in each arm and five adaptive
candidates per arm. Both arms retained the shared initial best fitness
`0.490582252501`; neither recorded an improved best. The G0 arm used 20 of 20
proposal attempts. The G_pilot arm used 19 of 20 and ended with
`optimizer_returned_no_attempts`. Neither arm recorded a G_pilot macro in a
scored candidate. The run summary and detailed metrics are preserved under
[`results/v4/e1`](../../results/v4/e1/).

This is an observation about one bounded run pair, not an estimate of macro
utility. The E1 artifact did not pin the executing source revision, a complete
dataset fingerprint, or the complete evaluator configuration. Its file
timestamp predates commit `41c8bfb`, which later changed E1 mechanism-family
eligibility and focus scheduling. That timing supports a pre-correction source
inference, but does not identify the exact runtime tree.

### E2 — Targeted generation capability

E2 issued all six planned requests, two per macro, and loaded no MNIST data.
Every response invoked its requested macro and passed structural validation.
Each pair reduced to one unique expanded AST because the second response was a
duplicate. E2 requested no scores. These records establish targeted generation
in this prompt setting only; see
[`results/v4/e2/macro_adoption_probe_2026-10-19`](../../results/v4/e2/macro_adoption_probe_2026-10-19/).

### E3 — Three selected expanded programs

E3 evaluated those three unique E2 programs as canonical G0 ASTs on the fixed
training-derived split. It did not evaluate macro syntax as a separate
function. The recorded fitness values and accuracies were:

| Expanded program | Fitness | Validation accuracy | Feature dimension |
|---|---:|---:|---:|
| `stroke_degree_profile` | 0.491353 | 0.4950 | 19 |
| `multiscale_spatial_profile` | 0.822582 | 0.8280 | 116 |
| `multiscale_spatial_degree_profile` | 0.778965 | 0.7825 | 18 |

All three exceeded the shared initial fitness except `stroke_degree_profile`,
which was only 0.000770 higher. E3 used the existing 500-example stage-one
training sample and the 2,000-row validation split. Fitness includes measured
runtime, which varied with local execution and cache state. The three
descriptive measurements do not estimate search efficiency. The full report
and machine-readable result are
[`results/v4/e3/e2_macro_program_evaluation_2026-10-20`](../../results/v4/e3/e2_macro_program_evaluation_2026-10-20/).

### E4 — One-seed recipe versus macro packaging comparison

E4 reused the 20 E1 initial scores and compared two seed-202 searches with the
same fixed guidance policy, data split, evaluator, and attempt/resource caps.
The conditions differed in operation names, AST schema, prompt length, and
whether typed macro operations were available.

| Condition | Attempts | Valid proposals | Invalid | Duplicates | Adaptive scores | Best adaptive fitness |
|---|---:|---:|---:|---:|---:|---:|
| G0 recipes | 20 | 20 | 0 | 1 | 19 | 0.630531 at attempt 7 |
| G_pilot macros | 20 | 15 | 5 | 1 | 14 | 0.395342 at attempt 20 |

The macro condition's best adaptive fitness remained below its shared initial
best of `0.490582`. Neither condition invoked a macro or scored a complete
frozen recipe subtree under E4's exact-subtree criterion. This one-seed result
describes the observed runs; it does not isolate a causal effect of macro
syntax or establish a search-efficiency difference. E4's traces also contain
proposal IDs stamped with seed 101, while the optimizer and model request
seeds were 202 onward. The saved report documents that the ID field was
metadata only and did not enter prompts or model sampling. See
[`results/v4/e4/seed_202`](../../results/v4/e4/seed_202/).

### V4 primary-protocol status and revision-14 trajectory spotlight

Primary-protocol revision 11 (`v4-primary-11`) reduced the V4 primary design to
five discovery runs and twenty fresh-search runs. The hash-valid protocol IDs
`v4-primary-10` through `v4-primary-14` are successive revisions within this
single V4 study; `v4-primary-14` is the latest. The preserved revision-14
trajectory records contain partial exploratory signals:

| Revision-14 discovery trajectory | Attempt records | Scored proposals | Candidate-context failures | Interruptions | Best recorded discovery fitness |
|---|---:|---:|---:|---:|---:|
| Seed 1101 | 540 | 103 | 436 | 1 | 0.907394 (attempt 198) |
| Seed 1202 | 221 | 131 | 89 | 1 | 0.910471 (attempt 151) |

The attempt totals include one interrupted proposal in each trajectory. Every
other unscored proposal in these records ended in candidate-context validation
failure with `candidate language parent hash does not match`. This is an
observed lineage-validation failure at the evaluator boundary; the preserved
records do not isolate which component produced the mismatched lineage.

Among scored proposals, seed 1101 recorded 19 macro-introduction events:
`spatial_topology_features` (14), `spatial_degree_profile` (2), and one each
for `multiscale_spatial_occupancy`, `spatial_skeleton_profile`, and
`skeleton_length_quartiles`. Seed 1202 recorded 15 events: `skeleton_graph`
(13) and `skeleton_paths` (2). The best-scored record in each trajectory lists
`spatial_topology_features` or `skeleton_graph` in its `language_macros`
inventory and has no macro introduction on that record. The inventory does not
by itself establish that the scored AST invoked a macro.

The run records are preserved at [seed 1101](../../results/v4/phase12/runs/discovery-1101-736f9da03cc2/trajectory.jsonl) and
[seed 1202](../../results/v4/phase12/runs/discovery-1202-736f9da03cc2/trajectory.jsonl).
Seed 1101 reached the 540-attempt cap with status `incomplete_attempt_cap`;
its 793 MB final manifest is preserved locally but excluded from the release
tag. Seed 1202 has 221 attempts in a state snapshot last updated
`2026-10-18T14:04:23.936131+00:00`. The snapshot says `running`, but no final
`run_manifest.json` or live process was verified.

The candidate-AUC horizon requires 180 scored adaptive unique evaluations beyond
the 20 shared starting programs to reach 200 total evaluations. Neither
trajectory reached that horizon: it has at most 103 or 131 scored adaptive
proposals, respectively. No complete candidate AUC, frozen `G*` selection,
completed five-seed discovery table, other revision-14 discovery run, or
revision-14 fresh-search condition exists. Earlier phase-10 and phase-12
failures remain historical exploratory or incomplete records; none has been
promoted to a completed primary result.

## Unsupported hypotheses

- E1's lack of macro use does not show that G_pilot is useless. It is one run
  pair, stopped early in the macro arm, and predates a source correction to
  mechanism eligibility and focus scheduling.
- E2's targeted invocations do not show that a model spontaneously prefers
  macros or that macros improve a search. The prompts explicitly requested
  each macro and no fitness was measured.
- E3's higher scores for two selected programs do not show that macro
  abstraction caused the scores. The evaluated objects were complete expanded
  programs selected by E2, not matched macro-versus-recipe searches.
- E4's G0 result being higher than the macro arm does not show that recipes
  are generally better. There was one seed, five macro-arm schema failures,
  and multiple prompt/schema differences.
- The revision-14 trajectories' recorded fitness values and distinct macro
  introduction patterns do not show that the macros caused those scores, that
  the language improved search, or that the pattern would replicate. Both runs
  are incomplete, and neither completed the candidate-AUC horizon.
- None of E1–E4 supports causal abstraction utility or improved search
  efficiency.

## Untested claims

- A frozen, discovered `G*` improves the preregistered candidate AUC over G0
  across five matched seeds and both optimizers.
- A V4 language or any of its macros generalizes beyond this fixed
  MNIST-training-derived split, transfers to another dataset, or improves
  official-test performance.
- Macro naming or descriptions causally affect search behavior; the semantic
  ablation was omitted.
- The 25-run primary campaign specified by `v4-primary-11` meets its
  statistical or numeric support criteria. No E5 or other search is part of this
  release.

## Data, protocol, and reproducibility boundaries

E1, E3, and E4 use the official MNIST training partition only. The pinned
training archives are identified by SHA-256 in the manifest. The shared
training-derived split has fingerprint
`41bc42fedd084e7c6f67d995be6cb84d77eb72acc44fca3b31fe3691301b129f`, with
seed 42, 58,000 training rows, and 2,000 validation rows. E1's own saved
manifest records the source and split component hashes but not the later
aggregate fingerprint or full evaluator configuration. E2 records that no
MNIST data was loaded. The official test partition was not accessed in E1–E4.

Neither this closure nor the post-tag documentation clarification changes
`V4_PROTOCOL.md`, any finalized primary protocol, `V4_PRIMARY_DESIGN.md`, or
`V4_PRIMARY_DESIGN_V11.md`. The protocols and historical run artifacts remain
unchanged. Reproduction guidance points to the checksummed evidence bundle and
does not authorize a new V4 run.

## Blocking correctness defect

The shared iterative optimizer has a final-slot budget bug at
[`llm_common.py:204`](../../src/bias_optimizer/optimizer_bench/optimizers/llm_common.py#L204):
it sizes a batch using `remaining_attempts // 2`. When exactly one attempt
remains, the batch size becomes zero and the optimizer returns an empty batch.
The E1 runner then records `optimizer_returned_no_attempts` and writes a
complete trace. This matches the preserved E1 G_pilot arm: 19 of 20 attempts,
with no model or token cap reached. Existing tests cover duplicate/invalid
attempt accounting and hard caps, but not the one-attempt remainder.

This defect blocks any statement that the E1 G_pilot arm exhausted its full
attempt cap. It does not support a primary or utility claim, and it does not
prevent an honest exploratory closure. No source fix, result repair, or rerun
was made.

## Release verification

The V4 closure's focused deterministic test set passed **208 tests** using
mocked proposal clients and synthetic fixtures. This documentation follow-up
reran no tests, model requests, searches, scientific scoring, or official-test
loader. The current branch's artifact hashes are in
[`V4_EVIDENCE_MANIFEST.json`](V4_EVIDENCE_MANIFEST.json), with post-tag document
revisions marked outside the immutable release tag. The original tagged
manifest and checksums remain available at `v4-exploratory-final`.
