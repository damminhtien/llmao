# LLMAO V4 — Evolving the Language of Inductive Bias

**Status: frozen exploratory research study.** Scientific evidence is frozen
at the 2026-10-22 closure. This editorial synthesis, dated 2026-10-23, brings
the two preserved discovery trajectories to the foreground and integrates the
E1–E4 diagnostics. The intended primary comparison remains incomplete.

## The V4 research pitch

Earlier LLMAO studies searched for representation programs inside a language
chosen by humans. V4 asks whether discovery can also propose the vocabulary:
**can an LLM invent abstractions that make useful inductive biases easier to
discover again?** The system can propose typed macro compositions over approved
primitives alongside candidate programs and search guidance. The intended
scientific test freezes a discovered language, restarts search, and compares
that fresh search with the original language under the fixed protocol.

The two partial discovery trajectories are the spotlight of V4. One introduced
spatial topology, degree, and occupancy abstractions; the other introduced
`skeleton_graph` and `skeleton_paths`. Their best recorded discovery fitness
values were **0.907394** and **0.910471**. These are preserved candidate-level
observations on a training-derived MNIST split, not test accuracies, completed
primary results, or estimates of a macro's contribution. Macro inventories
alone do not establish invocation by the scored program.

E1–E4 give that spotlight a useful diagnostic context through a separate frozen
pilot language: all six targeted requests expressed the requested macro; two
selected expanded programs recorded local fitness 0.822582 and 0.778965, above
the shared pilot starting best of 0.490582; the bounded search pairs recorded no
spontaneous macro adoption. Thus, expression, expanded-program quality, and
search adoption are different empirical questions. The pilot macros are not a
selected language from the spotlight trajectories, and these diagnostics do
not validate those trajectories' particular abstractions.

V4 contributes an inspectable record of proposed abstraction families and the
gap between candidate quality and demonstrated language utility. The two
trajectories contain promising descriptive signals. A benefit for fresh search
remains untested because no `G*` was selected and the primary campaign did not
complete. This is the study's exploratory conclusion.

## How to read the evidence

The [evidence manifest](evidence/V4_EVIDENCE_MANIFEST.json) records source revisions,
dataset fingerprints, artifact hashes, exclusions, and missing evidence. The
[integration handoff](../../docs/V4_MERGE_READINESS.md) records the local
verification and the relation to the immutable release tag.

V4 is one study. IDs such as `v4-primary-11` and `v4-primary-14` identify
successive revisions of its primary protocol. The 25-run scope was specified
by revision 11; revision 14 is the latest finalized artifact. Revision numbers
do not identify separate research studies or branches.

The reading map separates two bodies of observations from the intended primary
test:

| Evidence | What is preserved | What it can establish |
|---|---|---|
| Two discovery trajectories under `v4-primary-14` | Candidate scores, abstraction inventories, macro-introduction records, failures, and state snapshots | Descriptive candidate-level and language-inventory observations in incomplete searches |
| E1–E4 using the three frozen `G_pilot` macros | Bounded search traces, targeted generation, selected expanded-program scores, and packaging comparison | Local observations about expression, representation quality, and adoption |
| Intended frozen-`G*` fresh-search comparison | Protocol and design only | No empirical utility estimate; no selected `G*` or fresh-search campaign exists |

## Confirmed observations

### Spotlight — two evolving abstraction inventories

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

The release preserves these trajectory records and state snapshots, rather
than the full native worker workspaces and per-candidate replay bundles. The
spotlight can therefore be audited as a record of scores and inventories;
complete independent replay and macro-invocation attribution exceed the
bundled evidence.

The candidate-AUC horizon requires 180 scored adaptive unique evaluations beyond
the 20 shared starting programs to reach 200 total evaluations. Neither
trajectory reached that horizon: it has at most 103 or 131 scored adaptive
proposals, respectively. No complete candidate AUC, frozen `G*` selection,
completed five-seed discovery table, other revision-14 discovery run, or
revision-14 fresh-search condition exists. Earlier phase-10 and phase-12
failures remain historical exploratory or incomplete records; none has been
promoted to a completed primary result.

### E1–E4 — complementary diagnostics with a separate pilot language

The three-macro `G_pilot` is a frozen exploratory language. It is not an
independently validated output of either spotlight trajectory and is not the
primary language `G*`. E1–E4 answer different questions and must not be pooled
into a confirmatory language-utility experiment.

