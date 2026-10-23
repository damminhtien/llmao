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
   every changed source and fixture and use fresh macro-free G0. Do not require
   a live Plus usage snapshot before launch. The contract must continue to
   prohibit paid credits and rate-limit resets. Do not continue this run or draw
   discovery conclusions from it.

## Data-free response evidence — 2026-10-15

- The worker instructions now copy
  `selected_prefill/logs/evaluate/lineage_state.json["language_hash"]` exactly.
  The focused data-free context check passes for the matching parent and rejects
  the G0 seed's older `parent_language_hash`.
- Fixture `20261015-native-sequential-03` passes all 21 no-model preflight
  checks and all 44 native postconditions. One fixture-created tmux session,
  one pane, and one `CodexTmuxSessionDriver` instance served two sequential
  native launches. Each launch used the workspace-only wrapper and the pinned
  system-prompt-file route, produced its own JSONL transcript, passed the
  checker and denial probes, and left candidate/workspace files unchanged.
- The contract-fixture validator accepts the result and independently checks
  transcript hashes and tool-call summaries. Result SHA-256 is
  `131c032afae48aee8dc30c076be8315f215327f60d5eb10677dd247b4fc4f5f8`;
  preflight SHA-256 is
  `0ac56dfb6779c6ac3d968b944c62237fba7fde578b1e3cbdcad0bbcca6a95069`.
  Transcript SHA-256 values are `72676b37badefad74a81b1eb9d51d5b67b876480b937eebdc2a5b0074e67926e`
  and `27f0cd07d3b63cb70cca94b847fc7714e700b9e9edeefc6556ecabe6f5fa32a2`.
- Setup attempt `20261015-native-sequential-01` used direct-file invocation
  instead of the documented `python -m` form; it stopped before preflight and
  did not create a native worker. Its `setup_failure.json` is retained with
  SHA-256 `cba8949828e79d3ea87bdeba7095cf8a0e2f3aa95fbbd25b12866f04dd5253b2`.
- Attempt `20261015-native-sequential-02` passed preflight but exposed that the
  wrapper allowed only the production prompt path. Inspection of the exact
  launch command and wrapper allowlist diagnosed rejection of the fixture's
  separate prompt; the wrapper's error text was not captured. No JSONL
  transcript was created and the detached tmux session disappeared. The result
  and both invocation failure records remain preserved. The wrapper now accepts
  only a workspace copy whose bytes
  match the checked-in data-free fixture prompt; arbitrary prompt overrides
  remain rejected. The successful sequential fixture above uses that exact
  route. No `respawn-pane` error occurred in the passing fixture, so it supplies
  no new stderr for the original failed pilot's nine `respawn-pane` failures;
  those historical failures remain unchanged.
- Before a later contract is frozen, the freezer now verifies the previous
  repair contract and rehashes all 211 records in its failed archive, in
  addition to the 218 records in the earlier follow-up archive. It pins both
  failure histories and the passing fixture. This remains fixture and audit
  evidence only; it is not a scientific pilot result.

## Stop point

This plan records the failure and the work required to make another run
auditable. It does not authorize another scientific pilot automatically.
Primary discovery remains closed until a separately contracted run passes every
gate and Phase 0 has a verified final protocol hash.
