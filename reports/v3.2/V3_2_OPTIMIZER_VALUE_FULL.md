# V3.2 Optimizer Value Study

## 1. Research question

> Does an LLM provide measurable value as an optimizer over structured inductive-bias program spaces, beyond conventional search methods?

V3.2 compares search quality over the frozen V3 typed program space. Candidate search quality is distinct from the final representation quality assessed after search.

## 2. Why V3.2 followed V3 and V3.1

V3 established a structured program space and selected candidate programs. V3.1 froze and evaluated those candidates across representation dimensions such as linear and nonlinear probes, HOG complementarity, and robustness. Those results answer whether the selected representations are useful; they do not isolate whether the LLM search procedure was better than conventional optimizers. V3.2 holds the V3 space and stage-one objective fixed to measure that optimizer contribution.

## 3. Frozen search space and objective

- V3 typed DSL primitives and validator; maximum dimension 128, depth 6, and 127 AST nodes.
- Raw-pixel features were prohibited, consistent with the V3 discovery track.
- The exact V3 stage-one objective was reused unchanged: `accuracy_500 - 0.001*log1p(feature_dim) - 0.0001*log1p(runtime_ms)`, where runtime is the V3 sum of feature, training, and inference runtime.
- Each candidate was evaluated on the same 500-example training subset and fixed MNIST validation partition with the same learner. The official test split was not accessed during optimizer search.
- V3.1 HOG-complementarity, robustness, transfer, and multi-probe metrics were excluded from primary fitness.

## 4. Optimizers

| Optimizer | Search method |
|---|---|
| `typed_random` | Type-directed AST sampling with frozen depth, primitive, and parameter sampling rules. |
| `genetic_programming` | Typed subtree mutation/crossover, tournament size 3, elitism 2, and a 0.5/0.5 crossover-or-mutation choice. |
| `llm_one_shot` | Frozen local Qwen model and V3 proposal interface; receives DSL/task/constraints and seed examples but no evaluation scores or adaptive history. |
| `llm_iterative` | Same local Qwen model and V3 iterative proposal logic; receives the bounded V3 evidence format and no V3.1 characterization. |

## 5. Equal-budget protocol

The frozen protocol declares 20 shared V3 seed programs and 180 new evaluations per run, for 200 unique valid evaluated candidates, with protocol seeds `[101, 202, 303, 404, 505]`. The matched execution used seeds `[101, 202]`. The proposal cap was 540 attempts per run. Invalid ASTs and duplicates did not consume evaluation budget; all were counted as overhead. Runs stopping before 200 are marked incomplete, with no increase to the cap. The protocol SHA-256 is `db190b013b29fd40605d346f4fe7bbdd989d1d7f3c61e0079d631fff69fd536a`.
Runtime fallback: local qwen3.5:35b-mlx proposal throughput made the full five-seed execution prohibitive. The primary analysis is restricted to the matched seed subset shown above. Of the 12 excluded optimizer-seed cells, 6 extra runs were retained outside the matched analysis and 6 runs were not started. Their per-cell statuses are in `results/v32/manifest.json`.

Full-budget primary runs: 6/8. Among conditions with at least one complete run, mean best-fitness ordering was `llm_iterative > genetic_programming > llm_one_shot`; it is descriptive and does not by itself establish a reliable difference.
No condition-level 200-candidate estimate is available for: `typed_random`. Incomplete runs are retained as censored observations and are not counted as full-budget threshold failures.

## 6. Primary search curves

The line and shaded min-to-max range are shown only through the longest candidate count reached by every run included for that optimizer; the range is not a confidence interval. This prevents the plotted mean from changing its run composition at the censoring boundary. Incomplete runs are marked at their last observed score in panel C.

![V3.2 best-so-far search curves and optimizer diagnostics](figures/V3_2_SEARCH_CURVES.png)

## 7. Final best-fitness results

### Final best fitness

| Optimizer | Complete runs | Best fitness @200 (mean; median; SD; min–max) | Per-seed best or last observed |
|---|---:|---:|---|
| `genetic_programming` | 2/2 | 0.8557 (median 0.8557; SD 0.0027; range 0.8538–0.8576) | 101: @200 0.8538; 202: @200 0.8576 |
| `llm_iterative` | 2/2 | 0.8587 (median 0.8587; SD 0.0005; range 0.8583–0.8590) | 101: @200 0.8590; 202: @200 0.8583 |
| `llm_one_shot` | 2/2 | 0.8306 (median 0.8306; SD 0.0171; range 0.8185–0.8427) | 101: @200 0.8185; 202: @200 0.8427 |
| `typed_random` | 0/2 | not available | 101: incomplete @ 184 (0.8048); 202: incomplete @ 183 (0.8312) |

