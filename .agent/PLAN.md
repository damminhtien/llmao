# LLMAO V4 milestones

The detailed requirements remain in `TODO.md`. Each milestone below ends at an independent verification boundary. Keep only one milestone active at a time and update `STATE.md` with evidence before moving forward.

## M0 — Native checker and sandbox fixture

**Status: complete.** The data-free fixture demonstrated structured checker feedback and denied writes outside the candidate workspace. Evidence and digests are in `V4_SANDBOX_REPAIR.md` under `20261015-native-boundary-04`.

## M1 — Respond to the failed exploratory follow-up

**Status: active.** The 2026-10-15 repair attempt failed; follow
`V4_FOLLOWUP_REPAIR_RESPONSE_PLAN.md` and retain its archive unchanged.

- Clarify Scalar/Vector contracts and require genuine inherited-macro use by a descendant.
- Make checker failure guidance explicit; workers must report infrastructure failure and stay within the original proposal budget. Do not create environments or modify files outside the candidate boundary.
- Bound the verified launcher, runtime, strict workspace-only policy, preflight, source digests, and native fixture evidence into a new, separately hashed contract.
- Use a fresh G0 initialization and preserve the original ten-proposal budget and all validity, eight-distinct-representation, macro-use, descendant, resource, and boundary gates.

Latest attempt evidence:

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
- No further scientific pilot is part of this active response. The response
  gates and new contract are recorded below; wait for explicit authorization
  before a separate pilot.

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
live Plus usage check is required or performed.

Next, request explicit authorization before a separately contracted
exploratory pilot. M1 remains active until that pilot has passed every gate; do
not launch it automatically.

**Done when:** a separately contracted exploratory pilot passes every gate, all proposals and native transcripts are preserved, and there are no candidate-boundary deviations. Do not replace invalid, failed, or repeated proposals. A failed gate remains failed and requires a separately documented response.

## M2 — Final preregistration and implementation pins

Resolve every remaining Phase 0 decision. Integrate the primary design, objective, budgets, seed set, source/configuration pins, common initial-program digest, resume/failure rules, and analysis requirements into a versioned canonical protocol.

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
