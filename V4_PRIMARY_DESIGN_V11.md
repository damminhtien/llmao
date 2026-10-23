# V4 primary-design amendment v11 — reduced experiment matrix

Status: **approved scope for the next primary protocol**. This amendment
supersedes the planned fresh-search matrix and secondary-run scope in
`V4_PRIMARY_DESIGN.md` for new V11 work only. Protocol v10, its five contracts,
partial run roots, and source digests remain immutable historical evidence.
V11 must use the new storage layout and a new protocol-scoped run root.

## Research question

Does a language evolved from `G0` improve fresh-search efficiency over `G0`
when both are used by a fixed iterative optimizer and by EvE?

The primary claim is limited to MNIST fresh search under the two tested
optimizers. This design does not test semantic naming effects or transfer to
other datasets, and it cannot support a general cross-task transfer claim.

## Retained search count and budgets

Keep five independent discovery seeds:

```text
1101, 1202, 1303, 1404, 1505
```

Keep five independent fresh-search seeds:

```text
101, 202, 303, 404, 505
```

Each run retains the existing frozen budget: 20 common initial programs,
200 unique successfully evaluated expanded ASTs total, at most 540 adaptive
proposal attempts, and the same per-run token, turn, timeout, and failure
rules. Every condition restarts from the common initial-program set. No
invalid, failed, timed-out, or duplicate proposal is replaced.

Retain five seeds because the preregistered exact one-sided sign-flip test can
first attain a p-value at or below 0.05 with five paired seed records (minimum
possible value `1/32`). Four seeds cannot meet that criterion (`1/16`). Do not
reduce the seed count to make a nominally significant result easier or harder.

## Primary search matrix

### Discovery

Run five independent joint language-discovery searches:

```text
G0 + EvE + language evolution
```

Select `G*` only from complete, successfully evaluated discovery evidence,
using the frozen v10 language-selection rule. Do not use fresh-search or
official-test evidence to select it.

### Fresh-search evaluation

Run the following four matched conditions for each of the five fresh seeds:

| Language | Optimizer |
|---|---|
| `G0` | fixed iterative Codex |
| `G*` | fixed iterative Codex |
| `G0` | EvE |
| `G*` | EvE |

The two language conditions under each optimizer share the same seed, initial
programs, candidate and token budgets, model, reasoning effort, evaluator,
data split, context policy, and resource rules. The `G*` manifest is frozen
before these fresh searches. Do not carry a discovery population, candidate,
guidance revision, or optimizer state into evaluation.

This yields **25 primary search runs**: five discovery runs and twenty
fresh-search runs. The previously planned design contained 135 runs: five
discovery, thirty six-condition fresh searches, twenty semantic-ablation
searches, and eighty four-dataset transfer searches. V11 removes 110 runs
(81.5%) while retaining the five-seed primary comparison and its two optimizer
replications.

`GH` remains a frozen descriptive language reference. It receives no fresh
search runs in V11. Compare its manifest, primitive inventory, and size with
`G0` and `G*`; do not make a comparative fresh-search-performance claim for
`GH`.

## Primary analysis

Retain the candidate-budget AUC definition and primary numeric criteria from
`V4_PRIMARY_DESIGN.md`. For each fresh seed, calculate the two paired contrasts
`AUC(G*) - AUC(G0)`, one within each optimizer. The primary paired difference
is their mean. Report all five paired differences and both optimizer-specific
means.

Use the exact one-sided sign-flip test over all 32 assignments of the five
paired seed differences, including ties in the tail. Bootstrap the five paired
seed records 10,000 times with random seed 4204 and report the two-sided 95%
percentile interval. LLM calls, candidates, and optimizer conditions are not
independent statistical samples.

Primary support still requires all five matched seed blocks to complete, the
mean primary AUC gain to be at least 0.002, exact one-sided p at most 0.05, a
bootstrap lower bound above zero, positive mean gain under each optimizer,
positive paired differences in at least four of five seeds, macro reuse in at
least two independent fresh-search seeds, and zero protected-boundary or
official-test violations. These are evidence criteria, not a search-until-pass
rule.

## Secondary work without new searches

- **Primitive reuse (Phase 16):** descriptive lineage analysis of discovery
  and fresh-search artifacts. Report counts and score associations as
  observational; do not claim causal benefit for an individual primitive.
- **Human DSL comparison (Phase 18):** compare canonical `G0`, `GH`, and `G*`
  inventories and structural properties. Fresh-search score comparisons are
  limited to the four V11 conditions.
- **Optimizer-language interaction (Phase 19):** estimate the difference
  between the two optimizer-specific `G* - G0` contrasts from the Phase 14
  matrix. Treat it as secondary and report the five paired seed-level values.
- **Semantic ablation (Phase 15): omitted.** It would add 20 search runs and
  is not needed to answer the V11 primary question.
- **Transfer (Phase 17): omitted.** It would add 80 search runs and is
  outside the bounded MNIST claim. Do not claim transfer or general reuse
  across tasks.
- **Level B primitive synthesis (Phase 20): omitted.** Report the
  protocol-based omission; do not build or run a separate synthesis study.

Do not access official test data before the frozen-language evaluation gate.
Preserve fixture, exploratory, partial, and primary evidence as separate
levels. Never pool v10 partial runs with V11 or infer completion from them.
