# V4 follow-up repair pilot 20261015-02 — failed

## Contract and run

The pilot used frozen contract
`V4_FOLLOWUP_REPAIR_CONTRACT_20261015-02.json` (SHA-256
`7689417fc9295bb4c49565f92240f27aad890bdff853234b34a8f4b60dddb60e`). The
launcher passed `--validate-only` before launch. Run ID:
`run-20261015_151539_503246-repair_followup_20261015-02-de2b210f0a85`.

The runner completed ten proposal slots with no replacements and exited 0.
Runner exit status is not a scientific pass. All ten candidate evaluations
failed context validation, so the pilot failed its validity gate (0/10 valid;
8/10 required).

## Gate audit

Every archived candidate retained G0's
`parent_language_hash` (`34053b62a917cb7f19b572a4458440972350ea800391fdeba2d3f624cc331b2f`).
The selected prefill's evaluator lineage state recorded
`language_hash=5ba1e2f9e0b1d45a4e0c6fa9825491f83e169bae43bde63fe03863008315e765`.
The evaluator rejected all ten with `candidate language parent hash does not
match`. Attempt 1's native completion artifact reports `status=ok` but no
changed files; its archived patch is empty. Attempts 2–10 have native launch
errors at `tmux respawn-pane`, each with exit status 1.

No proposal JSONL transcript was captured. The archive records one attempt as
`driver_artifacts_only` and nine as `missing`; neither completion metadata nor
the nine error files contain per-worker JSONL. The tmux error files retain the
failed command and exit status but omit stdout and stderr, so this report does
not infer the cause of the pane failures.

The post-run boundary audit checked ten structural bundles and found no
monitored boundary violation. The fresh-G0 check also found no violation.
Because the per-worker transcripts are missing, the protected-boundary gate is
incomplete; the pilot does not pass that gate. All ten submissions remain
counted and failed, with no replacement or rescore.

The pinned stage-one evaluator uses the MNIST training partition and fixed
validation split; the official test split remains disabled. No live Plus usage
check was performed. The contract retains its restrictions on paid credits,
plan upgrades, and rate-limit resets.

## Preserved evidence

The immutable archive is
`results/v4/phase10_followup/archive/repair_followup_20261015-02/`. Its manifest
records 208 verified file entries and is marked `failed`.

| Artifact | SHA-256 |
| --- | --- |
| `manifest.json` | `cd059044554c7a83a26499e759c7ddcf9026d54e886c49a104c1f2f7421b9f08` |
| `execution.json` | `f212bf12663a99b77d5f0bad3f461dc1d20c045be92269f5453caa6502817d92` |
| Frozen contract | `7689417fc9295bb4c49565f92240f27aad890bdff853234b34a8f4b60dddb60e` |

This is failed exploratory feasibility evidence only. It is not a discovery
result and does not change the conclusions of either earlier failed pilot.
The next response requirements are recorded in
`V4_FOLLOWUP_REPAIR_RESPONSE_PLAN_20261015-02.md`.
