# LLMAO V4 — TODO

## Phase 0 — Freeze previous work

- [x] Create branch `v4-evolving-bias-language` from the current integrated
  `main` branch.
- [x] Move the previous architecture and completed V3.1 checklist to
  `ARCHITECTURE_V3_REFERENCE.md` and `TODO_V3_1.md`.
- [x] Replace the root architecture and checklist with the V4 design and plan.
- [x] Record commit hashes for V3, V3.1 and V3.2 artifacts in
  `results/v4/baseline_manifest.json`.
- [x] Verify V3/V3.1/V3.2 reports and results remain unchanged; record 86
  protected artifact hashes in the baseline manifest.
- [x] Create `V4_PROTOCOL.md` as a pre-discovery draft.
- [x] Create canonical `results/v4/protocol.json` as a pre-discovery draft.
- [x] Hash the current draft snapshot in `results/v4/protocol.sha256`.
- [ ] Resolve all pending preregistration decisions in `V4_PROTOCOL.md`.
- [ ] Hash the V4 protocol before producing primary results.
- [x] Define primary RQ and qualitative acceptance criteria before running
  V4 discovery; numerical support criteria remain pending final preregistration.

The protocol is a draft. Phase 0 is complete only after its pending decisions
are resolved and the final protocol is hashed. No V4 discovery or primary
evaluation has run.

---

# Phase 1 — Pin EvE / Codex environment

- [x] Clone/pin `scaling-group/eve` at a specific commit.
- [x] Record EvE commit in `results/v4/environment.json`.
- [x] Verify the installed Codex CLI supports the selected GPT-6 model.
- [x] Verify ChatGPT Plus authentication using `codex` and the account usage
  status.
- [x] Confirm the account plan is ChatGPT Plus (not Pro) and use its ordinary
  Codex allowance; the 2026-10-14 09:32 UTC pre-launch usage snapshot showed
  37% used in the five-hour window, 12% in the weekly window, and no paid
  credits.
- [x] Verify exact GPT-6 Luna model identifier exposed by the CLI:
  `gpt-6-luna`.
- [x] Verify `max` reasoning is available for that model using an isolated
  Codex CLI invocation.
- [x] Pin exact model and reasoning level in V4 protocol.
- [x] Record Codex CLI version.
- [x] Configure `codex_tmux` with `workspace-write`, no agent-shell network,
  disabled web search, and disabled multi-agent mode. Do not use `codex_exec`
  for scientific workers because it bypasses the Codex sandbox.
- [x] Verify the scientific worker config pins `codex_tmux`, disables network,
  web search, and multi-agent mode, and uses the isolated Codex home.
- [x] Verify EvE can launch Codex workers using ChatGPT-account authentication.
- [x] Ensure V4 workers use the isolated Codex configuration so the global
  custom API base URL cannot reroute requests.
- [x] Record token/usage information returned by each rollout in the smoke
  manifest; keep primary-study budgets unresolved until preregistration.

Main-run invariant:

```text
ChatGPT Plus account
GPT-6 Luna (`gpt-6-luna`)
max reasoning
same model
same reasoning level
same agent permissions
same context policy
```

for all LLM-based conditions.

---

# Phase 2 — Reproduce current baseline

Before adding language evolution:

- [x] Re-run a small V3.2 fixed-language experiment on the M2 Max.
- [x] Confirm the 20 frozen seed-program candidate IDs, accuracies, and feature
  dimensions reproduce exactly; maximum fitness delta stayed below the recorded
  `0.001` runtime-timing tolerance.
- [x] Confirm split settings match the existing protocol and save SHA-256
  fingerprints for the search train pool, validation split, and 500-example
  training subset.
- [x] Record evaluator and end-to-end runtimes for all four smoke conditions.
- [x] Confirm the official test partition was not used by the search evaluator.
- [x] Save baseline traces, manifest, protocol copy, and summary under
  `results/v4/baseline_reproduction/`.

Gate:

> Do not proceed until the existing fixed-DSL evaluator is trustworthy on the new machine/environment.

---

# Phase 3 — Define \(G_0\)

- [x] Create `src/bias_optimizer/v4/language/base_language.py`.
- [x] Build \(G_0\) from the frozen V2-level typed DSL.
- [x] Explicitly exclude manually introduced V3 relational primitives.
- [x] Canonically serialize language manifests.
- [x] Add SHA-256 language identity.
- [x] Record every primitive's signature and parameters.
- [x] Write tests verifying deterministic language hashing.
- [x] Add frozen \(G_H\) wrapper for the complete human-designed V3 DSL.

