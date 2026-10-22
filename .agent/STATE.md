# Current state

V4 is closed as a frozen exploratory study. The E1–E4 source, tests,
protocol revisions, run artifacts, data lineage, and reduced primary-campaign
status have been audited. No model, search, scientific evaluation, or
official-test loader was invoked for closure.

## Findings

- Deterministic focused suite: 208 passed.
- E1–E4 are descriptive and do not establish generalization, causal
  abstraction utility, or improved search efficiency.
- The V11-reduced 25-run primary design is incomplete; V14 seed 1101 has an
  incomplete-attempt-cap manifest, seed 1202 has a stale `running` snapshot
  without a final manifest, and there are no other V14 discovery or fresh
  runs.
- Blocking correctness defect: `llm_common.py` computes a zero-sized batch
  when exactly one attempt remains. E1 therefore cannot claim the G_pilot arm
  exhausted its 20-attempt cap. The defect is reported but not repaired or
  rerun.

## Closure artifacts

- Scientific report: `reports/scientific/V4_EVOLVING_BIAS_LANGUAGE.md`.
- Evidence manifest: `reports/scientific/V4_EVIDENCE_MANIFEST.json` (98
  bundled source, protocol, data-lineage, and E1–E4 artifact hashes).
- Checksum inventory: `reports/scientific/V4_EVIDENCE_FILES.sha256`; manifest
  sidecar: `reports/scientific/V4_EVIDENCE_MANIFEST.sha256`.
- Local annotated release tag: `v4-exploratory-final`, targeting the closure
  commit on `v4-evolving-bias-language`.

No historical experiment artifacts or scientific protocol files were edited.
