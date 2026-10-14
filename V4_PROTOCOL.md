# LLMAO V4 — Language Evolution Protocol

Status: **draft, before discovery**. The canonical design is in
`results/v4/protocol.json`; its current snapshot digest is in
`results/v4/protocol.sha256`. A draft digest records the current document and
does not constitute final preregistration. Resolve the pending decisions below
and regenerate the digest before discovery or primary results.

## Research question and acceptance criteria

Can an LLM invent reusable abstractions that make useful inductive biases
easier to discover?

The primary claim requires a frozen evolved language, fresh optimizer runs,
matched budgets and data, improved search efficiency over the starting
language across independent seeds, and at least one invented abstraction
reused across independent searches. Transfer to an unseen related task would
support the stronger claim of a reusable vocabulary across tasks.

Joint discovery performance alone establishes neither language utility nor
transfer. Freeze the language and discard the discovering representation,
search history, guidance state, and EvE population before primary evaluation.

## Frozen prior work

V4 starts from integrated `main` commit
`ea6e1d6d268a10bdafc2061c73fcb2c694be9679`.

| Study | Preserved source commit |
|---|---|
| V3 | `1e9f29bd7f21863f84340b25e6b3e193c43d1220` |
| V3.1 | `798415cf847bf8d74e76c9f46f8cc272bc74725c` |
| V3.2 | `85beeaff62791946989b3163cd67fbaed7e7c108` |

`results/v4/baseline_manifest.json` records SHA-256 digests of the existing
tracked reports and results, the seven protected V2/V3 artifacts recorded by
V3.1, and the historical protocol and reference documents. V3.1 and V3.2
protocol digests and protected artifacts were verified when this draft was
created. Existing V3.2 incomplete-run statuses remain part of the evidence.

## Language and execution boundary

- `G0`: the frozen V2-level vocabulary, excluding `spatial_condition`,
  `pairwise_difference`, `cross_histogram`, and `path_summary`.
- `GH`: the full frozen human V3 vocabulary, used as a reference condition.
- `G*`: `G0` plus typed macros invented during discovery.

The canonical manifests for `G0` and `GH` are stored in
`results/v4/languages/g0.json` and `results/v4/languages/gh.json`. Their
SHA-256 identities are recorded in adjacent `.sha256` files and
`results/v4/protocol.json`. Each manifest records the typed input and output
contract, output-dimension rule, parameter schema, and primitive source digest.
`G0` pins the V2 primitive vocabulary at
`cab3e82fecf82326bb49690c22f9233824d55eae`; `GH` pins the full V3 vocabulary
at `1e9f29bd7f21863f84340b25e6b3e193c43d1220`.

Level A macro invention is the initial implementation. Each macro has a static
signature and closed parameter schema with defaults; candidates may override
those defaults with validated values. Language snapshots carry a parent hash,
and macro definitions have canonical hashes. Each candidate records its
language and program hashes, introduced and used macros, and lineage
provenance. Cycles, recursive definitions, unused new macros, and resource
limit violations fail validation. The current implementation defaults cap
both macro dependency depth and expanded AST depth at 6, expanded AST size at
127 nodes, and output width at 128 features, matching the V3.2 discovery
limits. The protocol caps each language at eight macros and each candidate at
one newly introduced macro. Language complexity is measured and reported, but
its discovery penalty definition and coefficient remain pending final
preregistration. Arbitrary Python and Level B primitive synthesis are excluded
from the initial experiment.
Macro bodies and their transitive expansions use only `G0` operations and
previously validated macros; hidden use of excluded `GH` operations is invalid.
Level A changes the vocabulary while preserving `G0` computational expressivity.

Candidate agents work in an EvE workspace containing candidate artifacts and
task guidance. The EvE boundary checker rejects edits outside the candidate
language and program files. Scientific workers must use the `codex_tmux` driver,
`workspace-write` sandboxing, disabled agent-shell network access, disabled web
search, and disabled multi-agent mode. The worker's Codex home is isolated from
the user's global Codex configuration. The evaluator and its data are kept
outside the candidate workspace; it returns scalar scores and structured
failure summaries only.

Candidates are JSON ASTs accepted by a deterministic allow-listed interpreter,
not agent-authored Python or executable code. Candidate execution has no
labels, dataset, network, filesystem, subprocess, dynamic imports, or model
inference. EvE's file boundary and the typed interpreter are separate gates;
neither substitutes for the other.

## Evaluator basis

Reuse the V3.2 stage-one evaluator: MNIST official training partition only,
a fixed stratified 2,000-example validation split with seed 42, and a
500-example training subset with seed 42. The learner is training-fitted
`StandardScaler` followed by logistic regression with `C=1`, `lbfgs`,
`max_iter=1000`, `tol=0.0001`, and `random_state=42`.

The V3.2 smoke evaluator was reproduced on the M2 Max before V4 discovery.
All four optimizer conditions completed 40 candidates. Their 20 frozen seed
programs matched the saved V3.2 traces exactly by candidate ID, accuracy, and
feature dimension; the largest fitness difference was below `0.001`, allowing
for runtime variation. Split fingerprints and reproduction traces are in
`results/v4/baseline_reproduction/summary.json` and `manifest.json`. The V3.2
protocol and manifest remained byte-for-byte unchanged.

The existing stage-one score is

```text
accuracy_500
- 0.001 * log1p(feature_dim)
- 0.0001 * log1p(feature_runtime_ms + training_runtime_ms + inference_runtime_ms)
```