Canonical `G0` and `GH` manifests and their digests are saved under
`results/v4/languages/` and pinned in the draft protocol.

Required languages:

```text
G0 = base / impoverished language
GH = frozen human V3 language
```

---

# Phase 4 — Implement typed macro invention

- [x] Add `MacroPrimitive`.
- [x] Define:

```text
name
description
input_types
output_type
parameters
body_AST
```

- [x] Type-check macro bodies.
- [x] Expand macros into canonical underlying ASTs.
- [x] Detect recursive macro definitions.
- [x] Reject cyclic dependencies.
- [x] Cap macro expansion depth.
- [x] Cap expanded AST node count.
- [x] Cap output feature dimension.
- [x] Canonically hash macro definitions.
- [x] Add macro deduplication by behavior/expanded AST.
- [x] Require every newly introduced macro to be used by the candidate that introduces it.

Tests:

- [x] valid macro;
- [x] type mismatch;
- [x] recursion;
- [x] excessive expansion;
- [x] duplicate macro;
- [x] unused primitive;
- [x] dimension overflow.
- [x] total macro-count and per-candidate macro-addition caps.

The implementation enforces the V3.2 discovery caps: macro dependency and
expanded AST depth 6, 127 expanded AST nodes, and 128 output features. The V4
protocol now sets a maximum of eight macros per language and one new macro per
candidate. The language-complexity penalty definition and coefficient remain
pending final preregistration.

---

# Phase 5 — Candidate schema

Implement:

```text
CandidateV4
├── language
├── program
└── provenance
```

- [x] Add `language_hash`.
- [x] Add `parent_language_hash`.
- [x] Add `program_hash`.
- [x] Add list of invented primitives.
- [x] Add list of primitives used.
- [x] Add parent candidate ID.
- [x] Add EvE agent ID.
- [x] Add guidance hash.
- [x] Add generation number.
- [x] Add model/backend metadata.
- [x] Add evaluation seed.
- [x] Add token usage.
- [x] Add wall-clock measurements.

Candidate hashes and used-primitive lists are recomputed when loading a record;
serialized values must match the validated language and expanded program.

---

# Phase 6 — Build immutable candidate evaluator

Create:

```text
experiments/v4_evaluate_candidate.py
```

Evaluator procedure:

1. load candidate;
2. validate language;
3. compile macros;
4. validate representation AST;
5. expand candidate to canonical base AST;
6. execute representation;
7. fit frozen learner;
8. score validation set;
9. record program/language complexity components and apply only a
   preregistered penalty;
10. write score artifact.

- [x] Reuse frozen V3.2 learner settings and the 500-example stage-one score.
- [x] Reuse deterministic 2,000-example validation split and 500-example
  training-subset machinery.
- [x] Keep candidate input data-only; return scalar accuracy/score and omit
  labels, predictions, and confusion matrices from evaluator output.
- [x] Store score artifacts and evaluator logs outside the candidate directory.
- [x] Hash the evaluator entrypoint, LLMAO source, frozen protocol/language
  manifests, environment record, and dependency configuration.
- [x] Record candidate validation and evaluator failures in structured artifacts.
- [x] Record program and language complexity components separately.
- [ ] Freeze the language-complexity definition and coefficient in the final
  preregistration before producing a V4 discovery fitness value.

The evaluator currently emits the frozen V3.2 stage-one score for smoke and
integration use. It marks `discovery_ready` false and `discovery_fitness` null
until the language-complexity penalty and remaining preregistration decisions
are frozen. No scientific candidate evaluation or discovery run has been
launched.

---

# Phase 7 — Boundary and leakage tests

EvE must never edit scientific infrastructure.

The V4 typed interpreter and candidate loader now reject executable payloads,
unknown operations, extra candidate files, and test-label fields. This static
boundary is covered independently from the EvE worker sandbox; the worker-side
read-only and filesystem/network enforcement remains pending below.

- [ ] Make evaluator files read-only to agent.
- [ ] Make dataset loader read-only.
- [ ] Make learner configuration read-only.
- [ ] Make protocol manifest read-only.
- [ ] Make train/validation indices read-only.
- [x] Keep labels and test data out of the candidate AST and score artifact.
- [x] Reject candidate filesystem payloads and executable operation names.
- [x] Reject network, subprocess, and dynamic-import operations in candidate ASTs.
- [ ] Enforce the same restrictions in the EvE worker sandbox.
- [ ] Verify deterministic execution.

