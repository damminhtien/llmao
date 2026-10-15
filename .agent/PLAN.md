# LLMAO V4 milestones

The detailed requirements remain in `TODO.md`. Each milestone below ends at an independent verification boundary. Keep only one milestone active at a time and update `STATE.md` with evidence before moving forward.

## M0 — Native checker and sandbox fixture

**Status: complete.** The data-free fixture demonstrated structured checker feedback and denied writes outside the candidate workspace. Evidence and digests are in `V4_SANDBOX_REPAIR.md` under `20261015-native-boundary-04`.

## M1 — Respond to the failed exploratory follow-up

**Status: active.** The 2026-10-15 repair attempt failed; follow
`V4_FOLLOWUP_REPAIR_RESPONSE_PLAN.md` and retain its archive unchanged.

- Clarify Scalar/Vector contracts and require genuine inherited-macro use by a descendant.
- Make checker failure guidance explicit; workers must report infrastructure failure and stay within the original proposal budget. Do not create environments or modify files outside the candidate boundary.
- Bind the verified launcher, runtime, strict workspace-only policy, preflight, source digests, and native fixture evidence into a new, separately hashed contract.
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
- No further scientific pilot is part of this active response. First fix the
  lineage handoff and verify repeated native-driver launches plus transcript
  capture in a data-free fixture.

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
