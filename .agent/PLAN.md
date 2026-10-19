# E2 execution record

## M0 — Verify frozen inputs and bounded direct-call path

**Complete.** The E1 budgeted client supports one direct structured request
without invoking its proposer repair loop. The frozen G_pilot checksum,
provenance, G0 grammar, macro signatures, local model tag, fresh output root,
and six-request token reservation passed preflight.

## M1 — Test the no-score E2 runner

**Complete.** Mock coverage verifies six direct requests, fixed seeds/caps,
typed macro parsing, canonical expansion, duplicate identity, and failure
recording. The focused E1 and E2 suite passed 20 tests; Ruff and formatting
checks passed.

## M2 — Execute and archive the capability probe

**Complete.** Exactly six Qwen requests ran, two per macro. All responses were
raw macro invocations, typed and structurally valid, and successfully expanded.
The second response per macro repeated the first expanded AST. No scores or
MNIST data were used. Raw calls and summaries were made read-only.

## M3 — Report and stop

**Complete.** Results and limitations are recorded in `.agent/STATE.md` and
`results/v4/e2/macro_adoption_probe_2026-10-19/`. No follow-up run is launched.