Attack tests:

- [x] candidate tries reading labels;
- [x] candidate tries opening test data;
- [ ] candidate modifies evaluator;
- [x] candidate imports sklearn model;
- [x] candidate writes global state;
- [x] candidate calls network;
- [x] candidate creates raw-pixel passthrough;
- [x] candidate expands beyond dimension cap.

All must fail.

---

# Phase 8 — Create EvE LLMAO task

Create EvE-side configs:

```text
configs/eve/application/llmao_v4.yaml
configs/eve/evaluation/llmao_v4.yaml
configs/eve/optimizer/llmao_v4.yaml
configs/eve/llmao_v4.yaml
```

Application:

- [x] snapshot only the minimal G0 candidate task; the evaluation wrapper
  requires the clean LLMAO checkout at the exact `LLMAO_EXPECTED_COMMIT`;
- [x] allow edits only to `candidate/program.json` for the frozen-language
  smoke; keep `candidate/language.json` read-only until the Phase 9 gate passes;
- [x] assign zero score to boundary violations and reject the candidate.

Evaluation:

- [x] invoke the pinned V4 evaluator and keep its artifacts in the EvE log
  directory;
- [x] convert only the draft V3.2 stage-one score to EvE's scalar score;
- [x] return candidate identity, accuracy, dimensions, runtimes, protocol
  status, evaluator digest, and a structured failure summary.

Optimizer prompt:

- [x] explain the typed DSL and expose the pinned G0 manifest/current language;
- [x] expose candidate and evaluator history through sampled solver examples
  and their score/log artifacts;
- [x] ask the agent to propose either:
  - better program;
  - useful abstraction;
  - both.
- [x] explicitly prohibit evaluator modification and executable candidate data.

---

# Phase 9 — EvE smoke test with frozen language

Before allowing \(G\) to evolve:

\[
G_t=G_0.
\]

- [x] Run EvE with `language.json` read-only.
- [x] Allow only `program.json` modification in the solver snapshot; keep the
  separate optimizer guidance artifact explicitly scoped.
- [x] Run five candidate attempts in the initial smoke and two in the
  optimizer-guidance follow-up; six attempts produced valid stage-one scores.
- [x] Verify EvE solver population.
- [x] Verify guidance population evolves in a two-iteration follow-up: optimizer
  population grew from one to three entries, and guidance changed between
  iterations.
- [x] Verify score feedback returns correctly.
- [x] Verify valid candidates remain within limits. The `flatten_pixels(image())`
  proposal (784 features) failed candidate-context validation before scoring;
  it was not recorded as a scored 128-feature-cap rejection.
- [x] Verify per-rollout token usage logging.
- [x] Verify no cross-workspace contamination.

Frozen-G0 smoke evidence (2026-10-14): the initial five-iteration run had four
valid stage-one proposals and one candidate-context validation failure. Its
seed scored 0.4906 (`accuracy_500=0.493`, 6 features), and its best proposal
scored 0.8933 (`accuracy_500=0.8985`, 89 features). In the follow-up, both
proposals received valid stage-one scores; optimizer population grew from one
to three entries. `candidate/language.json` and the G0 reference remained
byte-identical across worker snapshots, while only `candidate/program.json`
changed in each solver workspace. One attempted `flatten_pixels(image())`
proposal represented 784 features and failed candidate-context validation
before scoring. All six successful scores are draft V3.2 stage-one feedback,
not discovery results; `discovery_ready=false` and `discovery_fitness=null`.
Token totals, run IDs, commits, failed setup attempts, and exact candidate
scores are recorded in `results/v4/smoke_manifest.json`.

Gate:

> EvE must reproduce ordinary representation search before language evolution is enabled.

The frozen-language smoke gate is satisfied. Phase 10 is next. Its numeric
acceptance gates are recorded; validate the isolated language-pilot config and
lineage handoff before enabling language edits. Do not start Phase 12 discovery
or emit discovery fitness until the pending Phase 0 preregistration decisions
are resolved and the final protocol is hashed.

---

# Phase 10 — Enable language evolution

Before the pilot:

- [x] Predeclare numeric pilot gates, macro/resource limits, and stop rules in
  `V4_PROTOCOL.md` and `results/v4/protocol.json`; then refresh the protocol
  digest.
