# Decisions

Append durable workflow and research-boundary decisions here. Keep detailed scientific parameters in `V4_PROTOCOL.md`, `V4_PRIMARY_DESIGN.md`, and versioned amendments such as `V4_PRIMARY_DESIGN_V11.md`.

## 2026-10-19 — Prepare E1 separately from the V4 primary campaign

The active objective is the bounded G0-versus-exploratory-G_pilot utility
comparison. Preserve historical V10/V14 evidence and the old V4 task record;
use only the train-only MNIST source and existing V3.2/V4 components. E1-PREP
does not authorize model generation or candidate evaluation. A separate user
request is required to execute the prepared comparison.

## 2026-10-15 — Keep the root agent instructions as a router

`AGENTS.md` holds only startup rules, stable invariants, tool/checkpoint conventions, and links. Detailed continuation guidance lives in `docs/AGENT_WORKFLOW.md`; active task state lives in `.agent/`.

## 2026-10-15 — Preserve existing research sources of truth

`TODO.md` remains the phase checklist; the architecture, protocol, primary design, pilot reports, and response plans remain authoritative for scientific details. `.agent/PLAN.md` groups their open work by verification boundary instead of copying their specifications.

## 2026-10-15 — Failed pilots are immutable evidence

Keep both Phase 10 pilot outcomes failed. A later data-free fixture cannot turn either pilot into a pass. Any retry needs a separate contract, fresh G0 initialization, original proposal budget, and complete audit evidence.

## 2026-10-15 — Fresh-thread checkpoint heuristic

After two or more compactions, or when a thread repeats the same reads without completing a milestone, update `STATE.md` and continue in a fresh thread. This changes context only; it never resets experiment budgets or failure history.

## 2026-10-15 — Require the V4 native sandbox launch path

Every V4 native Codex worker must use `scripts/codex-v4-sandbox` through the approved contract-backed launch or fixture entrypoint. The worker's model prompt is too late to enforce launch configuration. A passing OS-level preflight must precede a model worker; tmux provides session management, not filesystem or network isolation. Preserve failed attempts and do not infer a timeout's cause without logs.

## 2026-10-15 — Remove live Plus usage gates

The user confirmed sufficient resources and requested removal of Plus usage checks. Launchers, fixtures, and active run guidance must not require account-usage snapshots or allowance checks. Keep the existing restrictions against plan upgrades, paid credits, and rate-limit resets, and preserve completed-run usage snapshots as historical evidence.

## 2026-10-15 — Preserve EvE's Hydra context in the traced runner

The external tmux-capture bootstrap must put the EvE checkout ahead of the LLMAO checkout on `sys.path` and run `scaling_evolve.algorithms.eve.runner` as `__main__`. Calling its decorated entrypoint from the bootstrap changes Hydra's config-module resolution. Resolve the frozen pilot configuration through this same external entrypoint before launch.

## 2026-10-17 — Keep persistent V4 outputs under the LLMAO checkout

For new contracts and runs, keep persistent V4 outputs, V4-owned scratch, and the MNIST cache under `results/v4/`, with every writer enforcing resolved-path containment. The worker sandbox must deny candidate agents access to the dataset cache. Keep the pinned EvE checkout/runtime and user-managed Codex credentials as explicit external inputs. Preserve existing external fixture/data caches and frozen run artifacts at their original paths; do not relocate or rewrite them. Use a new contract/layout version before launching with the redesigned path rules.

## 2026-10-17 — Reduce the V4 experiment matrix in protocol v11

Keep five independent discovery seeds and five fresh-search seeds, plus the
existing per-run candidate and resource budgets. Five paired seeds are the
minimum for the exact one-sided sign-flip test to attain `p <= 0.05`. Fresh
search has four conditions (`G0`/`G*` under fixed Codex and EvE), producing 20
evaluation runs after five discovery runs. Omit GH fresh-search, semantic
ablation, four-dataset transfer, and Level B synthesis. Use primitive reuse,
structural human-language comparison, and optimizer interaction as secondary
analyses of existing data only. This reduces the planned total from 135
searches to 25 and limits conclusions to MNIST fresh search; no transfer claim
is permitted. Protocol v10 and its incomplete runs remain immutable historical
evidence.

## 2026-10-17 — Supersede the unused V11 protocol before launch

Protocol artifact v11 was finalized with SHA-256
`d435b08a2dc84280e7f2d9e58b3f2203113cdb88221d0df10c6b20b0bef802b6`, but no
contracts or workers used it. Contract review found that the schema-v2 gate
required a local MNIST-cache read probe in the EvE lineage fixture even though
the separate OS-level preflight already performs that probe. Keep the finalized
artifact unchanged, correct the validator to use the recorded preflight, and
issue protocol revision v12 with the same V11 scientific scope before any
contract freeze or model worker.

## 2026-10-17 — Supersede V12 after the first path-layout startup failure

Protocol v12 and its five contracts passed preflight, fixture, and validate-only
gates, but seed 1101 failed while building the first initial-candidate context:
the contract's repo-relative protocol path was resolved from the run root. No
candidate was scored and no native discovery worker started. Preserve the V12
contract set and failed seed-1101 root without resuming it. Normalize validated
protocol and checker-bundle paths to absolute checkout paths in the runner, then
freeze protocol revision v13 and five fresh contracts before restarting Phase
12.

## 2026-10-17 — Preserve and correct the V13 cache-guard failure

Protocol v13 passed its sandbox preflight, native fixture, and five contract
validation gates. Seed 1101 scored the common initial set and launched one
contracted adaptive worker, whose valid proposal received no score because the
Phase 2 adapter still required `LLMAO_DATA_DIR` to be outside the checkout.
Preserve that run as an incomplete terminal protocol failure with its full
candidate, transcript, and token record. Update the adapter to verify the
protocol digest and allow only the exact `results/v4` cache for storage-layout
v2, while retaining the external-cache rule for legacy protocols and rejecting
symlink escapes. Protocol v14 and fresh contracts are required; do not resume
or pool the V13 run.

## 2026-10-19 — Keep E2 as a generation-only capability diagnostic

E2 uses two fixed-seed, no-score requests per frozen G_pilot macro. The six
explicitly targeted responses all invoked and validated their requested macro;
this supports a generation-preference explanation for E1's spontaneous
non-adoption, but does not establish macro utility or broad structural
capability. Preserve the E2 response archive and stop without launching a
follow-up automatically.

## 2026-10-20 — Keep E3 as a descriptive representation check

E3 evaluates only the three unique macro-bearing programs already produced by E2, after canonical expansion to G0 ASTs. Score the expanded function, not the macro syntax. Reuse prior E1 scores only with exact AST identity plus matching complete evaluator configuration and dataset fingerprint; otherwise perform no more than three train-only evaluations. The result can screen representation quality but cannot establish search-efficiency or causal abstraction utility.

## 2026-10-21 — Treat E4 as an exploratory packaging comparison

E4 compares the same three frozen G_pilot behaviors presented as G0
composition recipes versus available typed macros. Reuse the E1 shared initial
score records, train-only split, evaluator, corrected guidance-only focus
policy, and request caps. Keep prompt/schema differences logged as part of the
treatment. Do not put E2/E3 programs or measured scores into optimizer context;
do not infer causal generalization from the single seed.
