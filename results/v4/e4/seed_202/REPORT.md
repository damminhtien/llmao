# LLMAO E4 — Controlled Abstraction Reuse Experiment

Exploratory, single-seed comparison of three frozen structural behaviors as ordinary G0 recipes versus typed G_pilot macros. Both conditions reused the same 20 E1 initial score records, seed 202, E1 train-only split, guidance policy, evaluator, model configuration, and per-condition caps. No E2/E3 fitness or candidate was supplied to either optimizer. The fixed policy used Qwen `qwen3.5:35b-mlx`, temperature 0.65, at most 20 proposal attempts, 40 requests, 120 seconds per request, 2,500 output tokens per request, and 750,000 reserved tokens per condition.

## Conditions and outcomes

| Condition | Raw proposals | Attempts | Structurally valid | Duplicates | Adaptive scores | Best overall | Best adaptive | Attempt AUC mean (sum/20) | Unique-score AUC, k=0–14 (mean) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| G0 + recipes | 20 | 20 | 20 | 1 | 19 | 0.630531 | 0.630530641490992 | 0.588546 (sum=11.770922) | 7.917764 (mean=0.565555) |
| G_pilot + macros | 15 | 20 | 15 | 1 | 14 | 0.490582 | 0.39534237091501706 | 0.490582 (sum=9.811645) | 6.868152 (mean=0.490582) |

Attempt AUC is the right-endpoint sum of best-so-far fitness after attempts 1–20, divided by 20; unused authorized attempts hold the last best after a graceful cap stop. Unique-score AUC is the trapezoidal area over the shared range `k=0..14`, where `k=0` is the common initial best and `k=1..14` are the first 14 unique adaptive scores in each condition. The table shows the area and area divided by 14. Exact arrays remain in `e4_results.json`.

## Best-so-far trajectories

- **G0 + recipes:** attempt 1–6: 0.490582; attempt 7–20: 0.630531. Unique-score index (`k=0` is the common initial best): k 0–6: 0.490582; k 7–14: 0.630531.
- **G_pilot + macros:** attempt 1–20: 0.490582. Unique-score index (`k=0` is the common initial best): k 0–14: 0.490582.

## Adoption and costs

- **G0 + recipes:** raw exact recipe-subtree proposals `{'multiscale_spatial_degree_profile': 0, 'multiscale_spatial_profile': 0, 'stroke_degree_profile': 0}`; scored exact recipe-subtree use `{'multiscale_spatial_degree_profile': 0, 'multiscale_spatial_profile': 0, 'stroke_degree_profile': 0}`; raw macro proposals `{'multiscale_spatial_degree_profile': 0, 'multiscale_spatial_profile': 0, 'stroke_degree_profile': 0}`; typed-valid macro proposals `{'multiscale_spatial_degree_profile': 0, 'multiscale_spatial_profile': 0, 'stroke_degree_profile': 0}`; scored macro invocations `{'multiscale_spatial_degree_profile': 0, 'multiscale_spatial_profile': 0, 'stroke_degree_profile': 0}`; 0 invalid attempts by status `{}`; 0 structural/constraint rejections; 47187 reported tokens (40402 input, 6785 output) over 9 requests, reserved 487,770/750,000; 154.9s search wall time (146.2s summed request time); mean prompt 15373 bytes (max 16572); 3 schema variants; 0 novel scored composites beyond the three standalone E2/E3 ASTs, requiring a full recipe subtree.
- **G_pilot + macros:** raw exact recipe-subtree proposals `{'multiscale_spatial_degree_profile': 0, 'multiscale_spatial_profile': 0, 'stroke_degree_profile': 0}`; scored exact recipe-subtree use `{'multiscale_spatial_degree_profile': 0, 'multiscale_spatial_profile': 0, 'stroke_degree_profile': 0}`; raw macro proposals `{'multiscale_spatial_degree_profile': 0, 'multiscale_spatial_profile': 0, 'stroke_degree_profile': 0}`; typed-valid macro proposals `{'multiscale_spatial_degree_profile': 0, 'multiscale_spatial_profile': 0, 'stroke_degree_profile': 0}`; scored macro invocations `{'multiscale_spatial_degree_profile': 0, 'multiscale_spatial_profile': 0, 'stroke_degree_profile': 0}`; 5 invalid attempts by status `{'invalid_response_json_or_schema': 5}`; 0 structural/constraint rejections; 47218 reported tokens (38126 input, 9092 output) over 8 requests, reserved 514,367/750,000; 196.2s search wall time (190.1s summed request time); mean prompt 16346 bytes (max 17466); 2 schema variants; 0 novel scored composites beyond the three standalone E2/E3 ASTs, requiring a full recipe subtree.

Both conditions received the same three expanded G0 recipe trees and the same focus-selection policy; mechanism focus remained guidance rather than an eligibility gate. The recipe text and focus policy were fixed, while the E1 iterative prompt naturally summarized each run's own fresh scored candidates. G0 presented ordinary-language labels and G0 compositions. G_pilot presented the macro names and enabled their typed AST operations. Naming, AST syntax availability, and resulting prompt/schema length are the intended packaging differences. The exact-subtree adoption count requires the complete canonical recipe tree to occur under the scored AST; partial use of individual primitives is not counted as recipe adoption.

## Best adaptive candidates

- **G0 + recipes:** candidate `28cf5060ac6727dc5500d7857280ae7bca30b3cfd3a7346f294df25bf249be1e` at proposal attempt 7, fitness 0.630531, accuracy 0.6340, 16 features, measured feature runtime 578.09 ms. Raw proposal provenance and the full expanded AST are stored in `e4_results.json`.
- **G_pilot + macros:** candidate `6865a69e128e3e0177b22855844b71951fd04e59c41705ecf4730bd47930a993` at proposal attempt 20, fitness 0.395342, accuracy 0.3975, 4 features, measured feature runtime 239.31 ms. Raw proposal provenance and the full expanded AST are stored in `e4_results.json`.

## Interpretation and limits

This one-seed run describes adoption and search behavior under these fixed prompts. Any score difference is not a general causal estimate: the conditions differ in operation names, AST syntax, schema vocabulary, and prompt length. Fitness includes measured runtime, which varies with local execution and cache state. It does not establish transfer or cross-task generalization.

Seed provenance audit: each run trace, optimizer instance, and model request sequence used seed 202 (requests began 202, 203, and so on). A leftover constant stamped proposal IDs as `llm_iterative:101:<attempt>` through the optimizer context. This value only labels proposal IDs/metadata in the iterative optimizer and did not enter the prompt or model sampling seed; the adapter now propagates the requested seed. The completed searches were not rerun.

Data: split fingerprint `41bc42fedd084e7c6f67d995be6cb84d77eb72acc44fca3b31fe3691301b129f`; train-only manifest SHA-256 `26c3e3f7b8ee8b2eb3169d684fbc4bf7e0c429f38f0e7bd2654278b87cef63f4`. The official test partition was blocked at the data-access boundary.

Both conditions terminated within their frozen caps; no additional seed or search was run.