- [x] Keep pilot feedback marked stage-one-only while discovery penalty and
  primary-study decisions remain unresolved.
- [x] Compose the isolated EvE application, optimizer, and evaluator groups;
  permit only `candidate/language.json` and `candidate/program.json` edits.
- [x] Validate evaluator-managed parent-language lineage propagation through
  EvE solver-entry evaluation logs; keep the frozen Phase 9 evaluator unchanged.

Allow:

```text
language.json
program.json
```

to evolve jointly.

- [ ] Run exactly 10 candidate attempts; invalid and failing attempts count and
  are not replaced. The initial seed evaluation is separate from those attempts.
- [ ] Inspect every invented primitive manually.
- [ ] Inspect language lineage.
- [ ] Check invalid-rate.
- [ ] Check dead-primitive rate.
- [ ] Check duplicate abstractions.
- [ ] Check language bloat.
- [ ] Check whether agents simply rename existing operations.
- [ ] Check whether macros actually alter search behavior.

The fixed pilot gates are:

```text
10 candidate attempts; invalid/failing attempts count and are not replaced
valid stage-one candidates >= 8/10
every introduced macro is used by its introducing candidate
at least one introduced macro is used by a descendant
maximum 8 macros per language; at most 1 new macro per candidate
maximum expansion depth 6; expanded AST nodes 127; feature width 128
zero evaluator, data, label, test-partition, or workspace-boundary violations
```

Stop after 10 attempts or immediately on a protected-boundary or official-test
access violation. A failed gate requires a separately documented pilot plan
before another language run.

Lineage handoff: the pilot evaluator stores the last valid candidate ID,
generation, canonical language hash, and ordered language snapshots in
`evaluate/lineage_state.json`.
EvE carries this evaluator log with its solver entry. Each evaluation reads the
state from the selected prefill example and appends the current language only
after candidate-context validation succeeds; context failures preserve the
last valid state. The V4 parent ID refers to that last valid language ancestor,
and the EvE prefill entry ID is stored separately for audit.

---

# Phase 11 — Add language lineage archive

- [ ] Store every unique language.
- [ ] Store parent-child edges.
- [ ] Store primitive birth generation.
- [ ] Store primitive death/removal.
- [ ] Store candidate score using each primitive.
- [ ] Track primitive descendant frequency.
- [ ] Track primitive reuse by independent agents.
- [ ] Generate lineage graph.

Output:

```text
results/v4/discovery/language_lineage.json
```

---

# Phase 12 — Run full language discovery

Primary discovery condition:

```text
EvE
+ GPT-6 Luna
+ max reasoning
+ G0 initial language
+ language evolution enabled
```

- [ ] Predeclare candidate/token budget.
- [ ] Predeclare independent seeds.
- [ ] Run matched independent searches.
- [ ] Store every solver candidate.
- [ ] Store every language.
- [ ] Store every agent guidance revision.
- [ ] Store token usage.
- [ ] Store search trajectory.
- [ ] Store primitive lineage.

Do not access official test results.

---

# Phase 13 — Select and freeze \(G^*\)

Selection must use only discovery evidence.

- [ ] Predeclare language-selection rule.
- [ ] Select \(G^*\).
- [ ] Export canonical language manifest.
- [ ] Hash \(G^*\).
- [ ] Freeze primitive definitions.
- [ ] Freeze names/descriptions.
- [ ] Freeze compiler.
- [ ] Freeze evaluator.
- [ ] Freeze dataset protocol.
- [ ] Record all hashes in `results/v4/frozen_manifest.json`.

Important:

> Do not carry the winning representation or EvE population into primary language evaluation.

---

# Phase 14 — Fresh-search experiment

Restart every optimizer from scratch.

Run:

```text
G0 + fixed iterative Codex
GH + fixed iterative Codex
G* + fixed iterative Codex

G0 + EvE
GH + EvE
G* + EvE
```

- [ ] Same initial candidate seeds.
- [ ] Same candidate budget.
- [ ] Same token budget/accounting.
- [ ] Same model.
- [ ] Same reasoning level.
- [ ] Same evaluation data.
- [ ] Same run seeds.

Primary metrics:

- [ ] best-so-far search curve;
- [ ] candidate-budget AUC;
- [ ] token-budget AUC;
- [ ] time-to-threshold;
- [ ] final best score;
- [ ] valid proposal rate;
- [ ] duplicate rate.

Primary hypothesis:

\[
AUC(G^*) > AUC(G_0).
\]

