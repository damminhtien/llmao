# Agent rules

## Start and resume

- Read `AGENTS.md`, `.agent/TASK.md`, `.agent/PLAN.md`, `.agent/STATE.md`, and `.agent/DECISIONS.md` before resuming work. Follow [`docs/AGENT_WORKFLOW.md`](docs/AGENT_WORKFLOW.md).
- Continue the active goal from `STATE.md`; inspect only the files needed for its next unfinished milestone.
- Keep this file as a routing table. Put task progress and decisions in `.agent/` and detailed process guidance in `docs/AGENT_WORKFLOW.md`.

## Project invariants

- `TODO.md` is the V4 phase checklist. `ARCHITECTURE.md`, `docs/v4/V4_PROTOCOL.md`, and `docs/v4/V4_PRIMARY_DESIGN.md` are the scientific sources of truth; do not duplicate their specifications here.
- V4 is frozen as an exploratory study. Start with the final report and
  `docs/V4_MERGE_READINESS.md`; incomplete milestones and worker launch
  procedures are historical records and do not authorize new V4 runs.
- Naming: V4 is the research study; use IDs such as `v4-primary-14` or
  “V4 primary-protocol revision 14” for protocol versions. Do not use V11/V14
  as separate study names.
- Preserve frozen V3/V3.1/V3.2 artifacts and failed pilot records. Never access official test data before the protocol's freeze and evaluation gates.
- Do not require live Plus usage snapshots or allowance checks before runs. Do not upgrade or use paid credits.
- Keep code small, readable, typed, and covered by focused regression checks when behavior changes. Never silently swallow exceptions.
- Always route V4 native Codex workers through `scripts/codex-v4-sandbox`; follow the mandatory preflight and launch procedure in [`docs/AGENT_WORKFLOW.md`](docs/AGENT_WORKFLOW.md#v4-native-worker-launch-and-sandbox).

## Repository workflow

- Prefer `rtk` for compact exploration and checks; use `rg`, exact line reads, and `git diff --check` when exact evidence matters.
- For codebase questions, query `graphify-out/graph.json` first. After relevant code changes, run `graphify update .`; never index secrets or `.env` files.
- Before committing, inspect status and diff, run `git diff --check` and the narrowest relevant validation, and stage explicit paths only.
- Commit completed implementation, configuration, or documentation work unless the user says not to.

## Navigation

- Current task and continuation state: `.agent/TASK.md`, `.agent/PLAN.md`, `.agent/STATE.md`, `.agent/DECISIONS.md`
- Long-running agent workflow: `docs/AGENT_WORKFLOW.md`
- Research architecture and protocol:
  `ARCHITECTURE.md`, `docs/V4_ARTIFACT_STORAGE_ARCHITECTURE.md`, `docs/v4/V4_PROTOCOL.md`,
  `docs/v4/V4_PRIMARY_DESIGN.md`, `docs/v4/V4_PRIMARY_DESIGN_V11.md`
- Phase checklist and experiment evidence: `TODO.md`, `reports/v4/V4_*_REPORT.md`, `reports/v4/V4_*_RESPONSE_PLAN.md`
- Reproducibility: `docs/REPRODUCIBILITY.md`
- Frozen V4 findings and integration: `reports/v4/V4_EVOLVING_BIAS_LANGUAGE.md`,
  `docs/V4_MERGE_READINESS.md`
- Versioned study documentation: `docs/VERSIONED_RESEARCH.md` and
  `docs/VERSION_ARTIFACT_LOCATIONS.json`
- V1 architecture: `docs/v1/ARCHITECTURE_V1.md`
- V3/V3.1 historical design and protocols: `docs/v3/` and `docs/v3.1/`
- Versioned study documentation: `docs/VERSIONED_RESEARCH.md` and
  `docs/VERSION_ARTIFACT_LOCATIONS.json`
- V1 documentation: `docs/v1/ARCHITECTURE_V1.md`
- V3/V3.1 historical design and protocols: `docs/v3/`, `docs/v3.1/`
- V4 artifact locations and historical-path mapping: `docs/v4/README.md`,
  `docs/v4/ARTIFACT_LOCATIONS.json`
