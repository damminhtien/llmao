# LLMAO E3 — Existing Macro-Bearing Program Evaluation

Completed a bounded descriptive evaluation of the three distinct E2 expanded programs. No LLM or optimizer ran. The evaluation path was restricted to the checksum-pinned official MNIST training archives and the saved E1 train/validation split; official test data was not accessed.

## Provenance and protocol

- E2 raw-call archive SHA-256: `fe94dcf6b9d14499bf4abd038a189ab9919466479dfe5331ea54b2fb23ecfbd8`; request-results SHA-256: `06eebff62512fe5ae0a51d606fae84906d7585af844642f37235e081da31bed4`.
- Frozen G_pilot manifest SHA-256: `0b7300a171b9efd25c3c9742cf84de8d1e9b85d23f23573ac8a4a5b3dc2e9e34`. Each raw response invoked its requested macro; E2’s recorded and replayed canonical hashes agree.
- E1 shared initial evaluations SHA-256: `8c659e6209807b2a0e1841cde86a46695324c66f37b2f85ee24259f6b9d159c9`. Best initial fitness was `0.490582252501` (accuracy `0.4930`).
- Train-only manifest SHA-256: `26c3e3f7b8ee8b2eb3169d684fbc4bf7e0c429f38f0e7bd2654278b87cef63f4`; split fingerprint: `41bc42fedd084e7c6f67d995be6cb84d77eb72acc44fca3b31fe3691301b129f`; split ID: `mnist-validation-seed-42-41bc42fedd084e7c`.
- Evaluator: the E1 500-example training subset, seed 42, fixed 2,000-row train-derived validation set, StandardScaler + multinomial LogisticRegression, and the V3.2 stage-one ranking score. Macro calls were expanded and scored as G0 ASTs.
- Each expansion passed E1 compilation and the frozen V4 limits (at most 127 expanded nodes, depth 6, feature width 128); all expanded operations are G0 primitives. No exact canonical expanded-AST match existed in either E1 condition or the shared initial records. E1 artifacts also omit the full run-time dataset fingerprint/evaluator configuration, so no score reuse was justified; all three were scored in the current E1 environment.

## Results

| E2 macro | Expanded AST SHA-256 | Fitness | Validation accuracy | Feature dimension | Feature runtime (ms) | Δ fitness vs initial best | Exact E1 structure match |
|---|---|---:|---:|---:|---:|---:|---|
| `stroke_degree_profile` | `87887eea08d331f8675e3bb791095391fa3a1eab2197fda8fcc06b5ca8f70a0a` | 0.491352637 | 0.4950 | 19 | 660.703 | +0.000770384 | No |
| `multiscale_spatial_profile` | `000c4c95cc31280437668e06372ef7f34c56aad8cdb1cd9ae40e3412e3d9fd0c` | 0.822582449 | 0.8280 | 116 | 686.749 | +0.332000196 | No |
| `multiscale_spatial_degree_profile` | `1e70cdc09e2daa3fed1a047205d4d30c383546055d6bc4e214db075de888c532` | 0.778964811 | 0.7825 | 18 | 358.535 | +0.288382558 | No |

Each raw macro call and its canonical expansion is the same program for evaluation; no score is attributed to syntax alone. “No exact match” refers to canonical expanded-AST identity, not to a proof of semantic inequivalence.

## Research recommendation

Treat E3 only as a representation-quality screen. These three scores cannot establish search-efficiency or causal abstraction utility; the next evidential step, if pursued, is a bounded G0-versus-G_pilot fresh-search comparison using the same frozen E1 objective and data split.