### Search-curve AUC and top-five mean

| Optimizer | AUC (mean; SD) | Top-five mean fitness (mean; SD) |
|---|---:|---:|
| `genetic_programming` | 138.4776 (median 138.4776; SD 1.6376; range 137.3197–139.6355) | 0.8550 (median 0.8550; SD 0.0037; range 0.8524–0.8576) |
| `llm_iterative` | 151.5228 (median 151.5228; SD 0.5828; range 151.1107–151.9349) | 0.8407 (median 0.8407; SD 0.0002; range 0.8406–0.8408) |
| `llm_one_shot` | 138.8643 (median 138.8643; SD 7.0896; range 133.8512–143.8774) | 0.7810 (median 0.7810; SD 0.0302; range 0.7596–0.8023) |
| `typed_random` | not available | not available |

## 8. Evaluations-to-threshold

The thresholds were computed from the protected V2/V3 artifacts and frozen before the benchmark. Hit probability uses complete 200-candidate runs. Panel B shows complete-run means as bars and observed hits from incomplete runs as black × marks; the table records incomplete hits and non-hits at their last observed evaluation.

For complete runs, `not reached` means no threshold hit by evaluation 200. The complete-run probability is the observed fraction of complete matched runs that reached the threshold. Incomplete-run observations are reported separately as censored hits or non-hits by the last observed evaluation.

| Optimizer | Threshold | Reached within 200 / complete runs | Evaluations among complete runs that reached | Incomplete-run evidence (censored) |
|---|---|---:|---:|---|
| `genetic_programming` | `v2_best` | 2/2 (100%) | 74.5 (median 74.5; SD 7.8; range 69.0–80.0) | — |
| `genetic_programming` | `v3_frozen_finalist_floor` | 1/2 (50%) | 157.0 (median 157.0; SD 0.0; range 157.0–157.0) | — |
| `genetic_programming` | `v3_top_20_cutoff` | 2/2 (100%) | 32.5 (median 32.5; SD 3.5; range 30.0–35.0) | — |
| `llm_iterative` | `v2_best` | 2/2 (100%) | 28.0 (median 28.0; SD 1.4; range 27.0–29.0) | — |
| `llm_iterative` | `v3_frozen_finalist_floor` | 2/2 (100%) | 38.5 (median 38.5; SD 13.4; range 29.0–48.0) | — |
| `llm_iterative` | `v3_top_20_cutoff` | 2/2 (100%) | 28.0 (median 28.0; SD 1.4; range 27.0–29.0) | — |
| `llm_one_shot` | `v2_best` | 2/2 (100%) | 68.0 (median 68.0; SD 38.2; range 41.0–95.0) | — |
| `llm_one_shot` | `v3_frozen_finalist_floor` | 0/2 (0%) | not reached | — |
| `llm_one_shot` | `v3_top_20_cutoff` | 2/2 (100%) | 33.0 (median 33.0; SD 11.3; range 25.0–41.0) | — |
| `typed_random` | `v2_best` | 0/0 (not estimable) | not estimable | 101: hit @ 38; 202: hit @ 37 |
| `typed_random` | `v3_frozen_finalist_floor` | 0/0 (not estimable) | not estimable | 101: no hit by 184; 202: no hit by 183 |
| `typed_random` | `v3_top_20_cutoff` | 0/0 (not estimable) | not estimable | 101: hit @ 22; 202: hit @ 26 |

## 9. Validity, duplicates, and cost

| Optimizer | Attempts | Valid proposals | Valid rate | Invalid | Duplicates | Duplicate rate | Constraint rejects | LLM calls | LLM tokens | Proposal min/run | Evaluation min/run | Total min/run |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `genetic_programming` | 447.0 | 435.0 | 97.6% | 0.0 | 255.0 | 56.1% | 12.0 | 0.0 | 0 | 0.00 | 1.65 | 1.67 |
| `llm_iterative` | 323.5 | 312.0 | 96.4% | 11.5 | 112.0 | 34.6% | 20.0 | 132.0 | 1214781 | 48.83 | 1.07 | 49.93 |
| `llm_one_shot` | 251.0 | 247.0 | 98.5% | 4.0 | 52.0 | 20.6% | 15.0 | 97.5 | 244197 | 19.91 | 0.96 | 20.90 |
| `typed_random` | 540.0 | 425.0 | 78.7% | 0.0 | 261.5 | 48.4% | 115.0 | 0.0 | 0 | 0.00 | 1.00 | 1.02 |

