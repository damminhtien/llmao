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

### V4 artifact storage boundary

Keep persistent V4 outputs, scratch, and dataset caches under `results/v4/` in
the LLMAO checkout. The pinned EvE checkout and user-managed runtime credentials
are explicit external inputs, not output roots. The new layout must keep the
MNIST cache evaluator-only and prove that Codex workers cannot read it. New
writers must reject paths that resolve outside `results/v4/`; existing frozen
artifacts retain their original locations. See
[`docs/V4_ARTIFACT_STORAGE_ARCHITECTURE.md`](docs/V4_ARTIFACT_STORAGE_ARCHITECTURE.md)
for the audited paths and migration contract.

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

For the Phase 10 EvE pilot, the evaluator stores the last valid V4 candidate
ID, generation, canonical language hash, and ordered language snapshots in
`evaluate/lineage_state.json`. EvE carries that evaluator log with each solver
entry and exposes it through read-only solver examples. The pilot evaluator
loads the state attached to EvE's selected prefill entry, passes its language
snapshots to the context builder, and appends the current snapshot only after
candidate-context validation succeeds. If validation fails, the evaluator
keeps the inherited valid state so later attempts can recover from it. The
EvE prefill entry ID is recorded separately from the V4 parent candidate ID;
the latter names the last valid language ancestor. This history stays outside
the two-file candidate directory and is never accepted from worker-authored
candidate data.

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

V4 Codex workers use EvE's `codex_tmux` driver through
`scripts/codex-v4-sandbox`. The wrapper removes the driver's legacy
`-s workspace-write` argument and installs the named
`llmao-v4-workspace-only` permission profile in the isolated Codex home.
The profile denies root access except the minimal system runtime, grants
read access to the workspace and pinned Python/runtime dependencies, permits
writes only to the four declared candidate JSON paths, and denies shell
network access, `/tmp`, and `$TMPDIR`. Workspace legacy sandbox configuration
and CLI policy overrides are rejected. Hooks, web search, multi-agent mode,
and the remote plugin catalog are disabled for the fixture. Do not use
`codex_exec` for scientific workers: its runtime bypasses the sandbox.

`experiments/v4_sandbox_preflight.py` checks actual OS enforcement without a
model. The native fixture runs this gate before creating a tmux worker. The
checker launcher first probes the project venv, then runs its resolved Python
binary with explicit venv site-packages; macOS denied traversal through the
venv's Homebrew interpreter symlink under the strict read policy.

The data-free `20261015-native-boundary-04` fixture passed the automated
preflight and all fifteen native postconditions, including valid/invalid
checker feedback, temporary-write denials, outside-read denial, unchanged
candidates, and a clean workspace. The earlier `native-boundary-02` verified
temporary writes under the legacy policy only. These fixtures do not establish
scientific-worker enforcement across a complete pilot. See
`V4_SANDBOX_REPAIR.md` for commands, evidence, and remaining contract gates.

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

The Phase 10 configuration uses a separate application, optimizer, and
evaluator group while retaining the frozen `llmao_v4` root config. It samples
up to 32 prior solvers per iteration, enough to include the complete population
for the ten-attempt pilot. The evaluator receives those solver examples and
their evaluator logs; it does not modify EvE's algorithm core or the frozen
Phase 9 evaluator.

### Phase 10 exploratory pilot outcome

The 2026-10-14 pilot completed ten proposals plus a separate seed evaluation.
Six proposals received valid V3.2 stage-one scores and four failed candidate
context validation, missing the preregistered minimum of eight valid proposals.
The best recorded accuracy was 0.873 on 500 examples with 33 features. This is
feasibility evidence only; `discovery_fitness` remains null and the result does
not establish a search improvement.

Lineage checks confirmed macro inheritance and descendant use. The run also
exposed two depth-7 proposals rejected against the depth-6 cap, two exact macro
reintroductions on separate branches, two duplicate candidate IDs, and one
accepted language carrying an unused inherited macro. No protected data or
workspace-boundary violation was found. The reviewed run summary is in
`V4_PHASE10_PILOT_REPORT.md`; candidate files, lineage snapshots, and raw
telemetry are preserved locally under `results/v4/phase10_pilot/`, which the
repository intentionally excludes from Git.

