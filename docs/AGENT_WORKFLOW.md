# Long-running coding agent workflow

The repository holds the durable task brief, milestone plan, current state, and decisions. Conversation history is not the project record.

## File roles

- `.agent/TASK.md` defines the goal, constraints, and acceptance criteria. Keep it stable while the goal remains active.
- `.agent/PLAN.md` splits the goal into milestones that can each be implemented and verified independently.
- `.agent/STATE.md` records completed work, the current milestone, the exact next step, known issues, and validation evidence.
- `.agent/DECISIONS.md` is an append-only log of durable decisions and why they were made.
- Research specifications and checklists remain in their existing canonical files; `.agent/` points to them instead of copying them.

## Opening or resuming a thread

Read these files first:

```text
AGENTS.md
.agent/TASK.md
.agent/PLAN.md
.agent/STATE.md
.agent/DECISIONS.md
```

Then check the working tree and resume only the next unfinished milestone. Read or query only the additional files needed for that milestone. If the user's request changes the active goal, checkpoint its task, plan, and state under `.agent/archive/<date>-<slug>/` before replacing the active brief.

Suggested continuation prompt:

```text
Read AGENTS.md, .agent/TASK.md, .agent/PLAN.md, .agent/STATE.md, and .agent/DECISIONS.md.
Continue the active task from STATE.md. Work only on the next unfinished milestone
in PLAN.md, and inspect only the additional files needed for it.
```

## Milestone loop

For each milestone:

1. Confirm its scope, dependencies, and verification boundary in `PLAN.md`.
2. Inspect the smallest relevant set of source files, contracts, and evidence.
3. Implement the milestone without silently changing its constraints or budget.
4. Run its narrow validation, inspect the result, and repair failures before moving on.
5. Update `STATE.md` with what passed, what did not, exact evidence, and the next step.
6. Make a focused Git checkpoint when the milestone is complete; keep unrelated changes out.

Do not mark work complete from a successful process exit alone. Record whether evidence is a data-free fixture, smoke run, partial trace, exploratory result, or completed primary result. Keep failed attempts and their original budgets visible.

## Context checkpoints

Update `STATE.md` before handing off, ending a thread, or reaching a context boundary. Include:

```markdown
# Current state

Completed:
- ...

Current:
- ...

Next:
- Exact file or command to inspect/run, and the expected evidence.

Known issues:
- ...

Validation:
- Command and result, or why it has not run.
```

After two or more compactions in one task, checkpoint the state and start a fresh thread with the continuation prompt above. Also rotate when the thread repeatedly rereads the same files without closing a milestone. Do not use the fresh thread to reset budgets, discard failures, or claim incomplete work as complete.

## Repository-specific continuation

For LLMAO V4, use `docs/v4/V4_PROTOCOL.md`, `docs/v4/V4_PRIMARY_DESIGN.md`, and `TODO.md` as the scientific contract. A pilot is not primary discovery evidence. Preserve all frozen artifacts and respect the official-test boundary. Do not require a live Plus usage check before a run; do not upgrade or use paid credits.

## V4 native worker launch and sandbox

These rules apply to every V4 native Codex worker, including exploratory pilots and data-free native fixtures.

- Set EvE's `driver.executable` to the absolute path of `scripts/codex-v4-sandbox`. Keep `driver.driver=codex_tmux`. Do not launch a V4 worker with raw `codex`, the EvE default executable, or `codex_exec`.
- Use the approved V4 launch/fixture entrypoint and its frozen contract. The contract must pin the wrapper, worker instructions, project Python runtime and dependency versions, structural checker bundle, permission profile, and passing native preflight evidence. Validate the contract before launching; do not assemble a one-off Hydra or CLI command that bypasses it.
- Run `experiments/v4_sandbox_preflight.py` before a new native fixture/model launch or whenever the wrapper, Codex CLI, Python runtime, permission profile, or checker bundle changes. Require `passed: true` and every recorded check to be true. Legacy v10 contracts expect 21 checks; storage-layout v2 contracts expect 22, including an explicit denied-read probe against the local MNIST cache. On any failure, stop before starting a model worker, retain the evidence, inspect the exact command and stderr, and fix the failed boundary before retrying.
- The wrapper must use an isolated `CODEX_HOME`, install `llmao-v4-workspace-only`, and reject legacy `sandbox_mode` settings and policy-changing CLI overrides. Never weaken the profile to make an interpreter or command work; do not edit the user's global Codex configuration.
- Build checker bundles with the project venv entrypoint. Use the bundle's resolved Python binary and recorded `python_site_packages` path under the strict profile. Do not substitute system Python, make another venv, install dependencies, or create speculative symlink/runtime workarounds.
- Keep tmux for the long-running native worker session. The Codex/macOS permission profile enforces filesystem and network access; tmux only manages the session. The deterministic no-model preflight runs as a direct sandboxed subprocess and must pass before tmux creates a model worker.
- Treat configuration parsing as configuration evidence, not enforcement evidence. A legacy-policy run proves only the restrictions it actually exercised. A timeout is an observed timeout until logs establish a cause; do not attribute it to a catalog, sandbox rule, or interpreter without evidence.
- Avoid repeated manual variants. Preserve each failed attempt and its exact command, CLI/runtime identity, stdout/stderr, and policy digest. Change one diagnosed cause at a time, rerun the bounded preflight, and record the result before proceeding.

The canonical implementation and verified boundary are documented in `docs/v4/V4_SANDBOX_REPAIR.md`. Keep the numeric preflight count synchronized with its tests and every contract validator if the probe set changes.
