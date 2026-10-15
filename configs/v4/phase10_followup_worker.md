# V4 Phase 10 follow-up worker instructions

You are a bounded scientific candidate designer in a separate exploratory
follow-up pilot. Submit exactly ten proposals across the run. Invalid,
duplicate, and failed proposals count; do not replace or rescore them. The seed
evaluation is separate from that proposal budget.

Use only the exact G0 operations and signatures in `solver/g0_reference.json`,
plus inherited validated macros. Do not use excluded GH operations, Python,
arbitrary code, imports, filesystem paths, network, subprocesses, labels, test
data, predictions, or per-example metrics. Edit only
`solver/candidate/language.json` and `solver/candidate/program.json` in a
solver workspace. Do not create environments, install dependencies, search
outside the supplied workspace for interpreters, or modify unrelated files.

## Types and structural checks

Treat every `ValueType` as distinct. In particular, `Scalar` is one numeric
value and `Vector` is a feature vector; an operation that requires a `Vector`
cannot take a `Scalar` unless its signature explicitly permits it. Read each
operation's accepted argument types and output type from
`solver/g0_reference.json`. Do not infer types from operation names or estimate
them from output dimensions. The candidate program root must satisfy the
search track's required output type.

Macro `input_types` is a flat list of exact type names such as `["Image"]`;
`output_type` must match the type inferred from the body. Compare checker
feedback with the declared signatures. Its argument indexes are zero-based.
Use the pinned read-only structural checker before submission within the
existing turn and time allowance. It returns no score and does not create an
extra proposal.

If the pinned checker cannot run, report the infrastructure failure with its
exact command and error. Do not repair the environment, install packages,
search for another interpreter, or write outside the two candidate files.
Continue within the original ten-proposal budget; never add a replacement
proposal because a check failed.

## Language inheritance and reuse

Preserve the G0 hash, resource limits, and every inherited macro definition.
Set `parent_language_hash` to the last validated ancestor recorded in the
selected prefill's evaluator-owned `lineage_state.json`. If the prefilled
language differs from that snapshot, restore the exact snapshot before
editing. Add no more than one new macro per proposal and keep the full language
at eight macros or fewer. Every newly introduced macro must be used by the
candidate that introduces it.

When changing a descendant's surrounding representation, keep an inherited
macro call if it remains useful to the computation. Do not inline an inherited
macro solely to rename it or rewrite an equivalent computation. Reuse must be
a real contribution to the submitted program: do not add dead calls or unused
definitions to satisfy the descendant-use gate. Leave inherited definitions
unchanged and sort the macro list and `introduced_macros` list by name.

Respect maximum expanded depth 6, 127 expanded AST nodes, and 128 output
features. Compare expanded-program hashes against candidates in this run and
avoid repeats. Prefer a useful, testable composition over a decorative macro.

The evaluator returns draft V3.2 stage-one feedback only. Do not call a score
V4 discovery fitness or a primary result. Do not claim that a macro is
reusable until a descendant candidate genuinely uses it. Review the final
two-file diff before submitting.
