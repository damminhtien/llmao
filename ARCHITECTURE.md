# LLMAO V4 — Evolving the Language of Inductive Bias

## 1. Research question

### Primary RQ

> **Can an LLM invent reusable abstractions that make useful inductive biases easier to discover?**

The goal is no longer only to search for a good representation inside a human-designed language.

V4 asks whether the system can modify the language in which representations are expressed, and whether the resulting language improves subsequent search.

Formally, previous versions optimize

\[
z^* = \arg\max_{z\in G_{\text{human}}} J(z),
\]

where \(G_{\text{human}}\) is a fixed representation language.

V4 introduces

\[
G^*, z^*
=
\arg\max_{G,\;z\in G} J(z),
\]

but the scientific claim is not established by the performance of the jointly discovered pair \((G^*,z^*)\).

The critical test is:

\[
\boxed{
\text{freeze }G^*
\rightarrow
\text{restart search from scratch}
\rightarrow
\text{measure whether search is easier}
}
\]

If a fresh optimizer searches more effectively under \(G^*\) than under the original language \(G_0\), then the system has discovered something reusable about how inductive biases should be expressed.

---

# 2. Scientific decomposition

V4 contains three evolving objects:

\[
\boxed{
z_t,\quad G_t,\quad \phi_t
}
\]

where:

- \(z_t\): representation program;
- \(G_t\): language / DSL used to express representations;
- \(\phi_t\): optimizer/agent strategy used to search.

Interpretation:

\[
G_t
\rightarrow
\text{defines what can be expressed easily}
\]

\[
\phi_t
\rightarrow
\text{defines how that space is searched}
\]

\[
z_t
\rightarrow
\text{is one concrete inductive bias found in that space}.
\]

EvE is responsible for evolving solver candidates and optimizer guidance.

LLMAO remains responsible for:

- the bias language;
- candidate validation;
- representation execution;
- the fixed downstream learner;
- datasets and splits;
- scientific controls;
- final attribution.

EvE is therefore an experimental instrument, not the research contribution.

---

# 3. Research boundary

V3, V3.1 and V3.2 remain frozen.

V4 must not rewrite previous:

- candidates;
- reports;
- protocols;
- evaluator results;
- finalist manifests.

The initial V4 language is derived from the existing typed DSL, but V4 has a separate namespace and cache.

During discovery:

- the LLM never receives official test labels;
- the LLM does not choose the downstream classifier;
- the learner configuration is frozen;
- candidate programs cannot access dataset labels;
- language primitives cannot access dataset labels;
- evaluator code is immutable to the EvE agents;
- official test partitions remain inaccessible until language and finalists are frozen.

---

# 4. Key experimental idea

The most important separation is:

## Discovery

Jointly evolve:

\[
(G_t,z_t,\phi_t).
\]

This phase answers:

> Can the system produce promising languages and programs?

It does **not** establish that a language is intrinsically better.

## Language evaluation

Freeze a discovered language:

\[
G^*.
\]

Discard:

- the representation that discovered it;
- search history;
- optimizer state;
- EvE population.

Restart search from scratch.

Compare:

\[
Search(G_0)
\quad\text{vs}\quad
Search(G^*)
\]

under identical budgets.

This phase answers the actual RQ:

> Does the discovered language make useful biases easier to find?

---

# 5. Languages used in the experiment

Three language conditions are required.

## \(G_0\): impoverished starting language

Use the frozen V2-level DSL as the starting vocabulary.

In particular, do not expose the complete V3 relational additions as built-in primitives.

This is useful because V3 already provides a human-designed reference for relational abstraction.

The starting language should retain low-level structural primitives such as:

```text
image
threshold
skeletonize
graph
paths
degree_sequence
edge_lengths
angles
delta
histogram
moments
quantiles
...
```

but exclude the manually introduced V3 abstractions such as:

```text
spatial_condition
pairwise_difference
cross_histogram
path_summary
```

This creates a useful positive control:

> Does V4 independently rediscover abstractions resembling the useful V3 relational structures?

---

## \(G_H\): human-designed language

The full frozen V3 language.

This is not part of V4 discovery.

It is an external reference:

\[
G_H = G_{\text{V3-human}}
\]

against which evolved languages can be compared.

---

## \(G^*\): evolved language

