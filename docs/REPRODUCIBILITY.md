# Development and historical reproduction

This page retains the original V1/V2 setup and command reference. For an exact
historical implementation, check out the version commit listed in the
[research overview](../README.md#preserved-versions-and-reading-guide) in a separate
checkout. Later versions change the DSL and search behavior; rerunning an older
command on `main` does not reproduce its historical experiment automatically.

Search and evaluation write local artifacts. Preserve existing frozen results
before rerunning commands, and follow the corresponding protocol and manifests.
The V3.1 workflow is specified in [V3_1_PROTOCOL.md](../V3_1_PROTOCOL.md).
The V3/V3.1 architecture and V3.2 execution boundaries are documented in
[ARCHITECTURE_V3_REFERENCE.md](../ARCHITECTURE_V3_REFERENCE.md) and its
[study report](../reports/V3_2_OPTIMIZER_VALUE.md).
The frozen V4 exploratory results and their limits are documented in the
[V4 report](../reports/scientific/V4_EVOLVING_BIAS_LANGUAGE.md). The intended
primary design remains in [ARCHITECTURE.md](../ARCHITECTURE.md),
[`V4_PRIMARY_DESIGN.md`](../V4_PRIMARY_DESIGN.md), and its
[revision-11 amendment](../V4_PRIMARY_DESIGN_V11.md); that primary campaign did
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

The current branch adds a documentation-only clarification after the tag. The
updated manifest records the clarified report and documentation files as
post-tag content; the tag and its original manifest remain unchanged. Protocols,
source code, data, and historical run records were not edited. Do not use the
primary launch commands below this section to resume V4; they remain historical
protocol documentation.

Verify the manifest and bundled artifacts at the current branch revision from
the repository root:

```sh
shasum -a 256 -c reports/scientific/V4_EVIDENCE_MANIFEST.sha256
shasum -a 256 -c reports/scientific/V4_EVIDENCE_FILES.sha256
```

The MNIST source archives are public training inputs and are identified by
their pinned SHA-256 values in the manifest; they are not duplicated in the
release. The official test partition was not used. The report lists the
deterministic local checks run for closure. To inspect the exact original
release files, read them at `v4-exploratory-final` with `git show`. Do not
rerun E1–E4, launch E5, or treat the incomplete primary protocol as
authorization for another search.

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

## Reproduce the experiment

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
[`reports/FINAL_REPORT.md`](../reports/FINAL_REPORT.md).

## V2 typed program search

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
[`PLAN.md`](../PLAN.md) and
[`ARCHITECTURE_V3_REFERENCE.md`](../ARCHITECTURE_V3_REFERENCE.md) for the V2
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
[`reports/V2_PROGRAM_SYNTHESIS.md`](../reports/V2_PROGRAM_SYNTHESIS.md); MAP-Elites
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
- `results/`, `cache/` — local generated artifacts; contents are ignored.

For V4, persistent run outputs, evidence, scratch, and the MNIST dataset cache
belong under `results/v4/`. The evaluator can read the cache; the Codex worker
sandbox must deny it. The pinned EvE checkout remains a separate runtime input.
