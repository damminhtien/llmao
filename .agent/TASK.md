# LLMAO E2 — Minimal Macro Adoption Capability Probe

## Goal

Determine whether local Qwen can generate structurally valid G_pilot programs
that explicitly invoke each of the three frozen macros when directly instructed.
This is a six-request generation-only diagnostic, not an optimization search.

## Constraints

- Use the checksum-verified frozen G_pilot language, E1 schema/validator, and
  resource-capped local Ollama client.
- Issue exactly two independent requests per macro, with fixed recorded seeds,
  `free_exploration` focus, and no retries or repairs.
- Do not score candidates, load MNIST, use the official test partition, change
  V3.2/E1 evidence, discover macros, or start a search.
- Preserve immutable raw responses in a fresh E2 output root.
- Stop after the capability report; do not launch a follow-up experiment.

## Acceptance

- All six direct requests and their outcomes are archived with per-request
  schema, structural, expansion, identity, duplicate, token, and duration data.
- Per-macro invocation/validity/expansion/distinctness rates and failure
  categories are reported.
- No evaluator, dataset, retry, or search path is invoked.
