# LLMAO V4 — Evolving the Language of Inductive Bias

**Status: frozen exploratory research study.** This report closes V4 using the
preserved evidence available on 2026-10-22. It adds no search, evaluation,
model request, or protocol amendment. V4 did not complete its reduced primary
campaign, so this report makes no primary-language efficacy claim.

The immutable evidence inventory is in
[`V4_EVIDENCE_MANIFEST.json`](V4_EVIDENCE_MANIFEST.json). It records source
revisions, dataset fingerprints, artifact hashes, missing evidence, and the
scope of the release bundle.

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

### Primary campaign status

The finalized V4 primary protocol was reduced by the V11 amendment to five
discovery runs and twenty fresh-search runs. The preserved protocol revisions
v10–v14 are hash-valid, and v14 is the latest. The evidence does not complete
that design:

- V14 discovery seed 1101 exhausted 540 attempts and has an
  `incomplete_attempt_cap` manifest.
- V14 discovery seed 1202 has 221 attempts in a state snapshot last updated
  2026-10-18. Its snapshot says `running`, but no final `run_manifest.json`
  exists; the snapshot is not evidence of a live process or completion.
- No other V14 discovery seed has a preserved run root, and no V14 fresh-search
  condition is present.
- No frozen `G*` selection or completed five-seed discovery table exists.

The v14 protocol, its digest, and the two available run-status records are
listed in the evidence manifest. Earlier phase-10 and phase-12 failures remain
historical exploratory or incomplete records; none has been promoted to a
completed primary result.

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
- V4's reduced 25-run primary campaign meets its statistical or numeric
  support criteria. No E5 or other search is part of this release.

## Data, protocol, and reproducibility boundaries

E1, E3, and E4 use the official MNIST training partition only. The pinned
training archives are identified by SHA-256 in the manifest. The shared
training-derived split has fingerprint
`41bc42fedd084e7c6f67d995be6cb84d77eb72acc44fca3b31fe3691301b129f`, with
seed 42, 58,000 training rows, and 2,000 validation rows. E1's own saved
manifest records the source and split component hashes but not the later
aggregate fingerprint or full evaluator configuration. E2 records that no
MNIST data was loaded. The official test partition was not accessed in E1–E4.

This closure does not change `V4_PROTOCOL.md`, any finalized primary protocol,
V4_PRIMARY_DESIGN.md, or V4_PRIMARY_DESIGN_V11.md. The protocols and their
historical artifacts remain unchanged. Reproduction guidance now points to
the frozen evidence bundle and hash checks rather than suggesting a new V4
run.

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

The focused deterministic V4/E1–E4 test set passed **208 tests**. It used
mocked proposal clients and synthetic fixtures. This closure did not invoke a
model, launch a search, score a scientific candidate, or call the official-test
loader. The release artifacts and their exact SHA-256 hashes are in
[`V4_EVIDENCE_MANIFEST.json`](V4_EVIDENCE_MANIFEST.json); the checksum files
support independent verification from the tagged source tree.
