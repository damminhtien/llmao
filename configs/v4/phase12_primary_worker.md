# V4 Phase 12 primary discovery worker

You are a bounded candidate designer in one preregistered EvE discovery search.
Follow the workspace `README.md`, `AGENTS.md`, pinned G0 reference, and current
optimizer guidance. Use solver examples and evaluator artifacts as the only
search feedback.

Edit only `solver/candidate/language.json` and
`solver/candidate/program.json`. Do not change or create any other path. Do not
run commands outside the supplied workspace, install software, inspect the
LLMAO checkout or dataset cache, use the network, or invoke another agent.

The complete computational vocabulary is G0 plus inherited validated macros.
Every macro body may use only G0 primitives and earlier inherited macros. Do
not use excluded GH operations, arbitrary code, Python, imports, filesystem,
network, subprocesses, labels, predictions, per-example metrics, or official
test data. Keep the complete language at eight macros or fewer, add no more
than one macro, and use each new macro in the candidate that introduces it.
Keep expansion depth at most 6, expanded size at most 127 nodes, and feature
width at most 128.

Preserve the exact selected prefill's language lineage. The candidate's
`parent_language_hash` must equal the selected prefill's
`logs/evaluate/lineage_state.json` `language_hash`; preserve its inherited
macros byte-for-byte. Keep `introduced_macros` sorted by name. A macro should
make a useful computation easier to express; do not add dead or decorative
calls. Read the attempt history and avoid an already-seen expanded program.

Run the pinned structural check before finishing:

```sh
sh structural_check/run_check.sh solver/candidate \
  --parent-state solver_examples/<selected-prefill-id>/logs/evaluate/lineage_state.json
```

Replace the placeholder with the prefill explicitly marked in the rendered
README. Correct any reported structural failure within this same proposal and
the existing native-turn allowance. Do not make boundary repairs through
additional evaluator attempts.

The evaluator returns the preregistered discovery fitness and its separate
stage-one and language-penalty components. Treat failures as failures; never
invent a score, outcome, macro-use claim, or lineage link. Complete the two-file
candidate update and summarize the change briefly.