The pilot gate failed. `V4_PILOT_RESPONSE_PLAN.md` records the response and
preserves its result. Another exploratory pilot requires that plan's tooling,
configuration, and contract checks. Primary discovery requires completed and
hashed Phase 0 preregistration.

The follow-up is separately pinned in `V4_FOLLOWUP_PILOT_CONTRACT.json`.
It keeps the original G0 seed, stage-one score, learner, ten-proposal budget,
one worker, and original resource/boundary gates. Its additional quality gate
requires eight distinct valid expanded-program hashes among the ten proposals.
This measures structural diversity, not semantic or statistical independence.
Workers receive a digest-verified data-free structural checker; checks share
the existing turn/time budget and never return scores. Invalid, failed, and
repeated final submissions still count. Primary discovery remains closed until
final preregistration.

Future structural bundles include a hashed `run_check.sh` launcher bound to
the verified project Python entrypoint. The exporter records the interpreter
and dependency versions. This removes dependence on `LLMAO_PYTHON` propagation
through native worker shells. Four focused bundle tests pass; native worker
integration remains pending. The running follow-up retains its original
21-file bundle and frozen contract.

Structural replay records context acceptance separately from score success.
An accepted candidate whose evaluation fails keeps its original failed score
and can supply the evaluator-owned parent state for a later descendant.
Replay verifies both state transitions and candidate contents; successful
stage-one score counts exclude these failures.

The follow-up ended after ten proposals with eight valid scores and eight
distinct valid expanded ASTs. Its overall gate failed: none of four invented
macro behaviors was used by a descendant, and native transcripts exposed
noncandidate temporary writes while workers tried to repair missing checker
dependencies. Immutable workspace checks did not detect those host effects.
`V4_PHASE10_FOLLOWUP_REPORT.md` records the complete audit and preserved
evidence; `V4_FOLLOWUP_RESPONSE_PLAN.md` defines the required interface and
boundary fixes before another fresh pilot. Primary discovery remains closed.

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

`V4_PRIMARY_DESIGN.md` fixes the discovery language cost as invented macro
count with coefficient 0.0005. Fresh frozen-language searches retain the
unchanged stage-one score. It also fixes the common 200-unique-evaluation target,
540 adaptive-proposal cap, token/turn/time budgets, separate discovery and fresh
seed sets, discovery-only selection, paired primary AUC contrast, and numeric
support criteria. Final implementation/configuration pins and the canonical
protocol hash remain launch requirements. No primary discovery has started.

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

The archive distinguishes each scored observation from candidate content,
language revisions, computational macro behavior, and expanded programs.
Repeated proposals retain their separate scores and timing measurements.
Invalid proposals remain in the attempt ledger but never create valid language
nodes. Source file digests and canonical lineage chains must verify before
archiving. The archive records births, removals, inherited use, and unused
macro inventory; separate worker-entry IDs do not establish independent search
reuse. A declared independent-search identity is required for that measure.

The implemented pilot importer is `experiments/v4_archive_lineage.py`. It
verifies artifact digests, canonical lineage state, previously accepted
parents, and score telemetry through `candidate/replay.py`, then builds the
archive through `v4/lineage.py`. The data-free author check is
`experiments/v4_check_candidate.py`; it reuses evaluator validation and reports
expanded structural limits without reading examples or generating a score.
The first pilot archive contains five language nodes including G0, four edges,
two valid macro behaviors, and eleven observations including the seed. The
six valid proposals contain three distinct expanded representations. The
archive describes exploratory evidence; primary discovery remains pending.

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

`V4_INITIAL_PROGRAMS.json` freezes twenty distinct ASTs in their original
V3.2 protocol order, read from the pinned source commit. The manifest records
canonical AST identities, historical candidate identities, static dimensions,
depths, node counts, and used operations. All programs pass G0 constraints and
use operations available in GH. It includes no historical scores or proposer
descriptions. Fresh G* searches start from these same base ASTs without
substituting discovered macros. Its digest must be bound into the final primary
protocol before launch; the running pilot keeps its original one-program seed.

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
