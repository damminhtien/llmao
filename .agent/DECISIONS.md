# Decisions

Append durable workflow and research-boundary decisions here. Keep detailed scientific parameters in `V4_PROTOCOL.md` and `V4_PRIMARY_DESIGN.md`.

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
