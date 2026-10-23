# Organize versioned research documentation

Group V1, V2, V3, V3.1, V3.2, and V4 documents and reports into versioned
`docs/` and `reports/` directories. Include root-level historical documents and
versioned reports currently scattered under `reports/`, `reports/scientific/`,
and `reports/figures/`.

Keep `results/` data and manifests in place, preserve scientific content and
historical versions, and record every relocated artifact's former path and
hash. Update current links and report-generator output path literals only as
needed for the new locations. Do not change experiment logic or scientific
claims.

Complete with deterministic path/hash/link checks, graph update for path-only
source edits, updated task state, and an atomic commit. No scientific runs.