#### E1 — One bounded, pre-correction search pair

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

#### E2 — Targeted generation capability

E2 issued all six planned requests, two per macro, and loaded no MNIST data.
Every response invoked its requested macro and passed structural validation.
Each pair reduced to one unique expanded AST because the second response was a
duplicate. E2 requested no scores. These records establish targeted generation
in this prompt setting only; see
[`results/v4/e2/macro_adoption_probe_2026-10-19`](../../results/v4/e2/macro_adoption_probe_2026-10-19/).

#### E3 — Three selected expanded programs

E3 evaluated those three unique E2 programs as canonical G0 ASTs on the fixed
training-derived split. It did not evaluate macro syntax as a separate
function. The recorded fitness values and accuracies were:

| Expanded program | Fitness | Validation accuracy | Feature dimension |
|---|---:|---:|---:|
| `stroke_degree_profile` | 0.491353 | 0.4950 | 19 |
| `multiscale_spatial_profile` | 0.822582 | 0.8280 | 116 |
| `multiscale_spatial_degree_profile` | 0.778965 | 0.7825 | 18 |

All three exceeded the shared initial fitness of `0.490582252501`.
`stroke_degree_profile` was only 0.000770 higher; the two spatial programs
showed the larger differences in this selected set. E3 used the existing
500-example stage-one training sample and the 2,000-row validation split.
Fitness includes measured
runtime, which varied with local execution and cache state. The three
descriptive measurements do not estimate search efficiency. The full report
and machine-readable result are
[`results/v4/e3/e2_macro_program_evaluation_2026-10-20`](../../results/v4/e3/e2_macro_program_evaluation_2026-10-20/).

#### E4 — One-seed recipe versus macro packaging comparison

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

## What these observations mean for V4

The spotlight preserves two different abstraction inventories rather than a
single predetermined macro family. This supports the descriptive observation
that language proposals differed between these two trajectories. The macro
names and inventories do not establish mechanistic correctness, novelty beyond
the permitted primitives, or reproducibility across independent discovery runs.

The pilot diagnostics distinguish three steps. E2 shows targeted expression
in six requests. E3 shows that selected expanded programs can score well in the
local evaluator. E1 and E4 record no spontaneous macro adoption in their
bounded settings. A plausible interpretation is that available abstractions
and good examples do not ensure that search will choose those abstractions.
That is a hypothesis about adoption, not a demonstrated cause of either
spotlight trajectory's outcomes.

The intended unit of success was a language that helps a new search. The
preserved evidence stops before that test. V4 therefore closes with
candidate-level signals, diagnostics of expression and adoption, and explicit
limits on language-level inference.

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

Neither the closure nor the subsequent editorial revisions change
`docs/v4/V4_PROTOCOL.md`, any finalized primary protocol, `docs/v4/V4_PRIMARY_DESIGN.md`, or
`docs/v4/V4_PRIMARY_DESIGN_V11.md`. The protocols and historical run artifacts remain
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
mocked proposal clients and synthetic fixtures. The same focused set was run
again for integration preparation on 2026-10-23; its result is recorded in the
[integration handoff](../../docs/V4_MERGE_READINESS.md). The editorial work
invoked no model, research search, scientific scoring, or official-test loader.
The current branch's artifact hashes are in
[`V4_EVIDENCE_MANIFEST.json`](evidence/V4_EVIDENCE_MANIFEST.json), with post-tag document
revisions marked outside the immutable release tag. The original tagged
manifest and checksums remain available at `v4-exploratory-final`.

The current checkout matches 85 of the 86 historical baseline-manifest hashes.
The sole exception is the reports navigation index, `reports/README.md`,
updated to include V4. Its original bytes match at the recorded baseline
commit. All other protected entries match; the manifest and handoff record this
editorial exception rather than asserting an unqualified 86/86 current check.

## Repository layout follow-up

A post-publication cleanup relocated 25 root documents and frozen inputs into
`docs/v4/`, `reports/v4/`, and `configs/v4/` without changing their bytes.
Current script/test path references were updated; scientific criteria and run
records were preserved. See the [location guide](../../docs/v4/README.md) and
its hash index. Historical embedded paths and source pins apply to the original
`v4-exploratory-final` checkout. This cleanup adds no scientific evidence.