---

# Phase 15 — Semantic-language ablation

Construct:

```text
G*_semantic
G*_anonymous
```

with identical computational behavior.

- [ ] deterministically anonymize primitive names;
- [ ] anonymize descriptions;
- [ ] preserve signatures;
- [ ] preserve implementations;
- [ ] preserve parameter names where required for execution only;
- [ ] verify bit-identical primitive output.

Run matched fresh searches.

Measure:

\[
\Delta_{\text{semantic}}
=
AUC(G^*_{\text{semantic}})
-
AUC(G^*_{\text{anonymous}}).
\]

This separates:

```text
computational vocabulary
```

from:

```text
semantic vocabulary available to the LLM
```

---

# Phase 16 — Primitive reuse analysis

For every invented primitive:

- [ ] number of independent candidates using it;
- [ ] number of independent runs using it;
- [ ] score distribution with/without it;
- [ ] generations survived;
- [ ] descendants;
- [ ] semantic similarity to V3 primitives;
- [ ] structural equivalence to existing DSL expressions.

Identify:

```text
one-off tricks
vs
reusable abstractions
```

---

# Phase 17 — Transfer test

Freeze \(G^*_{\text{MNIST}}\).

Fresh search on:

```text
EMNIST Digits
EMNIST Letters
KMNIST
Fashion-MNIST
```

Primary comparison:

\[
Search(G^*_{\text{MNIST}})
\quad vs\quad
Search(G_0).
\]

Do not transfer the MNIST winning representation.

Transfer only the language.

This is the critical distinction.

Measure:

- [ ] search AUC;
- [ ] final fitness;
- [ ] time-to-threshold;
- [ ] which invented primitives are reused;
- [ ] which primitives disappear;
- [ ] which new abstractions are added.

---

# Phase 18 — Human DSL comparison

Compare:

\[
G_0,\quad G_H,\quad G^*.
\]

Questions:

- [ ] Does evolved \(G^*\) rediscover V3 relational concepts?
- [ ] Does \(G^*\) contain abstractions absent from V3?
- [ ] Is \(G^*\) smaller or larger than \(G_H\)?
- [ ] Which language gives better fresh-search AUC?
- [ ] Which language transfers better?
- [ ] Which language needs fewer candidate evaluations?

---

# Phase 19 — Optimizer-language interaction

Use the \(3\times2\) design to test whether:

\[
\text{language effect}
\]

depends on:

\[
\text{optimizer}.
\]

Specifically compare:

\[
\Delta_G^{fixed}
=
AUC(G^*,fixed)-AUC(G_0,fixed)
\]

and

\[
\Delta_G^{EvE}
=
AUC(G^*,EvE)-AUC(G_0,EvE).
\]

This answers:

> Does an adaptive optimizer exploit an evolved language differently from a fixed optimizer?

Secondary result only; not the primary RQ.

---

# Phase 20 — Optional Level B primitive synthesis

Only after macro evolution works.

- [ ] Define restricted numerical primitive language.
- [ ] Add generated primitive body validator.
- [ ] Add deterministic sandbox.
- [ ] Ban labels/datasets/models/imports/network.
- [ ] Add CPU/runtime limit.
- [ ] Add memory limit.
- [ ] Add semantic equivalence checks.
- [ ] Repeat pilot.

Do not mix Level A and Level B results.

---

# Phase 21 — Statistics

For primary comparisons:

- [ ] use multiple independent search seeds;
- [ ] retain complete trajectories;
- [ ] bootstrap differences in search AUC;
- [ ] report paired comparisons where seeds/budgets align;
- [ ] report individual run results;
- [ ] do not rely only on mean final score;
- [ ] do not treat LLM calls as independent statistical samples.

---

# Phase 22 — Final report

Generate:

```text
reports/V4_LANGUAGE_OF_BIAS.md
```

Required sections:

1. Research question
2. Why fixed DSL is a hidden human inductive bias
3. V4 architecture
4. Language evolution mechanism
5. EvE setup
6. Discovery results
7. Language lineage
8. Fresh-search experiment
9. Human DSL comparison
10. Semantic ablation
11. Transfer
12. Primitive reuse
13. Failure modes
14. Attribution limits
15. What the system actually discovered

Final conclusion must distinguish:

```text
discovered a good representation
```

from:

```text
discovered a useful representation language
```

and from:

```text
discovered a generally reusable inductive-bias vocabulary.
```

These are three different claims.
