# Current state

Updated: 2026-10-19

## Completed

- Preserved the prior V4 active task, plan, and state at `.agent/archive/2026-10-19-e1-prep/` before switching the active goal to E1-PREP.
- Confirmed no active V14/V4 runner: `tmux ls` reported no tmux server, and the process scan found no matching runner. The saved V14 seed-1202 `running` checkpoint is historical/interrupted; it was not resumed or changed.
- Added a train-only E1 loader for the two checksum-pinned official MNIST training IDX archives. It does not call the historical OpenML loader, fetch the 70,000-row OpenML dataset, or reference a test partition. It preserves V3.2 stratified `train_test_split` and float32 `/255` preprocessing and verifies a saved manifest.
- Added the E1-specific adapter using the existing V3.2 `LLMIterativeOptimizer`, `ProgramProposer` prompt/schema helpers, evaluator, V4 macro validator, and deterministic macro expander. Both grammars expose only G0 primitives; G_pilot additionally exposes its three frozen macros. Expanded ASTs are compiled and deduplicated by canonical identity.
- Added per-condition caps: 20 proposal attempts; at most 40 Ollama requests; 120 seconds/request; 2,500 output tokens/request; 750,000 conservative reserved tokens/condition (1,500,000 across both). Failed, invalid, and duplicate calls consume the request/attempt reservations. A valid proposal after an invalid/duplicate batch slot retains its actual attempt number.
- The 20 initial G0 programs are scored once by the E1 run entrypoint and passed as the same immutable score tuple to both conditions. A mock regression verifies the single-score/shared-tuple orchestration; no real candidate score was produced during preparation.
- No model generation, E1 search, candidate evaluation, or V4 discovery was launched. The ignored E1 `runs/seed_101` output path remains absent. Preflight only loaded the pinned train partition, checked manifests and constraints, and read local Ollama tags.

## Preflight evidence

Command: `./.venv/bin/python experiments/e1.py --preflight`

Result: `preflight: passed`; seed 101; 20 unique initial programs; V3.2 protocol SHA-256 `db190b013b29fd40605d346f4fe7bbdd989d1d7f3c61e0079d631fff69fd536a`; G0 language SHA-256 `34053b62a917cb7f19b572a4458440972350ea800391fdeba2d3f624cc331b2f`; frozen G_pilot manifest SHA-256 `0b7300a171b9efd25c3c9742cf84de8d1e9b85d23f23573ac8a4a5b3dc2e9e34`; G_pilot language SHA-256 `0736be05cbae240fa99878d77fdf4f0f7233d7e4c2ce3e2bd8d8e03a12d4d1dc`.

Train-only cache path: `results/v4/e1/data/mnist/raw/`. Source archive hashes: train images MD5 `f68b3c2dcbeaaa9fbdd348bbdeb94873`, SHA-256 `440fcabf73cc546fa21475e81ea370265605f56be210a4024d2ca8f203523609`; train labels MD5 `d53e105ee54ea40749a09fcbcd1e9432`, SHA-256 `3552534a0a558bbed6aed32b30c495cca23d567ec52cac8be1a0730e8010255c`. Decompressed IDX SHA-256 values: images `ba891046e6505d7aadcbbe25680a0738ad16aec93bde7f9b65e87a2fc25776db`; labels `65a50cbbf4e906d70832878ad85ccda5333a97f0f4c3dd2ef09a8a9eef7101c5`.

Split: seed 42, stratified 2,000 validation rows from the 60,000-row official training partition; 58,000 train rows and 2,000 validation rows; float32 pixel values divided by 255. Saved manifest SHA-256 `26c3e3f7b8ee8b2eb3169d684fbc4bf7e0c429f38f0e7bd2654278b87cef63f4`; dataset fingerprint `41bc42fedd084e7c6f67d995be6cb84d77eb72acc44fca3b31fe3691301b129f`. Train index/images/labels fingerprints: `6f93fe6e3ec2764671ae2f45a50b8042ff2f7317edce9f7e6b19bb1c26379282`, `15e12d6f269cda485395ddb7b4be01a639175ec830fed60779350ac516f8ca55`, `9d091d988de1b13fb9b2ee60de53671ce232ebb4fbb460f0fc8fd1eae9e865d6`. Validation index/images/labels: `a57e873cd99805aab3cf887c87c9a93b7c244c65226509ec899b6deff8fec5e7`, `a64a8c45f7b3394611d368e042dbc8906cb5858b156faad219edd610dc70a72a`, `d25be9529d09b59c7f2c887b71a06fe22e776dd0a4c2b84b353f358db0bc7c0f`.

Grammar preflight: 23 G0 operations, zero excluded V3 primitives; G_pilot adds exactly `stroke_degree_profile`, `multiscale_spatial_profile`, and `multiscale_spatial_degree_profile` (26 total schema operations). Each frozen macro expands deterministically to permitted G0 operations and passes the existing feature-dimension, depth-6, and 127-node constraints. Macro AST and expanded AST hashes match.

## Validation

- `PYTHONPATH=.:src .venv/bin/pytest -q tests/unit/test_mnist_e1.py tests/optimizer_bench/test_e1.py tests/unit/test_program_search_v3.py tests/unit/test_v4_macros.py tests/unit/test_v4_base_language.py tests/unit/test_v4_candidate.py tests/unit/test_v4_candidate_check.py` — 58 passed.
- `.venv/bin/ruff check src/bias_optimizer/data/mnist_e1.py src/bias_optimizer/optimizer_bench/e1.py experiments/e1.py tests/unit/test_mnist_e1.py tests/optimizer_bench/test_e1.py` — passed.
- `.venv/bin/python -m py_compile src/bias_optimizer/data/mnist_e1.py src/bias_optimizer/optimizer_bench/e1.py experiments/e1.py` — passed.
- `graphify update .` — code-only local extraction completed.
- An initial pytest collection without `PYTHONPATH=.:src` failed because the existing V4 candidate-check test imports `experiments.*`; rerunning with the repository root on `PYTHONPATH` collected and passed all 58 selected tests.

## Current

E1-PREP is implemented and verified. This checkpoint contains the focused E1 source/tests and active E1 task record on `v4-evolving-bias-language`.

## Next

No E1 run is authorized by this preparation task. If separately authorized later, use:

1. `./.venv/bin/python experiments/e1.py --preflight`
2. `./.venv/bin/python experiments/e1.py --run`

## Remaining limitations

- No actual MNIST candidate scores, search curves, or generated proposals exist yet.
- Ollama request token usage must be reported. If absent, E1 stops fail-closed; conservative input/schema/framing/output reservations still include failed requests in the total cap.
- Local model availability was observed during preflight and may change before a later run.
- The preflight verifies both frozen manifest checksums and provenance and checks that the output path is fresh; it does not reserve that path against another process after preflight returns.