Proposal time is separated from oracle evaluation time. Wall time includes both plus runner overhead. This table uses all attempted runs, including incomplete runs, and reports their actual per-run cost. LLM tokens are zero for non-LLM methods and are not an evaluator cost.

## 10. Diversity and novelty

The required figure reports five-axis descriptor-cell coverage. The table summarizes complete 200-candidate runs only; incomplete runs are shown as last-observed crosses in the figure and remain available in the raw per-run summary. Structural novelty is the V3 normalized tree-distance score recorded against previously evaluated ASTs. Behavioral novelty is computed post-search from fixed validation probes and is reported below with winner characterization. Novelty is descriptive and is not treated as optimizer quality by itself.

| Optimizer | Descriptor cells (mean; SD) | Structural novelty (mean; SD) | Feature dimension (mean; SD) | AST depth (mean; SD) | AST nodes (mean; SD) |
|---|---:|---:|---:|---:|---:|
| `genetic_programming` | 17.0000 (median 17.0000; SD 4.2426; range 14.0000–20.0000) | 0.1824 (median 0.1824; SD 0.0148; range 0.1719–0.1929) | 14.5400 (median 14.5400; SD 2.8496; range 12.5250–16.5550) | 5.0625 (median 5.0625; SD 0.2581; range 4.8800–5.2450) | 7.7375 (median 7.7375; SD 2.0754; range 6.2700–9.2050) |
| `llm_iterative` | 20.5000 (median 20.5000; SD 2.1213; range 19.0000–22.0000) | 0.1759 (median 0.1759; SD 0.0054; range 0.1721–0.1797) | 37.4675 (median 37.4675; SD 1.2056; range 36.6150–38.3200) | 5.1800 (median 5.1800; SD 0.0071; range 5.1750–5.1850) | 8.1575 (median 8.1575; SD 0.3712; range 7.8950–8.4200) |
| `llm_one_shot` | 21.0000 (median 21.0000; SD 0.0000; range 21.0000–21.0000) | 0.1627 (median 0.1627; SD 0.0349; range 0.1380–0.1873) | 34.6700 (median 34.6700; SD 1.0112; range 33.9550–35.3850) | 5.1025 (median 5.1025; SD 0.0389; range 5.0750–5.1300) | 8.0750 (median 8.0750; SD 0.1061; range 8.0000–8.1500) |
| `typed_random` | not available | not available | not available | not available | not available |

## 11. One-shot versus iterative LLM

Paired bootstrap comparisons use matching optimizer-seed indices. There are at most 2 pairs, so intervals and win counts are descriptive; no normal-theory t-test is used.

| Paired comparison | Metric | Mean difference (first optimizer minus second) | Paired bootstrap 95% interval | Seed wins / paired runs |
|---|---|---:|---:|---:|
| `genetic_programming_vs_llm_iterative` | `final_best_fitness` | -0.0029 | [-0.0052, -0.0007] | 0/2 metric wins |
| `genetic_programming_vs_llm_iterative` | `search_curve_auc` | -13.0452 | [-14.6153, -11.4752] | 0/2 metric wins |
| `genetic_programming_vs_llm_iterative` | `top_5_mean_fitness` | +0.0143 | [+0.0118, +0.0167] | 2/2 metric wins |
| `genetic_programming_vs_llm_one_shot` | `final_best_fitness` | +0.0251 | [+0.0149, +0.0353] | 2/2 metric wins |
| `genetic_programming_vs_llm_one_shot` | `search_curve_auc` | -0.3867 | [-6.5577, +5.7844] | 1/2 metric wins |
| `genetic_programming_vs_llm_one_shot` | `top_5_mean_fitness` | +0.0740 | [+0.0553, +0.0928] | 2/2 metric wins |
| `genetic_programming_vs_typed_random` | `final_best_fitness` | not available | not available | not estimable metric wins |
| `genetic_programming_vs_typed_random` | `search_curve_auc` | not available | not available | not estimable metric wins |
| `genetic_programming_vs_typed_random` | `top_5_mean_fitness` | not available | not available | not estimable metric wins |
| `llm_iterative_vs_llm_one_shot` | `final_best_fitness` | +0.0280 | [+0.0156, +0.0405] | 2/2 metric wins |
| `llm_iterative_vs_llm_one_shot` | `search_curve_auc` | +12.6585 | [+8.0575, +17.2595] | 2/2 metric wins |
| `llm_iterative_vs_llm_one_shot` | `top_5_mean_fitness` | +0.0598 | [+0.0385, +0.0810] | 2/2 metric wins |
| `llm_iterative_vs_typed_random` | `final_best_fitness` | not available | not available | not estimable metric wins |
| `llm_iterative_vs_typed_random` | `search_curve_auc` | not available | not available | not estimable metric wins |
| `llm_iterative_vs_typed_random` | `top_5_mean_fitness` | not available | not available | not estimable metric wins |
| `llm_one_shot_vs_typed_random` | `final_best_fitness` | not available | not available | not estimable metric wins |
| `llm_one_shot_vs_typed_random` | `search_curve_auc` | not available | not available | not estimable metric wins |
| `llm_one_shot_vs_typed_random` | `top_5_mean_fitness` | not available | not available | not estimable metric wins |

