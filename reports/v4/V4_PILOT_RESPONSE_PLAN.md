# V4 pilot response plan

This plan responds to the failed ten-attempt Phase 10 pilot. The original
protocol, scores, candidates, and failure ledger remain the historical record.
The follow-up is exploratory feasibility work under ChatGPT Plus, GPT-6 Luna,
and max reasoning. It cannot produce a primary discovery conclusion.

## Evidence and diagnosis

- Attempt 1 used nested `input_types` instead of a flat list of ValueType names.
- Attempts 4 and 5 composed expressions beyond expanded depth 6. A legal
  constituent can become illegal when another enclosing call is added.
- Attempt 6 placed `regional_ink_angle_profile` before
  `multiscale_ink_angle_profile`; canonical language serialization sorts macro
  definitions alphabetically. Reordering is a diagnosis, not a retroactive
  correction of that failed proposal.
- Attempts 9 and 10 repeated previous candidate content. Different language
  revision identities can also express the same expanded representation.
- Repeated solver-entry IDs are distinct observations, not proof of independent
  discovery or statistically independent macro reuse.

## Implementation before another run

1. Provide a read-only, data-free structural candidate check using the existing
   schema, type checker, expansion limits, and lineage loader. Print structural
   feedback only. Do not repair files or execute a representation on examples.
2. Build the Phase 11 archive from verified candidate and lineage artifacts.
   Keep observation identity, candidate identity, language revision identity,
   macro behavior identity, and expanded representation identity separate.
   Retain invalid attempts and repeated score measurements.
3. Record macro birth, inherited use, unused inventory, parent-child edges,
   removals, and observed agent/run identifiers. Independent-search reuse is
   unknown unless the source supplies a declared independent search identity.
4. Prepare future pilot guidance with flat signatures, alphabetical macro order,
   depth counted after expansion, and review of previous expanded-program hashes.
   Duplicate final proposals still count; no replacement budget is permitted.

## Follow-up run contract

Use a new run ID and start from the original G0 seed. Do not import the first
pilot's winning program, population, or macro definitions. Keep exactly ten
submitted proposals plus a separate seed, one worker, zero automatic boundary
repairs, the same learner and stage-one score, and the original 8/10 validity
gate. All existing resource, macro-use, descendant-use, and boundary gates apply.
Structural checking within a worker's existing turn/time allowance does not
provide an additional score call or proposal replacement.

Report exact candidate repeats and expanded-representation repeats separately.
Also predeclare a follow-up quality gate of at least eight distinct valid
expanded representations among the ten proposals. This is an additional gate;
the original pilot is not reassessed against it.

Before launch, pin the changed guidance and tooling commits, hash the follow-up
contract, and validate the isolated EvE configuration. A live Plus usage
snapshot is not required before launch.
Do not launch a new pilot until these implementation and configuration checks
are complete. Full Phase 0 preregistration is required before Phase 12 discovery
and primary evaluation; it is separate from an exploratory pilot contract.

## Remaining primary-study decisions

The full TODO still requires fixed primary candidate/token budgets, independent
seeds, timeout/censoring rules, shared initial programs, language-complexity
penalty, language selection and tie breakers, AUC bounds, statistics, and numeric
support criteria. Record these before primary discovery, then hash the final
protocol. A follow-up pilot does not satisfy those decisions or the later
fresh-search, semantic-ablation, transfer, and statistical requirements.

## Implemented response and replay

At terminal follow-up completion, collect a new archive only after the
supervisor reports exit zero and the checkpoint/telemetry cover all ten
proposals. Verify every worker bundle against the frozen manifest, preserve
the separate seed and all failed proposals, copy evaluator logs and native
transcripts without Codex authentication files, and hash each copied file.
Reconcile score JSON with telemetry before structural replay and lineage
analysis. A terminal process alone cannot satisfy any scientific gate.

Replay must distinguish context acceptance from a successful stage-one score.
The pinned EvE evaluator publishes the candidate's validated lineage before
fitting the learner. If fitting or artifact production fails, replay must
verify that accepted structure and retain the failed score without promoting
it to a successful evaluation. Descendants may inherit that evaluator-owned
state. Context failures instead retain the selected parent's state. Record
structural validity and score success separately and reject inconsistent state
transitions. The frozen evaluator and historical artifacts remain unchanged.

### Follow-up worker interface

The running follow-up exposed an interpreter-delivery defect: native worker
tool shells do not receive the runner's `LLMAO_PYTHON` variable. The next bundle
version now includes `run_check.sh`, which binds a verified absolute project
interpreter path while preserving its virtualenv entrypoint symlink. Workers
can invoke `sh structural_check/run_check.sh ...`; this needs no inherited
interpreter variable or project Python on PATH. The exporter probes the
interpreter version and static-check dependencies before writing the bundle,
then hashes the launcher and records the binding in its manifest. Four focused
tests pass, including valid and invalid checks with the variable absent, a
system-only PATH, and paths containing spaces. Native worker integration remains
pending. Do not change the running pilot's pinned assets or contract.