Discovery adds a language complexity cost. Its exact definition and coefficient
must be fixed before discovery. Record accuracy, dimension, runtime, program
complexity, and language complexity separately. Official test partitions are
inaccessible until languages and finalists are frozen.

The evaluator accepts only data-only candidate language/program JSON plus
evaluator-managed provenance and parent-language history. It returns scalar
validation accuracy, the frozen stage-one score, separate complexity
components, and structured failures; it does not return labels, predictions,
or a confusion matrix. Each score artifact records an evaluator-source digest.
While this protocol is a draft, the language penalty is unapplied and
`discovery_fitness` is null, so these artifacts cannot drive a preregistered
discovery run.

## Phase 10 language-evolution pilot

Run exactly ten candidate attempts with one solver worker and zero automatic
boundary-repair attempts. Count every proposal, including invalid candidates
and context or evaluator failures; do not replace failed attempts. The pilot
uses the frozen stage-one evaluator and is exploratory feasibility evidence
only. The initial seed evaluation is recorded separately and is not one of the
ten solver proposals. `discovery_fitness` remains null.

Use the existing `llmao_v4` Hydra root with these pilot-only overrides:

```text
application=llmao_v4_language_pilot
optimizer=llmao_v4_language_pilot
evaluation=llmao_v4_language_pilot
loop.max_iterations=10
loop.n_workers_phase2=1
loop.n_parallel_phase2=1
loop.boundary_repair_attempts=0
loop.n_solver_examples_phase2=32
```

The pilot evaluator includes solver examples so it can read the evaluator log
attached to EvE's selected prefill entry. Each valid seed or candidate context
stores `evaluate/lineage_state.json`: the last valid V4 candidate ID, its
language generation and canonical language hash, and the ordered language
snapshots from G0 through that candidate. A later evaluator invocation reads the state from the prefill's
read-only solver example, passes the snapshots to the context builder, and
appends the current language snapshot only after candidate-context validation
succeeds. A context failure carries the inherited valid state forward. The
EvE prefill entry ID is recorded separately; `parent_candidate_id` names the
last valid V4 language ancestor. Candidate files remain exactly
`language.json` and `program.json`.

The pilot passes only if all of these conditions hold:

- at least 8 of 10 candidate attempts receive valid stage-one scores;
- every introduced macro is used by its introducing candidate;
- at least one introduced macro is used by a descendant candidate;
- the language never exceeds eight macros, with at most one new macro per
  candidate, depth 6, 127 expanded nodes, and 128 features;
- zero evaluator, data, label, test-partition, or workspace-boundary violations.

Stop immediately on evidence of a protected-boundary or official-test access
violation. Stop after ten attempts. Retain all invalid, incomplete, and valid
candidate artifacts. A failed gate requires a separately documented plan before
another language pilot.

## Primary fresh-search design

Run the three language conditions `G0`, `GH`, and frozen `G*` with both fixed
iterative Codex and EvE. Each optimizer starts fresh with the same initial
programs, evaluation data, independent seeds, model, reasoning effort,
permissions, context policy, candidate budget, token accounting, and timeout.

The requested backend is GPT-6 Luna (`gpt-6-luna`) with `max` reasoning. The
ChatGPT Plus account, Codex CLI model access, and `max` reasoning support were
verified on 2026-10-14; the launch-preparation usage snapshot at 09:26 UTC
showed 36% used in the five-hour window, 11% in the weekly window, and no paid
credits. The CLI version and EvE commit are recorded in
`results/v4/environment.json`. The pinned account plan is Plus, not Pro. The
LLMAO evaluator/compiler snapshot, worker permissions, and context policy used
for each completed smoke run are pinned in
`results/v4/smoke_manifest.json`. Freeze their final protocol values before
launching the Phase 10 pilot or primary discovery workers.

The primary measure is best-so-far search AUC against candidate evaluations
for `G*` versus `G0` under matched optimizer conditions. Also retain token
curves, time to predeclared frozen thresholds, final fitness, invalid and
duplicate rates, compile/runtime failures, macro reuse, and macro survival.
The optimizer-language interaction and `GH` comparison are secondary.

After language freezing, semantic ablation changes only names and descriptions
while preserving computation, signatures, and parameter ranges. Transfer
restarts representation search on EMNIST Digits, EMNIST Letters, KMNIST, and
Fashion-MNIST using the frozen MNIST language.

## Decisions required before final preregistration

1. LLMAO evaluator/compiler snapshot, worker permissions, and context policy.
   The EvE commit, Codex CLI model identifier, reasoning support, and CLI
   version are recorded in `results/v4/environment.json`.
2. Candidate and token budgets, independent seeds, proposal-attempt cap,
   timeout policy, and rules for incomplete runs.
3. Common initial program manifest. The split parameters and fingerprints are
   recorded in `results/v4/baseline_reproduction/summary.json`. The existing
   twenty V3.2 seed ASTs contain none of the four excluded V3 operations,
   making them eligible for validation as the common starting set.
4. Language-complexity definition and discovery penalty coefficient. The V4
   macro caps are pinned at eight macros per language and one new macro per
   candidate; expansion caps remain depth 6, 127 nodes, and 128 features.
5. Discovery-only language selection rule and deterministic tie breakers.
6. Exact AUC integration bounds and normalization, primary contrast across
   optimizer conditions, paired statistical procedure, and numerical support
   criteria.
All decisions must be recorded before observing the results they govern.
Protocol changes after discovery require a versioned amendment; preserve the
original protocol, digest, and affected traces.