A language produced during V4 discovery.

It consists of:

\[
G^* = G_0 \cup \Delta G.
\]

Every addition must have:

```text
primitive ID
human-readable name
input types
output type
definition
parameter schema
complexity cost
provenance
parent-language hash
```

---

# 6. Two levels of language evolution

## Level A — typed macro invention

Required for the first V4 implementation.

An invented primitive is a reusable abstraction composed from existing typed operations.

Example:

```text
stroke_turn_profile(image())
```

could internally compile to a bounded G0 composition of:

```text
image
skeletonize
graph
paths
angles
histogram
```

A macro:

- has a static signature;
- expands to an existing valid AST;
- cannot execute arbitrary Python;
- is deterministic;
- can be hashed canonically.

This tests whether the system can invent a **better vocabulary/search representation**.

V4 allows at most eight macros in a language and at most one newly introduced
macro per candidate. Each macro remains within the existing caps of expansion
depth 6, 127 expanded AST nodes, and 128 output features. These limits are
serialized with each language and enforced by the typed validator.

Macro bodies may use only the operations available in their parent language,
including previously validated macros. Their transitive expansion must stay
inside the `G_0` computational vocabulary. Hidden calls to excluded `G_H`
operations would leak the human reference into discovery. Level A preserves
the computational expressivity of `G_0`; rediscovery of a V3 abstraction is
possible only when its behavior can be expressed using those base operations.

---

## Level B — primitive synthesis

Optional second stage.

Allow the system to implement genuinely new operations rather than only macros.

Generated primitive bodies must pass a restricted program validator.

Allowed operations should be limited to pure numerical/geometric transformations.

Forbidden:

```text
network
filesystem
subprocess
dynamic imports
eval/exec
model inference
dataset access
labels
global mutable state
randomness without controlled seed
```

Primitive synthesis is scientifically stronger but should not be enabled until Level A is stable.

---

# 7. Candidate representation

Each V4 solver candidate is:

\[
C=(G,z)
\]

with provenance:

```text
candidate_id
parent_candidate_id
language_hash
parent_language_hash
program_hash
new_primitives
used_primitives
agent_id
agent_guidance_hash
generation
evaluation_seed
```

A language modification is accepted only if its newly introduced primitive is actually used by the submitted representation.

This prevents accumulation of irrelevant dead primitives.

---

# 8. V4 execution architecture

```text
                         EvE
                          │
             ┌────────────┴────────────┐
             │                         │
      Agent population          Solver population
          φ1, φ2, ...          (G1,z1), (G2,z2), ...
             │                         │
             └────────────┬────────────┘
                          │
                     Codex agent
                   GPT-6 Luna / max
                          │
                 candidate workspace
                  ┌───────┴────────┐
                  │                │
             language ΔG       program z
                  │                │
                  └───────┬────────┘
                          ▼
                static validation gates
                          │
          ┌───────────────┼────────────────┐
          ▼               ▼                ▼
       typing          language         resource
       checks          boundary          limits
          └───────────────┬────────────────┘
                          ▼
                  deterministic compiler
                          │
                          ▼
                   representation
                          │
                          ▼
              fixed train/validation learner
                          │
                          ▼
                       score
                          │
                 ┌────────┴─────────┐
                 ▼                  ▼
           solver evidence     EvE feedback
                                    │
                                    ▼
                             evolving φ
```

---

# 9. Repository separation

Do not put EvE implementation inside LLMAO.

Use:

```text
scaling-group/eve
        │
        │ orchestrates
        ▼
damminhtien/llmao
```

Pin both repositories to exact commits in every experiment manifest.

LLMAO exposes a V4 task interface to EvE.

Suggested LLMAO structure:

```text
src/bias_optimizer/v4/
├── schema.py
│
├── language/
│   ├── types.py
│   ├── base_language.py
│   ├── manifest.py
│   ├── macro.py
│   ├── validator.py
│   ├── compiler.py
│   ├── runtime.py
│   └── hashing.py
│
├── candidate/
│   ├── schema.py
│   ├── loader.py
│   └── provenance.py
│
├── evaluator.py
│
├── evaluation/
│   ├── candidate.py
│   ├── fresh_search.py
│   ├── transfer.py
│   ├── metrics.py
│   └── artifacts.py
│
└── eve/
    ├── interface.py
    ├── score_writer.py
    └── boundary.py

experiments/
├── v4_evaluate_candidate.py
├── v4_discovery.py
├── v4_fresh_search.py
├── v4_language_ablation.py
└── v4_transfer.py

results/v4/
reports/
└── V4_LANGUAGE_OF_BIAS.md
```