The follow-up uses separate EvE application and optimizer groups, the original
G0 seed, and the unchanged Phase 10 stage-one evaluator. Its read-only worker
assets include a structural-check bundle assembled from a pinned LLMAO commit.
The bundle has an explicit source allowlist and per-file SHA-256 digests. It
contains the candidate schema, static type/expansion validators, and their
primitive definitions; it excludes evaluators, learners, data loaders, and
examples. Minimal package initializers avoid importing execution-only
convenience modules. Primitive source bytes remain unchanged so G0 identity
matches the authoritative validator.

Workers invoke the bundled checker with the project interpreter, isolated
Python imports, and bytecode writes disabled. They provide the selected
prefill's evaluator-owned lineage state. Checks consume their existing turn
and time allowance, return structural feedback only, and do not submit an
extra proposal. Immutable assets and other workspace files remain outside the
two-file edit allowlist. The final evaluator validates independently.

The follow-up worker guidance contains serialization and expansion rules but
imports no first-pilot macro, program, score trajectory, or population. Workers
compare final expanded hashes against examples from their own new run. A
repeated final submission still counts, and no evaluator replacement budget
is created.

`experiments/v4_check_candidate.py` checks a two-file candidate directory and
an optional evaluator-owned `--parent-state`. It reports content identities,
expanded depth/node count, feature dimension, used macros, and unused inherited
macros. It writes no files and computes no accuracy or learner fit. Exit status
is zero for valid structure and one for invalid structure. The authoritative
evaluator still controls accepted provenance and scored submissions.

`experiments/v4_replay_pilot.py` verifies the source digests, original protocol,
telemetry scores, candidate identities, canonical language chains, and accepted
parent states before replaying checks in temporary copies. The historical run
reproduces six valid and four invalid proposals, with three unique valid
expanded representations; all 59 source files verify. Sorting only attempt 6's
macro array in a separate temporary copy passes structural validation at depth
6. The original attempt remains invalid and receives no new score.

`experiments/v4_archive_lineage.py` performs the same verification before
producing language, primitive, candidate, and observation records plus a
Mermaid graph. The pilot archive has five language nodes including G0, four
edges, two valid macro behaviors, and 11 observations including the seed.
Repeated measurements and invalid attempts remain separate. Worker-entry IDs
are recorded; no independent-search declaration exists for this pilot, so
independent reuse is unknown. The CLI writes only new output paths.

The replay and archive are generated under `results/v4/phase10_pilot/` and stay
Git-ignored. Follow-up guidance/configuration is pinned at EvE
`01abaa5e33c3e0936d3fe2e250d071a746f71864`; the runtime checkout is LLMAO
`01f6371ded33537cb93c52b27303212db0c3a054`. The hashed launch contract is
`V4_FOLLOWUP_PILOT_CONTRACT.json`, with its digest in the adjacent `.sha256`.
The resolved configuration, original seed bytes, 21 checker bundle files, and
unchanged evaluation script verified before launch. Current run metadata is
stored separately under `results/v4/phase10_followup/`; the baseline
`environment.json` remains its historical snapshot. Primary discovery remains
pending final preregistration.

Example commands from the repository root (outputs must not already exist):

```bash
.venv/bin/python experiments/v4_check_candidate.py /path/to/candidate \
  --parent-state /path/to/evaluator/lineage_state.json
.venv/bin/python experiments/v4_replay_pilot.py \
  results/v4/phase10_pilot/manifest.json /tmp/v4-replay.json
.venv/bin/python experiments/v4_archive_lineage.py \
  --manifest results/v4/phase10_pilot/manifest.json \
  --output /tmp/v4-lineage.json --graph /tmp/v4-lineage.mmd
```

Validation: all 66 V4 unit tests passed, including read-only checks, malformed
parent states, artifact digest tampering, path escapes/symlinks, repeated score
preservation, forged parent rejection, and explicit independence declarations.
The 86 protected V3-family artifact digests remain unchanged.

The launch command is `experiments/v4_launch_followup.py`, with a new
`--record` path. `--validate-only` checks the frozen contract, source/file pins,
and clean evaluator/EvE checkouts without starting a worker. The supervisor records the owned runner
PID and terminal status, watches EvE forbidden-change artifacts and pinned
worker checker sources, and stops only its owned process group on a detected
boundary failure. This operational guard does not alter the EvE algorithm or
turn exploratory feedback into a primary result.