## 12. Random versus GP versus LLM

All four conditions were assigned the same unique-candidate budget. Runs that stopped at the hard attempt cap are reported as incomplete; their last observed score is not treated as a 200-candidate result. Full-budget pairwise estimates use only paired seeds for which both optimizers completed. The observed order should also be interpreted with the small run count and proposal cost in view.

Interpretation matrix:

| Observed pattern | Interpretation |
|---|---|
| Iterative LLM > GP > random | Semantic prior plus feedback appears useful for search efficiency. |
| GP ≈ iterative LLM > random | Structured adaptive search matters, with little added LLM value. |
| One-shot LLM ≈ iterative LLM > GP/random | Pretrained semantic prior helps; feedback adds little. |
| Iterative LLM > one-shot LLM but ≈ GP | Feedback matters, without a unique LLM advantage. |
| Random ≈ GP ≈ LLM | The space may be easy or the LLM may be unnecessary. |
| Random > LLM | The LLM prior may favor familiar but suboptimal regions. |

## 13. Semantic ablation

This secondary lexical-semantic ablation preserves operator signatures, types, parameter constraints, and mathematical behavior. It does not remove all pretrained knowledge.

| Condition | Final fitness (mean; median; SD; range) | Complete runs | Per-seed outcome | Mean calls / tokens / minutes |
|---|---:|---:|---|---:|
| `semantic_dsl` | 0.8585 (median 0.8581; SD 0.0007; range 0.8580–0.8593) | 3/3 | 101: @200 0.8580; 202: @200 0.8581; 303: @200 0.8593 | 131.0 calls / 1196221.3 tokens / 47.9 min |
| `anonymized_dsl` | 0.6129 (median 0.6306; SD 0.0354; range 0.5722–0.6359) | 3/3 | 101: @200 0.6359; 202: @200 0.5722; 303: @200 0.6306 | 177.7 calls / 2169195.3 tokens / 65.8 min |

Paired semantic-minus-anonymized mean difference: `+0.2456`; paired bootstrap interval [+0.2221, +0.2859]; 3/3 seed wins.

Interrupted proposal attempts are shown for cost transparency only. They produced no saved candidate trace and are excluded from fitness estimates and paired comparisons.

| Condition | Seed | Status | Response records | Requested slots | Distinct ASTs in audit | LLM tokens |
|---|---:|---|---:|---:|---:|---:|
| `semantic_dsl` | 303 | `interrupted_without_trace` | 144 | 303 | 177 | 888499 |
| `semantic_dsl` | 303 | `interrupted_before_trace` | 64 | 161 | — | 473034 |

## 14. V3.1 characterization of optimizer winners

Each representative was frozen as the highest-primary-fitness winner among the per-run winners included in the matched analysis. Under the runtime fallback, this applies the predeclared rule to the executed matched-seed subset. If the selected run was incomplete, its winner is the best observed candidate at its stopping point, not a 200-evaluation result. Characterization outputs were not fed back into search.
The robustness panel used a predeclared sample of the MNIST official test set only after optimizer search and winner freeze; it was post-search characterization and did not affect search or selection.

