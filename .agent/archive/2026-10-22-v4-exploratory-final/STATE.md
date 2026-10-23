# Current state

Completed E4, the bounded seed-202 comparison of frozen G0 recipe guidance and
typed G_pilot macros. Both searches terminated at the 20-attempt cap. Neither
search was resumed or launched again after its bounded run.

## Run evidence

- Report: `results/v4/e4/seed_202/REPORT.md`.
- Machine-readable analysis: `results/v4/e4/seed_202/e4_results.json`.
- Raw calls, response archives, traces, metrics, preflight, manifest, and run
  status are preserved in `results/v4/e4/seed_202/`.
- G0 recipes: 20 attempts, 20 typed-valid proposals, one duplicate, 19 scored;
  best adaptive fitness 0.630531 at attempt 7.
- G_pilot macros: 20 attempts, 15 typed-valid proposals, one duplicate, five
  invalid JSON/schema slots, 14 scored; best adaptive fitness 0.395342, below
  the shared initial best 0.490582.
- No raw proposal invoked a G_pilot macro. Neither condition proposed or scored
  a complete frozen recipe subtree. No novel scored composites beyond the
  three standalone E2/E3 ASTs were found by the exact-subtree criterion.
- E1 train-only split fingerprint:
  `41bc42fedd084e7c6f67d995be6cb84d77eb72acc44fca3b31fe3691301b129f`.
  The official test partition remained blocked at the data-access boundary.
- Independent SHA-256 checks match the pre-run manifest for all preserved E1,
  E2, E3, and G_pilot source artifacts.
- The E4 traces report optimizer seed 202 and model request seeds 202 onward.
  A hard-coded context value caused candidate proposal IDs to contain seed 101;
  that field was only used for ID/metadata labeling, not prompt construction or
  model sampling. The adapter now passes the requested seed through. Historical
  E4 logs were left intact and the searches were not rerun.

## Validation

- Focused tests: `.venv/bin/pytest -q tests/optimizer_bench/test_e1.py tests/optimizer_bench/test_e4.py tests/unit/test_mnist_e1.py` — 26 passed.
- Ruff: `.venv/bin/ruff check experiments/e1.py experiments/e4.py src/bias_optimizer/optimizer_bench/e1.py tests/optimizer_bench/test_e1.py tests/optimizer_bench/test_e4.py` — passed.
- Python compilation for `experiments/e1.py` and `experiments/e4.py` — passed.
- E4 preflight passed before the model calls with zero requests; both searches
  completed within attempt, request, and token-reservation limits.
- `graphify update . --no-cluster` completed after the final source edits
  (3,687 nodes, 11,648 edges); review the diff, `git diff --check`, and commit
  explicit E4-owned paths.

## Stop boundary

Do not run more seeds, change frozen macros using E3 fitness, resume the V4
primary campaign, or access official test data. After review and commit, report
the E4 findings and stop.
