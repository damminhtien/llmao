# E3 execution record

**Complete.** The preserved E2 raw responses were replayed against the frozen G_pilot manifest. Three unique macro-expanded ASTs passed E1 compilation and V4 expansion limits. None matched an E1 evaluated AST exactly, and the E1 run artifacts did not persist a complete evaluator configuration or dataset fingerprint, so no score reuse was justified.

The three programs were evaluated under the existing E1 500-example stage-one evaluator using the checksum-verified official-training-only MNIST files and the saved 58,000/2,000 seed-42 split. A loader-boundary guard rejected the historical OpenML and final/test-data paths. The absolute cap of three evaluations was enforced.

Report and records: `results/v4/e3/e2_macro_program_evaluation_2026-10-20/`. No model, optimizer, or official test partition was used. E1 and E2 evidence remains unchanged.