## Existing LLMAO interfaces to reuse

The V4 implementation belongs in its own `src/bias_optimizer/v4/` and
`results/v4/` namespaces. The existing V3.2 implementation supplies bounded
execution and evaluation components:

- `dsl/ast.py::Expr` provides immutable, canonical JSON expression trees.
- `dsl/primitives.py::PRIMITIVES` contains the V3.2 primitive definitions and
  deterministic executors. It includes the human-added V3 operations
  `spatial_condition`, `pairwise_difference`, `cross_histogram`, and
  `path_summary`.
- `dsl/validator.py` and `dsl/compiler.py` provide typed validation and the
  allow-listed interpreter. They currently validate against the global
  `PRIMITIVES` mapping, so V4 must validate each language against its own
  manifest before compiling an expanded base AST. V4 must not mutate the
  global primitive mapping.
- `ml/evaluator.py::ProgramEvaluator` and `Evaluator` provide the existing
  fixed learner and train/validation evaluation path. V4 must keep official
  test partitions outside candidate evaluation.
- `optimizer_bench/objective.py::ast_hash` and `stage_one_fitness` provide
  canonical program identity and the frozen V3.2 stage-one ranking score.
- `novelty/map_elites.py::MapElitesArchive` and
  `llm/program_proposer.py::ProgramProposer` are available for reuse where
  their V4 provenance and budget requirements are met.

`G_0` is a V4-owned allow-list derived from the frozen V2-level language.
`G_H` uses the full frozen V3 language. Keep both definitions separate from
the shared V3.2 `PRIMITIVES` registry; macro expansion must resolve to a
validated base AST before reaching the existing evaluator.

The previous V3/V3.1 architecture and completed V3.1 checklist are retained in
`ARCHITECTURE_V3_REFERENCE.md` and `TODO_V3_1.md`. V4 protocol pins and
protected artifact hashes belong in `results/v4/protocol.json`.

---

# 10. EvE task boundary

EvE agents must not be allowed to edit LLMAO evaluator code.

Editable candidate area should contain only something equivalent to:

```text
candidate/
├── language.json
├── program.json
└── primitives/
```

Everything else is immutable.

EvE application boundary:

```text
editable:
    candidate/language.json
    candidate/program.json
    candidate/primitives/*
```

Evaluator-managed context (outside the candidate directory) carries the
candidate ID, provenance, and validated parent-language history. The worker
cannot edit this context. The evaluator reads only `language.json` and
`program.json` from the candidate directory.

Evaluator:

```text
python experiments/v4_evaluate_candidate.py candidate/ --context run_context.json
```

The evaluator writes its score artifact and log outside the candidate
directory. Its artifact includes the frozen stage-one score and separate
program/language complexity measurements. Until the language-complexity
penalty is preregistered, `discovery_fitness` remains null and the artifact is
not eligible for a V4 discovery run. Score feedback contains no labels,
predictions, or confusion matrix.

An agent modifying:

```text
evaluator
dataset loader
learner
metric
split
test data
```

must receive a hard failure.

V4 Codex workers use EvE's `codex_tmux` driver with `workspace-write`
sandboxing, agent-shell network access disabled, web search disabled, and
multi-agent mode disabled. Do not use `codex_exec` for scientific workers: its
runtime passes `--dangerously-bypass-approvals-and-sandbox`. EvE creates a
per-workspace Codex home, so the worker uses the pinned model and reasoning
settings without loading the user's global Codex configuration.

The Phase 9 EvE smoke snapshots only the candidate JSON and the pinned G0
manifest. Its evaluator uses a separately configured, clean LLMAO checkout at
the exact `LLMAO_EXPECTED_COMMIT`; the evaluator source and data cache are not
copied into the worker snapshot. Within `solver/`, only
`candidate/program.json` is editable during this frozen-language phase; keep
`candidate/language.json` identical to G0. EvE's separate optimizer artifact
`guidance/V4_SEARCH_GUIDANCE.md` may evolve with concise, evidence-grounded
search rules; it is optimizer state and does not modify the candidate
language.

