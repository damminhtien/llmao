# LLMAO E3 — Evaluate Existing Macro-Bearing Programs

## Objective

Score the three distinct macro-bearing programs preserved by E2 under the E1 train-only evaluation protocol. This is a bounded descriptive representation check, not a search or causal utility experiment.

## Boundaries

- Use only the frozen E2 raw requests/results, frozen G_pilot manifest, E1 shared initial evaluations, and checksum-pinned E1 train-only data source.
- Reuse a saved score only when the expanded AST, full evaluator configuration, and data fingerprint match. Otherwise score at most three previously unevaluated expanded ASTs.
- Never launch a model or optimizer, access official test data, modify E1/E2 evidence, or run a search.

## Completion

Write a fresh E3 report and machine-readable result under `results/v4/e3`; report provenance, validation, scores, runtime, baseline comparison, and limits. Stop after the three program evaluations.
