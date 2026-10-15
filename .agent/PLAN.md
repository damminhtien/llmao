# LLMAO V4 milestones

The detailed requirements remain in `TODO.md`. Each milestone below ends at an independent verification boundary. Keep only one milestone active at a time and update `STATE.md` with evidence before moving forward.

## M0 — Native checker and sandbox fixture

**Status: complete.** The data-free fixture demonstrated structured checker feedback and denied writes outside the candidate workspace. Evidence and digests are in `V4_SANDBOX_REPAIR.md` under `20261015-native-boundary-04`.

## M1 — Respond to the failed exploratory follow-up

**Status: complete.** Earlier repair attempts remain failed and immutable; the
documented response and separately contracted 20261015-04 pilot are complete.

- Clarify Scalar/Vector contracts and require genuine inherited-macro use by a descendant.
- Make checker failure guidance explicit; workers must report infrastructure failure and stay within the original proposal budget. Do not create environments or modify files outside the candidate boundary.
- Bound the verified launcher, runtime, strict workspace-only policy, preflight, source digests, and native fixture evidence into a new, separately hashed contract.
- Use a fresh G0 initialization and preserve the original ten-proposal budget and all validity, eight-distinct-representation, macro-use, descendant, resource, and boundary gates.

The 20261015-01 repair attempt evidence:

- Contract `V4_FOLLOWUP_REPAIR_CONTRACT.json` was hashed before launch and
  pinned the passing `20261015-native-boundary-05` fixture, exact worker
  overlay/runtime, and fresh macro-free G0.
- The run reached 10/10 checkpoint iterations but all ten proposals failed
  candidate-context validation. Each candidate retained the seed's
  `parent_language_hash` instead of the selected prefill's
  `lineage_state.json["language_hash"]`.
- Attempts 2–10 report `tmux respawn-pane` exit 1. The pilot captured zero
  JSONL transcripts, so the boundary gate cannot be established. The final
  archive manifest is pinned at
  `results/v4/phase10_followup/archive/repair_followup_20261015-01/manifest.sha256`.
- That response plan did not authorize a pilot on its own. After the user
  requested the next phase, the data-free gates and new contract below were
  completed and the separately contracted 20261015-02 pilot was run.

Response gates now pass in data-free evidence. The lineage regression rejects
the old G0 parent hash. Fixture `20261015-native-sequential-03` passed 21/21
preflight and 44/44 native checks with two sequential calls through one
fixture-created pane and one driver; each call has a JSONL transcript. The
freezer and launcher rehash all 218 earlier archive records and all 211 repair
archive records, pin the passing fixture, and require unused paths for the new
contract. Ruff, `py_compile`, `git diff --check`, and 26 focused tests pass.

Contract `V4_FOLLOWUP_REPAIR_CONTRACT_20261015-02.json` is frozen at SHA-256
`7689417fc9295bb4c49565f92240f27aad890bdff853234b34a8f4b60dddb60e`, and its
`--validate-only` gate passes. The contract pins the successful data-free
fixture and both immutable failed archives. Freezing and validation launched no
worker. The passing fixture does not reproduce the original pilot's nine
`tmux respawn-pane` failures; retain those as failed historical evidence. No

The separately contracted pilot then ran ten proposals with no replacements
and failed 0/10 candidate-context validations. All ten candidates retained
G0's parent hash rather than the selected prefill's current language hash.
Attempts 2–10 have `tmux respawn-pane` exit-status-1 errors. No per-worker JSONL
transcript was archived, and the failure files omit stdout/stderr. A post-run
scan checked ten structural bundles and found no monitored boundary change or
fresh-G0 mismatch, but the missing transcripts leave that gate incomplete.
The archived manifest is marked `failed`, has 208 verified entries, and hashes
to `cd059044554c7a83a26499e759c7ddcf9026d54e886c49a104c1f2f7421b9f08`.
Details and new required data-free checks are in
`V4_FOLLOWUP_REPAIR_REPORT_20261015-02.md` and
`V4_FOLLOWUP_REPAIR_RESPONSE_PLAN_20261015-02.md`.

M1 is complete after pilot `20261015-04` passed the separately contracted
exploratory gates. Fixture `20261015-real-runner-lineage-04` passes through
the real EvE runner with seven lineage/context gates, a hashed JSONL transcript,
a strict language-only sandbox probe, and a successful tmux stdout/stderr capture
probe. Contract `V4_FOLLOWUP_REPAIR_CONTRACT_20261015-04.json` passed
`--validate-only` and pins both the immutable failed -02 pilot archive and the
pre-worker Hydra startup failure from contract -03. The -03 attempt created no
run directory or worker proposals. Pilot -04 completed its original
ten-proposal budget without replacements and passed the gate audit in
`V4_FOLLOWUP_REPAIR_REPORT_20261015-04.md`. Its archive manifest SHA-256 is
`d135dbf93ba84ed255c5b9f5c235253e9d50c3cbd708eb324430e9700b741e6b`; the
result remains exploratory feasibility evidence only.

**Done when:** a separately contracted exploratory pilot passes every gate, all proposals and native transcripts are preserved, and there are no candidate-boundary deviations. Do not replace invalid, failed, or repeated proposals. A failed gate remains failed and requires a separately documented response.

## M2 — Final preregistration and implementation pins

**Status: active.** Scientific Phase 0 choices are fixed in
`V4_PRIMARY_DESIGN.md`; finish implementation pins, canonical protocol
finalization, and launch evidence before Phase 12 discovery.

Integrate the primary design, objective, budgets, seed set,
source/configuration pins, common initial-program digest, resume/failure
rules, and analysis requirements into a versioned canonical protocol. Verify
the data-free sandbox preflight and native lineage fixture, then validate a
seed-specific contract for every discovery seed.

**Done when:** the final protocol is complete, its hash verifies, all pinned implementations and configurations match it, and the launch checks in `V4_PRIMARY_DESIGN.md` pass.

## M3 — Phase 12 language discovery

Run matched independent searches only under the verified protocol. Preserve every candidate, language, guidance revision, token record, trajectory, and lineage artifact. Do not access official test data.

**Done when:** the preregistered runs and manifests reconcile with their budgets and hashes, and the lineage archive is complete.

## M4 — Select and freeze G*

Select using discovery evidence only; export and hash the canonical language and freeze its primitives, compiler, evaluator, and dataset protocol.

**Done when:** `results/v4/frozen_manifest.json` verifies every required frozen artifact.

## M5 — Phase 14 fresh-search evaluation

Run the independent fresh-search comparison defined by the frozen protocol. Do not carry discovery populations into evaluation.

**Done when:** all required conditions, seeds, budgets, outputs, and run manifests pass the protocol's completeness checks.

## M6 — Phases 15–16 language analyses

Complete semantic ablation and primitive reuse analyses under their frozen boundaries.

**Done when:** each analysis has reproducible inputs, outputs, and protocol-conformant summaries.

## M7 — Phases 17–19 secondary comparisons

Complete transfer, human-language comparison, and optimizer-language interaction as specified in the protocol.

**Done when:** all required datasets, conditions, seeds, and analyses reconcile with the frozen design.

## M8 — Phase 20 optional Level B

Run only if the preregistration explicitly includes primitive synthesis; otherwise record the protocol-based omission and close the milestone.

## M9 — Phases 21–22 statistics and report

Complete preregistered statistics, evidence checks, and the final scientific report.

**Done when:** report claims map to verified evidence, limitations are explicit, and all applicable `TODO.md` gates are closed.