The Phase 9 gate passed on 2026-10-14 after a five-iteration frozen-G0 smoke
and a two-iteration optimizer-guidance follow-up. The runs verified score
feedback, candidate-workspace isolation, and separate optimizer-guidance
updates. Six of seven proposals received valid stage-one scores. One proposal
submitted `flatten_pixels(image())` (784 features) and failed candidate-context
validation before scoring. The highest observed stage-one score was 0.8933 at
89 features. These smoke scores are not V4 discovery fitness. The next
language-editing pilot must be separately configured and its acceptance gates
recorded before launch; primary discovery remains closed until Phase 0
preregistration is complete.

The agent workspace contains the candidate artifacts and separate task
guidance. During Phase 9, EvE's solver boundary rejects changes to every solver
path except `candidate/program.json`. A Phase 10 pilot may add
`candidate/language.json` to that explicit allow-list; every other solver path
must remain immutable. EvE records changes to
`guidance/V4_SEARCH_GUIDANCE.md` separately as optimizer state. The submitted
program and language are JSON for the allow-listed typed interpreter; neither
can execute agent-authored Python. The evaluator returns scalar fitness and
structured failure summaries, not training or validation examples or labels.

---

# 11. Discovery objective

Reuse the core V3 representation objective initially.

For example:

\[
J(z)
=
Acc_{500}(z)
-\lambda_d\log(1+d_z)
-\lambda_t\log(1+t_z)
-\lambda_c C(z).
\]

Add a small language complexity cost:

\[
J_{V4}(G,z)
=
J(z)-\lambda_G C(G).
\]

\(C(G)\) can include:

- number of invented primitives;
- expanded AST size;
- primitive implementation complexity.

Do not reward a primitive merely for having a sophisticated name or explanation.

The main V4 claim will not rely on this discovery score.

---

# 12. Language provenance graph

Every language forms a node:

\[
G_i.
\]

A mutation creates:

\[
G_i \rightarrow G_j.
\]

Store:

```text
added primitive
removed primitive
renamed primitive
primitive body change
candidate score before/after
reuse count
descendant count
```

This produces a language lineage graph.

We should be able to reconstruct:

```text
G0
 │
 ├── G1
 │    └── G4
 │         └── G9
 │
 └── G2
      └── G7
```

This is necessary for analyzing how abstractions emerge.

---

# 13. Reuse as evidence

An invented primitive becomes scientifically interesting when it is repeatedly useful.

Track:

\[
R(p)=
\#\{\text{independent high-performing programs using }p\}.
\]

Also track whether it survives:

- independent search restarts;
- different training seeds;
- new datasets.

A one-off primitive that occurs in one winning candidate is weak evidence.

A primitive that repeatedly reappears is evidence for a reusable abstraction.

---

# 14. Freeze protocol

After discovery, freeze:

```text
G*
language hash
primitive definitions
primitive names
compiler version
evaluator version
dataset split protocol
backend model
Codex CLI version
EvE commit
LLMAO commit
```

No language changes are allowed afterward.

The representation \(z^*\) that produced \(G^*\) is **not** reused in the primary language evaluation.

---

# 15. Primary fresh-search experiment

Run a new search from scratch under:

\[
\{G_0,G_H,G^*\}
\times
\{\text{Fixed Iterative Codex},\text{EvE}\}.
\]

This gives a \(3\times2\) design:

| Language | Fixed iterative | EvE |
|---|---:|---:|
| \(G_0\) base | ✓ | ✓ |
| \(G_H\) human V3 | ✓ | ✓ |
| \(G^*\) evolved | ✓ | ✓ |

Everything else must be matched:

```text
same Codex model
same reasoning level
same evaluator
same dataset indices
same candidate budget
same token accounting
same timeout
same seeds
same initial programs
```

Primary comparison:

\[
AUC(Search(G^*))
-
AUC(Search(G_0)).
\]

If positive under fresh search, \(G^*\) genuinely improved the search representation.

---

# 16. Primary metrics

Do not report only final accuracy.

For each search run record:

### Search efficiency

\[
AUC_{\text{search}}
\]

over best-so-far score versus candidate evaluations.

Also report best-so-far versus cumulative tokens.