| Optimizer | Winner seed | Search run | Primary fitness | Linear accuracy | RBF accuracy | HOG complementarity (linear) | Dimension | Robustness test |
|---|---:|---|---:|---:|---:|---:|---:|---|
| `genetic_programming` | 202 | complete @200 | 0.8576 | 0.8602 ± 0.0068 | 0.8647 ± 0.0076 | +0.0107 | 24 | translate_x_+2: +0.0003 |
| `llm_iterative` | 101 | complete @200 | 0.8590 | 0.8603 ± 0.0060 | 0.8652 ± 0.0091 | +0.0107 | 30 | translate_x_+2: +0.0003 |
| `llm_one_shot` | 202 | complete @200 | 0.8427 | 0.8480 ± 0.0041 | 0.8575 ± 0.0052 | +0.0087 | 24 | translate_x_+2: +0.0000 |
| `typed_random` | 202 | incomplete @ 183 | 0.8312 | 0.8490 ± 0.0053 | 0.8665 ± 0.0053 | +0.0075 | 36 | translate_x_+2: +0.0955 |

Candidate behavioral novelty was computed after primary search from pairwise feature-distance profiles on a fixed 128-image MNIST validation probe set; labels were not read.

| Optimizer | Mean behavioral novelty | Mean structural novelty | Mean descriptor cells |
|---|---:|---:|---:|
| `genetic_programming` | 0.1201 | 0.1558 | 17.0 |
| `llm_iterative` | 0.1599 | 0.1486 | 20.5 |
| `llm_one_shot` | 0.2159 | 0.1339 | 21.0 |
| `typed_random` | 0.2371 | 0.1679 | 25.0 |

## 15. Threats to validity

- The matched primary analysis uses 2 seed(s) per optimizer because of the recorded runtime fallback; paired bootstrap intervals are highly uncertain at this sample size.
- Wall-clock cost depends on local model and hardware state. The candidate-evaluation budget is the primary fairness unit.
- The fixed 500-example evaluator is a search proxy; V3.1 characterization addresses only preselected dimensions and winners.
- Random sampling, GP operators, and prompt behavior each encode design choices even though their settings were frozen before outcomes.
- Semantic anonymization removes lexical operator cues only as far as the preserved DSL contract allows; it does not erase all pretrained knowledge.
- The study covers this V3 program space and task, not optimizers or domains in general.

## 16. What the LLM actually contributed

The empirical contribution is the observed difference, if any, between one-shot and feedback-guided LLM search, plus their paired differences from typed GP and typed random search. The score, overhead, and characterization tables report those outcomes directly. A negative or near-zero result is a valid answer and does not indicate a failed study.

| Hypothesis | Observed evidence |
|---|---|
| H1 — search efficiency | The full-budget comparison is not estimable: typed random had 0/2 complete runs. In censored traces, random hit the V3 top-20 cutoff at seed 101 at 22, seed 202 at 26 and V2-best at seed 101 at 38, seed 202 at 37; iterative LLM's complete runs hit the top-20 cutoff in 28.0 (median 28.0; SD 1.4; range 27.0–29.0) and V2-best in 28.0 (median 28.0; SD 1.4; range 27.0–29.0). The finalist floor was reached by iterative LLM in 2/2 runs (38.5 (median 38.5; SD 13.4; range 29.0–48.0)); random did not reach it before stopping (seed 101 not by 184, seed 202 not by 183). Thus observed efficiency depends on threshold stringency; censored results do not supply a full-budget random estimate. |
| H2 — value beyond GP | Iterative minus GP: mean paired @200 fitness difference +0.0029, bootstrap 95% interval [+0.0007, +0.0052], iterative wins in 2/2 paired seeds. |
| H3 — evaluator feedback | Iterative minus one-shot LLM: mean paired @200 fitness difference +0.0280, bootstrap 95% interval [+0.0156, +0.0405], iterative wins in 2/2 paired seeds. |
| H4 — semantic prior (secondary) | Semantic minus anonymized iterative search: mean paired final-fitness difference +0.2456, bootstrap 95% interval [+0.2221, +0.2859], 3/3 semantic-condition wins. |
| H5 — scientific usefulness | V3.1 post-search characterization was completed for 4/4 preselected optimizer representatives. See linear/RBF accuracy, HOG complementarity, dimension, and robustness results in Section 14; these metrics did not affect search or winner selection. |

## 17. Claim boundary

The strongest allowed claim, if iterative LLM search consistently wins, is: **Under the frozen V3 typed program space and equal candidate-evaluation budget, iterative LLM-guided search reaches high-performing regions more efficiently than the tested random and genetic-programming baselines.**

This result does not establish that LLMs are generally superior optimizers, that the LLM invented new inductive biases, or that the LLM performed scientific discovery.

Protocol: `results/v32/protocol.json` (`db190b013b29fd40605d346f4fe7bbdd989d1d7f3c61e0079d631fff69fd536a`). Primary summary: `results/v32/summary/primary_summary.json`.
