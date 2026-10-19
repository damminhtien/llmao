# LLMAO E1-PREP — Minimal Abstraction Utility Experiment

## Goal

Prepare a reproducible, bounded exploratory comparison of G0 and the frozen exploratory G_pilot language using the existing V3.2 iterative optimizer and V4 language validator/expander.

## Constraints

- Do not resume V14, launch an E1 search, or run further V4 discovery.
- Never read, fetch, load, or materialize the official MNIST test partition.
- Leave historical V3.2 and V4 protocols and evidence unchanged.
- Use the existing local Qwen/Ollama client and identical optimizer feedback and resource policies in both conditions; G_pilot vocabulary is the sole treatment difference.
- Do not import V10/V14 populations or search feedback.
- Keep preparation to the train-only loader, small adapter, focused tests, and reproducibility record. Do not build another optimizer or orchestration framework.

## Acceptance

- The train-only data source, split semantics, provenance hashes, and saved fingerprints are verified and fail closed.
- G0 and G_pilot proposal grammars, macro expansion, expanded-AST deduplication, shared initial score design, and bounded request/attempt/token behavior have focused coverage.
- No model search request or candidate evaluation is launched during E1-PREP.
- A no-token preflight validates the frozen manifests, initial program set, dataset split, local model availability, conflicts, output path, and resource caps.
- Commit only the focused E1-PREP files and its regression tests/state record on `v4-evolving-bias-language`.
- Stop after E1-PREP. A separate explicit task is required to execute E1.
