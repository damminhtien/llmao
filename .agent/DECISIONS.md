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
