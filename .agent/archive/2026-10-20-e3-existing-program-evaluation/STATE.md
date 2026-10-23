# Current state

Updated: 2026-10-19

## Status

E2 macro-adoption capability probe is complete. Stop here; do not run E1 again,
start an optimization search, or issue further model requests.

## Completed

- Added a thin no-score entrypoint at `experiments/e2_macro_adoption_probe.py`.
  It calls the existing E1 budgeted Ollama client directly, not the E1 proposer
  repair loop, evaluator, or MNIST loader.
- Added mock coverage at `tests/optimizer_bench/test_e2_macro_adoption_probe.py`.
- Verified the frozen G_pilot manifest and all three macro signatures. The
  manifest SHA-256 remains
  `0b7300a171b9efd25c3c9742cf84de8d1e9b85d23f23573ac8a4a5b3dc2e9e34`.
- Preflight confirmed local `qwen3.5:35b-mlx`, six fixed request seeds 21001 to
  21006, `free_exploration` focus, 120 second timeout, 2,500 output-token cap,
  and 324,586 conservatively reserved tokens under the 400,000 total cap.
- Issued exactly six requests. All six raw ASTs invoked their requested macro;
  all passed the E1 typed proposal parser, structural validator, and canonical
  macro expansion. Each pair produced one unique expanded AST, so the second
  response for each macro was a duplicate.
- No candidate scores were requested, no MNIST data was loaded, and the
  official test partition was not accessed.
- Archived the prior E1-PREP task, plan, and state at
  `.agent/archive/2026-10-19-e2-macro-capability/` before changing the active
  task record.

## E2 results

| Macro | Raw invokes | Structurally valid invokes | Expansion successes | Distinct expanded ASTs | Failure category |
|---|---:|---:|---:|---:|---|
| `stroke_degree_profile` | 2/2 | 2/2 | 2/2 | 1 | 1 duplicate |
| `multiscale_spatial_profile` | 2/2 | 2/2 | 2/2 | 1 | 1 duplicate |
| `multiscale_spatial_degree_profile` | 2/2 | 2/2 | 2/2 | 1 | 1 duplicate |

Reported usage: 10,636 input tokens, 648 output tokens, 28.306 seconds total
request time. No request failed or exceeded a cap.

Output root: `results/v4/e2/macro_adoption_probe_2026-10-19/`. The raw
`model_calls.jsonl`, request plan, validation rows, and summary are mode 0444.
Raw call archive SHA-256:
`fe94dcf6b9d14499bf4abd038a189ab9919466479dfe5331ea54b2fb23ecfbd8`.

## Validation

- `.venv/bin/pytest tests/optimizer_bench/test_e1.py tests/optimizer_bench/test_e2_macro_adoption_probe.py -q` — 20 passed.
- `.venv/bin/ruff check experiments/e2_macro_adoption_probe.py tests/optimizer_bench/test_e2_macro_adoption_probe.py` — passed.
- `.venv/bin/ruff format --check experiments/e2_macro_adoption_probe.py tests/optimizer_bench/test_e2_macro_adoption_probe.py` — passed.
- `.venv/bin/python experiments/e2_macro_adoption_probe.py --preflight-only` — passed without generating a model response.
- `graphify update . --no-cluster` — code-only refresh completed; no LLM calls.
- `git diff --check` — passed.

## Conclusion and stop condition

Direct instruction demonstrates that Qwen can construct structurally valid
programs using all three frozen abstractions. The E1 absence is therefore more
consistent with open-ended generation preference than inability to compose the
macros; this probe does not establish broader search utility. A matched,
no-score prompt ablation could test that preference, but it is not part of this
completed task and must not be launched automatically.
