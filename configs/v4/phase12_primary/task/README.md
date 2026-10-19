# LLMAO V4 primary discovery

Read this task, `AGENTS.md`, the candidate files, the G0 primitive reference,
and the current optimizer guidance before proposing one candidate. Use solver
examples and evaluator artifacts as the only measured evidence.

## Objective

Evolve the representation and G0-based typed macro language to discover useful
reusable abstractions. The primary score is the frozen V3.2 stage-one fitness
minus `0.0005` times the number of invented macros in the complete language.
The evaluator reports both components and the resulting discovery fitness.

## Language and candidate boundary

Macros may compose only G0 operations and inherited validated macros. Add at
most one macro to a proposal and use every new macro in that proposal. Keep at
most eight macros total, expansion depth at most 6, expanded size at most 127
nodes, and output width at most 128. Preserve every inherited macro definition
unchanged. The candidate's `language.json.parent_language_hash` MUST equal the
selected prefill's current language hash from
`solver_examples/<selected-prefill-id>/logs/evaluate/lineage_state.json` at
`language_hash`. It MUST NOT equal the selected prefill's own
`logs/evaluate/lineage_parent.json` `parent_language_hash`, which identifies
the grandparent language.

Do not use excluded human-language operations, executable code, Python,
imports, filesystem paths, network, subprocesses, labels, predictions,
per-example metrics, or official test data. The evaluator and data are outside
the editable workspace.

## Editable surface

{editable_files_block}
{editable_folders_block}

All other solver files are read-only. Run the pinned structural checker before
finishing. The checker returns no score and does not create an additional
proposal.

## Solver history

{solver_examples_block}

## Optimizer history

{optimizer_examples_block}

## Immutable guidance overlays

{immutable_overlay_block}
