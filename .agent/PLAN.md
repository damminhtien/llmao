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

**Status: complete for protocol v10.** Protocol SHA-256 is
`ef4050aa854baa0aefd0273c5ed5077b2f9ba6e4200dff7084d10668da54610d`; all five
seed contracts and launch evidence were frozen, and Phase 12 runs were started.
The runs remain incomplete and are documented in `STATE.md` and `TODO.md`.

**Done when:** the final protocol is complete, its hash verifies, all pinned implementations and configurations match it, and the launch checks in `V4_PRIMARY_DESIGN.md` pass.

## M2.1 — Contain V4 outputs under the LLMAO checkout

**Status: implementation complete; live sandbox and fixture gates pending.**
The audit and target storage layout are documented in
`docs/V4_ARTIFACT_STORAGE_ARCHITECTURE.md`. New persistent outputs, scratch,
and the MNIST cache must resolve under `results/v4/`; the sandbox must deny
workers access to that cache. The pinned EvE checkout/runtime and user-managed
credentials remain external inputs. Preserve existing external fixture and v10
cache directories and all v10 run roots without moving or rewriting them.

The shared path resolver now enforces the boundary across V4 output CLIs,
evaluators, collectors, and fixture entry points. Future fixture scratch and
the V11 cache use repository-local paths; unit tests cover absolute-path and
symlink escapes. Freeze a new contract/layout version before starting another
primary run; do not reuse a v10 run root under changed path rules.

**Done when:** output paths outside `results/v4/` and symlink escapes are
rejected; new fixtures, the MNIST cache, and writer outputs remain repo-local;
workers cannot read the cache; failure scratch is recoverable; and contract
manifests verify the layout and relative paths.

## M2.2 — Freeze the reduced V11 experiment scope

**Status: design amendment complete; protocol and contracts pending.**
`V4_PRIMARY_DESIGN_V11.md` keeps five discovery and five evaluation seeds,
the original per-run budgets, and four matched Phase 14 conditions (`G0` and
`G*` under fixed Codex and EvE). It omits the 20 semantic-ablation and 80
transfer runs, reducing the planned search count from 135 to 25. Primitive
reuse, structural human-language comparison, and optimizer interaction are
secondary analyses of existing runs and add no searches. Preserve protocol
v10 and all its partial run evidence unchanged.

**Done when:** the path cutover is committed, protocol revision v12 supersedes
the unused prelaunch v11 artifact with the reduced condition matrix and
storage-layout version 2, and five fresh seed contracts validate before Phase
12 launch.

## M3 — Phase 12 language discovery

Run five matched independent searches only under protocol revision v12 and the
contracted storage layout. Preserve the v10 attempts as incomplete historical
evidence; do not resume or pool them with v11. Preserve every candidate,
language, guidance revision, token record, trajectory, and lineage artifact.
Do not access official test data.

**Done when:** the preregistered runs and manifests reconcile with their budgets and hashes, and the lineage archive is complete.

## M4 — Select and freeze G*

Select using discovery evidence only; export and hash the canonical language and freeze its primitives, compiler, evaluator, and dataset protocol.

**Done when:** `results/v4/frozen_manifest.json` verifies every required frozen artifact.

## M5 — Phase 14 fresh-search evaluation

Run the four matched V11 conditions (`G0`/`G*` × fixed Codex/EvE) over five
independent seeds. Do not carry discovery populations into evaluation.

**Done when:** all required conditions, seeds, budgets, outputs, and run manifests pass the protocol's completeness checks.

## M6 — Phase 16 primitive reuse analysis

Complete the descriptive, non-causal primitive reuse analysis from existing
discovery and evaluation artifacts. Phase 15 is omitted in V11.

**Done when:** each analysis has reproducible inputs, outputs, and protocol-conformant summaries.

## M7 — Phases 18–19 secondary comparisons

Complete structural human-language comparison and optimizer interaction from
the V11 Phase 14 matrix. Phase 17 transfer is omitted in V11.

**Done when:** all required datasets, conditions, seeds, and analyses reconcile with the frozen design.

## M8 — Phase 20 optional Level B

Record the protocol-based omission and close the milestone without a Level B
experiment.

## M9 — Phases 21–22 statistics and report

Complete preregistered statistics, evidence checks, and the final scientific report.

**Done when:** report claims map to verified evidence, limitations are explicit, and all applicable `TODO.md` gates are closed.
