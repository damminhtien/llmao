# V4 follow-up repair failure response plan

The 2026-10-15 repair pilot failed all ten candidate-context evaluations and
did not capture native worker JSONL transcripts. Its archive and audit are in
`results/v4/phase10_followup/archive/repair_followup_20261015-01/` and
`V4_FOLLOWUP_REPAIR_REPORT.md`. Preserve the archive and the original failed
pilot artifacts. Do not reuse, repair, rescore, or replace any proposal.

## Required response

1. **Make the lineage handoff exact.** In worker instructions and any
   pre-submission guard, require the child language's
   `parent_language_hash` to equal the selected prefill's
   `logs/evaluate/lineage_state.json["language_hash"]`. Do not substitute the
   seed language's own `parent_language_hash` or `base_language_hash`. Add a
   data-free context-construction check that exercises this exact parent/child
   relationship without scoring a proposal or reading official test data.
2. **Resolve the tmux worker lifecycle.** Reproduce two sequential driver
   launches in a data-free fixture using the same wrapper, runtime, prompt-file
   route, and workspace-only profile. Capture tmux stderr and the full exit
   result when `respawn-pane` fails. The fixture must demonstrate which process
   creates and reuses the pane, and must retain one JSONL transcript per worker
   invocation. Do not infer the cause from the escaped command text alone.
3. **Gate before any new pilot.** Require the preflight, exact lineage check,
   sequential-driver fixture, JSONL transcript capture, protected-file
   monitoring, and archive-collection path to pass before freezing another
   contract. Keep the original ten proposals, eight-valid, eight-distinct,
   macro-use, descendant-use, resource, and zero-boundary-violation gates.
4. **Use a new contract and unused paths if a later pilot is authorized.** Pin
   every changed source and fixture, use fresh macro-free G0, verify Plus
   ordinary usage, zero paid credits, and no reset-credit use immediately
   before launch. Do not continue this run or draw discovery conclusions from
   it.

## Stop point

This plan records the failure and the work required to make another run
auditable. It does not authorize another scientific pilot automatically.
Primary discovery remains closed until a separately contracted run passes every
gate and Phase 0 has a verified final protocol hash.