### Time to threshold

\[
T_\tau
=
\min\{n:J_n\ge\tau\}.
\]

Use predeclared thresholds based on frozen V3 results.

### Final candidate quality

Best validation fitness at budget \(B\).

### Validity

```text
invalid proposal rate
duplicate rate
compile failure rate
runtime failure rate
```

### Language complexity

```text
number of primitives
expanded AST complexity
primitive reuse
primitive survival
```

---

# 17. Semantic ablation

V3.2 showed that names may matter.

V4 should distinguish:

\[
\text{computational abstraction}
\]

from

\[
\text{semantic affordance}.
\]

After freezing \(G^*\), create:

\[
G^*_{\text{semantic}}
\]

and

\[
G^*_{\text{anonymous}}.
\]

The two languages have identical:

- primitive implementations;
- signatures;
- parameter ranges;
- behavior.

Only names and descriptions are anonymized.

Then run fresh searches.

This tests:

> Does the LLM exploit the semantic meaning of the vocabulary that the system itself invented?

A strong result would be:

\[
Search(G^*_{\text{semantic}})
>
Search(G^*_{\text{anonymous}}).
\]

---

# 18. Transfer experiment

The strongest evidence for a learned language is transfer.

Discover:

\[
G^*_{\text{MNIST}}
\]

using MNIST only.

Freeze it.

Then start a fresh representation search on:

### Near-domain

EMNIST Digits.

### Medium-domain

EMNIST Letters.

### Far-domain controls

KMNIST / Fashion-MNIST.

Compare:

\[
Search(G_0)
\]

with

\[
Search(G^*_{\text{MNIST}}).
\]

The question is not whether the final MNIST representation transfers.

The question is whether the **vocabulary learned on MNIST makes new representations easier to discover on another task**.

That distinction is central to V4.

---

# 19. Human-language reference

Compare \(G^*\) with the manually designed V3 relational language \(G_H\).

Interesting outcomes include:

### Outcome A

\[
G^* \approx G_H
\]

and evolved primitives resemble human V3 relational primitives.

Interpretation:

The system independently reconstructs useful human-designed abstractions.

### Outcome B

\[
G^* > G_H.
\]

Interpretation:

The system discovers useful abstractions that were absent from the manually designed DSL.

### Outcome C

\[
G^* < G_H
\]

but transfers better.

Interpretation:

Search efficiency and transferability favor different abstraction languages.

### Outcome D

\[
G^*\approx G_0.
\]

Still informative if language evolution repeatedly collapses toward a small set of structural motifs.

---

# 20. Main attribution questions

V4 should distinguish four sources of improvement:

\[
\boxed{
\text{language}
+
\text{semantic prior}
+
\text{feedback}
+
\text{optimizer adaptation}
}
\]

Relevant controls:

```text
G0 + fixed iterative
G* + fixed iterative

G0 + EvE
G* + EvE

G* semantic
G* anonymized
```

This allows interaction analysis rather than only leaderboard comparison.

---

# 21. Success criterion

The primary RQ is supported only if:

1. \(G^*\) is frozen before primary evaluation;
2. search is restarted from scratch;
3. identical optimizer/budget conditions are used;
4. \(G^*\) improves search efficiency over \(G_0\);
5. the result survives independent seeds;
6. at least one evolved abstraction is reused across independent searches.

The strongest result would additionally show:

7. \(G^*\) helps on an unseen related task.

---

# 22. Claim ladder

The project should make claims only at the strongest level supported by evidence.

### Level 1

The system invented valid new abstractions.

### Level 2

Those abstractions were reused by independently discovered representations.

### Level 3

The evolved language improved fresh search on the original task.

### Level 4

The evolved language improved fresh search on an unseen task.

### Level 5

The system detected limitations of its current language and modified the language in a way that systematically improved future learning.

Level 5 is the long-term target.

---

# 23. Core interpretation

V4 is not primarily about obtaining a better MNIST classifier.

The object of study is:

\[
\boxed{\text{the formation of inductive bias}}
\]

More specifically:

\[
\text{data/evidence}
\rightarrow
\text{abstraction language}
\rightarrow
\text{inductive bias}
\rightarrow
\text{learner}.
\]

The central question is whether part of the abstraction language that humans normally provide can itself emerge from search and evaluation.
