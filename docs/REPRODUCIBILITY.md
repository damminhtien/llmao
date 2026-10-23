# Development and historical reproduction

This page retains the original V1/V2 setup and command reference. For an exact
historical implementation, check out the version commit listed in the
[research overview](../README.md#preserved-versions-and-reading-guide) in a separate
checkout. Later versions change the DSL and search behavior; rerunning an older
command on `main` does not reproduce its historical experiment automatically.

Search and evaluation write local artifacts. Preserve existing frozen results
before rerunning commands, and follow the corresponding protocol and manifests.
The V3.1 workflow is specified in [V3_1_PROTOCOL.md](v3.1/V3_1_PROTOCOL.md).
The V3/V3.1 architecture and V3.2 execution boundaries are documented in
[ARCHITECTURE_V3_REFERENCE.md](v3/ARCHITECTURE_V3_REFERENCE.md) and its
[study report](../reports/v3.2/V3_2_OPTIMIZER_VALUE_FULL.md).
The frozen V4 exploratory results and their limits are documented in the
[V4 report](../reports/v4/V4_EVOLVING_BIAS_LANGUAGE.md). The intended
primary design remains in [ARCHITECTURE.md](../ARCHITECTURE.md),
[`docs/v4/V4_PRIMARY_DESIGN.md`](../docs/v4/V4_PRIMARY_DESIGN.md), and its
[revision-11 amendment](../docs/v4/V4_PRIMARY_DESIGN_V11.md); that primary campaign did
not complete. V4 is the study name; IDs such as `v4-primary-14` identify
revisions of its primary protocol.
V4 output roots, external read-only inputs, and the fixture scratch policy are
specified in [V4_ARTIFACT_STORAGE_ARCHITECTURE.md](V4_ARTIFACT_STORAGE_ARCHITECTURE.md).

## Frozen V4 exploratory release

The annotated tag `v4-exploratory-final` is the immutable V4 closure snapshot.
It contains the report, evidence manifest, SHA-256 checksums, preserved E1–E4
artifacts, and primary-protocol revisions through `v4-primary-14`. Revision 14
contains two incomplete discovery trajectories; there is no completed `G*`
selection or fresh-search campaign.

Current documentation adds the trajectory spotlight, E1–E4 synthesis, and
[integration handoff](V4_MERGE_READINESS.md) after the tag. The updated manifest
identifies post-tag documents; the tag and its original manifest remain
unchanged. The editorial revisions preserve scientific protocol contents, data, and
historical run records. A subsequent layout cleanup moves 25 root artifacts
without changing their bytes and adapts current source/test path references.
See the [V4 location guide](v4/README.md) for original-to-current paths and
a deterministic relocation audit. Historical source pins require the original
tag checkout. The V4 launch procedures in the protocol and agent
workflow remain historical execution documentation; they do not authorize
resuming this frozen study.

Verify the manifest and bundled artifacts at the current branch revision from
the repository root:

```sh
shasum -a 256 -c reports/v4/evidence/V4_EVIDENCE_MANIFEST.sha256
shasum -a 256 -c reports/v4/evidence/V4_EVIDENCE_FILES.sha256
```

The included trajectory JSONL files and state snapshots support independent
inspection of recorded scores, macro inventories, failure counts, and incomplete
run status. They do not contain a complete replay bundle for every candidate.
Seed 1101's 793 MB final manifest is hash-recorded as a local exclusion; seed
1202 has no final manifest. The tag omits the full native worker workspaces and
runtime caches. These exclusions limit replay beyond the preserved records.

The MNIST source archives are public training inputs and are identified by
their pinned SHA-256 values in the manifest; they are not duplicated in the
release. The official test partition was not used. The report lists the
deterministic local checks run for closure. To inspect the exact original
release files, read them at `v4-exploratory-final` with `git show`. Do not
rerun E1–E4, launch E5, or treat the incomplete primary protocol as
authorization for another search.

The existing focused V4 checks use mocked proposal clients and synthetic
fixtures. They passed 208 tests at closure and again during integration
preparation on 2026-10-23. The following command performs local software
verification without launching a research run:

```sh
.venv/bin/pytest --import-mode=importlib -q \
  tests/optimizer_bench/test_e1.py \
  tests/optimizer_bench/test_e2_macro_adoption_probe.py \
  tests/optimizer_bench/test_e4.py \
  tests/unit/test_mnist_e1.py tests/unit/test_v4_*.py
```

Passing these checks does not resolve the documented E1 final-slot defect or
establish scientific efficacy. See the report's correctness section and the
integration handoff for the validation boundary.

## Development setup

Requires Python 3.14.

```sh
python3.14 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev,plots]'
```

Run the integrated test suite with `python -m pytest --import-mode=importlib`.
The import mode allows the evaluation and optimizer suites to retain their
historical test filenames without module-name collisions.

## Historical V1 experiment

The proposer uses the local Ollama model `qwen3.5:35b-mlx`. Start Ollama and
install that model if it is not already available, then run the search and
freeze its finalists before any test-set evaluation:

```sh
# If needed, install the local model first:
ollama pull qwen3.5:35b-mlx
export OLLAMA_MODEL=qwen3.5:35b-mlx
python experiments/search_mnist.py --generations 10 --candidates-per-generation 8
python experiments/select_finalists.py
python experiments/final_evaluation.py
python experiments/plot_results.py
```

Final evaluation verifies that the search archive still matches the frozen
selection checksum. Run it before extending the search. Generated JSON/JSONL,
feature-cache, and PNG files are written under `results/` and `cache/`; Git
ignores these local artifacts. The final analysis is in
[`reports/v1/FINAL_REPORT.md`](../reports/v1/FINAL_REPORT.md).

## Historical V2 typed program search

V2 adds a typed expression DSL, static validation, a raw-pixel-free discovery
track, and a MAP-Elites archive. It keeps the V1 run as a separate baseline and
uses the same fixed learner and train/validation split.

```sh
export OLLAMA_MODEL=qwen3.5:35b-mlx
python experiments/search_programs.py --track discovery
python experiments/search_programs.py --track augmentation
```

The defaults evaluate 20 deterministic seed programs, then request 18 proposals
for each of 10 generations, using batches of at most four ASTs and up to 36
refill batches per generation. Discovery rejects raw pixels and caps the feature
width at 128; augmentation allows raw pixels and uses a 1,024-feature cap. Each
track has its own candidate and LLM-response JSONL archives. See
[`docs/v3/PLAN.md`](v3/PLAN.md) and
[`docs/v3/ARCHITECTURE_V3_REFERENCE.md`](v3/ARCHITECTURE_V3_REFERENCE.md) for the V2
scope and post-search evaluation protocol.

After both search tracks finish, freeze the raw-free discovery finalists before
loading external test partitions. The follow-on commands evaluate transfer,
sequence counterfactuals, LLM-proposed invariances, orbit pooling, and the
bounded shared-subexpression cache:

```sh
python experiments/freeze_transfer_candidates.py
python experiments/evaluate_pixel_augmentations.py
python experiments/evaluate_transfer.py
python experiments/evaluate_counterfactuals.py
python experiments/search_invariances.py
python experiments/profile_subexpression_cache.py
python experiments/summarize_v2.py
```

Transfer uses EMNIST Digits/Letters and KMNIST as handwriting domains, with
Fashion-MNIST as a negative control. It reports the exact sampled test protocol
and source checksums. The completed V2 run and its limits are summarized in
[`reports/v2/V2_PROGRAM_SYNTHESIS_FULL.md`](../reports/v2/V2_PROGRAM_SYNTHESIS_FULL.md); MAP-Elites
left several niches empty, sequence shuffles did not change finalist predictions,
and Fashion-MNIST transfer prevents a handwriting-specific claim.

## Project layout

- `src/bias_optimizer/domain/` — immutable experiment and search data models.
- `src/bias_optimizer/dsl/` — typed V2 representation AST, validator, compiler, and seed grammar.
- `src/bias_optimizer/novelty/` — structural novelty descriptors and MAP-Elites archive.
- `src/bias_optimizer/features/` — approved feature operators and pipelines.
- `src/bias_optimizer/compiler/` — compile declarative biases into pipelines.
- `src/bias_optimizer/ml/` — fixed learner and deterministic evaluator.
- `src/bias_optimizer/llm/` — provider-neutral proposal boundary.
- `src/bias_optimizer/search/` — V1 controller and V2 program-search engine.
- `src/bias_optimizer/data/` — reproducible MNIST splits and transfer loaders.
- `src/bias_optimizer/invariance/` — bounded transformation programs and orbit pooling.
- `src/bias_optimizer/cache/` — feature and cross-candidate subexpression caches.
- `experiments/` — baseline, search, finalist, evaluation, and plot entry points.
- `reports/` — tracked research conclusions.
- `tests/` — unit and integration tests.
- `results/`, `cache/` — local generated outputs, ignored by default; selected
  frozen evidence is tracked explicitly, including the V4 manifest inventory.

For V4, persistent run outputs, evidence, scratch, and the MNIST dataset cache
belong under `results/v4/`. The evaluator can read the cache; the Codex worker
sandbox must deny it. The pinned EvE checkout remains a separate runtime input.
