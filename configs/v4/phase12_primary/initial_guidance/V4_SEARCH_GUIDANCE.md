# V4 Phase 12 optimizer guidance

- Optimize useful, reusable typed abstractions under the frozen discovery score.
- Use only G0 primitives and inherited validated macros in macro bodies.
- Preserve the selected prefill's current lineage and all inherited definitions.
- Introduce at most one macro per proposal and require genuine use by its
  introducing candidate.
- Keep the total macro count at or below eight and respect all AST and feature
  limits.
- Use the complete score and candidate history; distinguish measured evidence
  from hypotheses and avoid exact expanded-program repeats.
- Keep proposed guidance revisions in the supplied `guidance/` tree. Do not
  alter the task, evaluator, permissions, or experiment protocol.
