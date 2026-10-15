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

For LLMAO V4, use `V4_PROTOCOL.md`, `V4_PRIMARY_DESIGN.md`, and `TODO.md` as the scientific contract. A pilot is not primary discovery evidence. Preserve all frozen artifacts, respect the official-test boundary, and verify live account and usage conditions immediately before any future model run.
