# V4 artifact storage architecture

Status: the shared path resolver, schema-v2 contract support, repo-local
fixture scratch, and local-cache sandbox probe are implemented. The V4 primary
protocol revision 13 passed its 22-check sandbox preflight, data-free native
fixture, and five contract gates. Its first seed-1101 adaptive proposal
exposed a stale Phase 2 adapter guard that rejected the protocol-pinned cache
inside the checkout. The run is preserved as incomplete with no adaptive
candidate score. The cache guard was updated before freezing primary-protocol
revision 14. Its partial discovery trajectories remain incomplete; see the
[V4 closure report](../reports/v4/V4_EVOLVING_BIAS_LANGUAGE.md). Existing
historical protocols, contracts, fixture evidence, and run directories keep
their current paths.

## Decision

`<LLMAO checkout>/results/v4/` is the single writable root for persistent V4
outputs, recoverable scratch, and V4-managed dataset caches. Every runner,
fixture, evaluator, collector, and report builder derives its output paths from
this root and records paths relative to it. A V4 command must reject an output
path that resolves outside this root, including a path that escapes through a
symlink.

The EvE checkout and user-managed credentials remain external read-only
dependencies. Store the MNIST cache under `results/v4/cache/datasets/mnist_784/`
and permit only the evaluator process to read it. The Codex worker sandbox must
continue to deny the cache path even though it is under the repository root;
the data-free preflight must verify this before a new run.

## Audit findings

The primary Phase 12 runner already sends its persistent run data to
`results/v4/phase12/runs/`: checkpoints, state snapshots, trajectory records,
SQLite lineage databases, EvE artifacts, solver/evaluation workspaces, and
Codex driver homes/transcripts all derive from the contract's `run_root`.
Current v10 contracts and those run roots are therefore already inside the
LLMAO checkout.

Two external persistent V4-owned directories come from data-free fixture
entry points. The v10 data cache is also external because its old contracts
pin that location:

| Current path | Contents and source | Target |
| --- | --- | --- |
| `~/Library/Caches/llmao-v4-native-check-fixtures/` | Historical synthetic checker workspaces and sandbox probes. | Preserved in place. New fixture workspaces go under `results/v4/scratch/native-check-fixtures/`; evidence remains under `results/v4/.../evidence/`. |
| `~/Library/Caches/llmao-v4-eve-lineage-fixtures/` | Historical EvE fixture runs, including workspaces, DBs, artifacts, and problem cache. | Preserved in place. New fixture runs go under `results/v4/scratch/eve-lineage-fixtures/`; evidence remains under `results/v4/.../evidence/`. |
| `~/Library/Caches/llmao-v4-phase12-mnist/` | Raw MNIST cache recorded by the Phase 12 v10 contracts. | Preserve for those historical contracts. New contracts use `results/v4/cache/datasets/mnist_784/`; workers must be denied reads from it. |
| `../eve/` and `../eve/.venv/` | Separate EvE source checkout and runtime, pinned by commit and environment metadata. | Keep separate from LLMAO outputs; runners may read them but must direct all run writes to `results/v4/`. |

Several V4 command-line tools also accept arbitrary `--output` or positional
output paths. Their defaults or documented invocations may be repository-local,
but the implementation does not consistently enforce that boundary. New
contracts must close this path escape so a typo or absolute path cannot create
V4 output elsewhere.

## Target layout

Keep the existing top-level historical protocol files and legacy phase
directories in place. New contracts use this protocol-scoped layout:

```text
results/v4/
├── protocol.json                         # historical protocol; preserve
├── primary_protocol.json                 # frozen protocol; preserve
├── cache/
│   └── datasets/mnist_784/                # ignored; evaluator-only
├── phase12/
│   ├── contracts/<protocol-id>/<seed>.json
│   ├── evidence/<contract-id>/           # immutable preflight and fixture evidence
│   ├── runs/<protocol-id>/<seed>/        # one complete, resumable run root
│   │   ├── checkpoints/
│   │   ├── artifacts/
│   │   ├── solver_workspaces/<attempt>/
│   │   │   ├── .codex-driver-home/
│   │   │   └── .codex-driver-transcripts/
│   │   ├── evaluation_workspaces/
│   │   └── run_manifest.json
│   ├── collections/<protocol-id>/
│   ├── analysis/<protocol-id>/
│   └── reports/<protocol-id>/
├── fixtures/<fixture-id>/                 # data-free fixture evidence
└── scratch/<operation-id>/                # disposable, still repo-local
```

All directories below `results/v4/` remain ignored by Git except the existing
explicitly tracked source-of-truth files. A run manifest and hashes provide
integrity; Git tracking is not the storage or completion signal for run data.

## Path and ownership rules

1. A shared V4 path module owns the resolved checkout root and artifact root.
   Writers receive logical paths relative to `results/v4/`, create parents only
   after validating containment, and reject symlink escapes. No V4 writer uses
   the process working directory or `$HOME` as an implicit output root.
2. Every run component—EvE `run_root`, both lineage DBs, artifact store,
   workspaces, evaluator logs, temporary runtime homes, and transcripts—must be
   a descendant of one contract-pinned run root. The contract stores
   repo-relative paths plus the protocol and source digests.
3. Every persistent output manifest stores repo-relative paths, hashes, sizes,
   and the storage-layout version. Machine-specific absolute paths are recorded
   only for external inputs/runtime identity where needed to reproduce the
   environment.
4. Fixture scratch lives under `results/v4/scratch/<operation-id>/`. On
   success, verify and write the evidence manifest before removing scratch. On
   failure, retain scratch under the same root and mark it incomplete. Never
   clean a path that is not owned by the current operation.
5. The worker's writable surface remains its declared candidate files. Moving
   scratch under the repository does not widen the worker sandbox: sibling
   paths, run manifests, source, and evidence stay denied to the worker.
6. External read-only exceptions are the pinned EvE checkout/runtime and
   user-managed Codex auth source. The MNIST cache is inside `results/v4/`,
   outside the worker workspace, and denied by the worker permission profile.
   Keep the isolated Codex home and transcripts inside each attempt workspace,
   where the current wrapper expects them. Credentials are symlinked from their
   user-managed location and are never copied into manifests or evidence.
7. Set the V4 process temporary/cache environment under its run or operation
   scratch root where supported. Any temporary output needed for recovery or
   audit must use the repo-local scratch directory.

## Contract and migration boundary

The next storage implementation gets a new contract schema version and a new
protocol/contract identity. It must pin the path resolver, storage-layout
version, all configured roots, and the output-boundary preflight. It must not
reuse an old run root after changing a writer or path rule.

The existing v10 contracts are schema v1 and bind the old code commit and
absolute run paths. Their five run-state files still say `running`, have no
final run manifest, and no runner/tmux process is currently present. Treat them
as incomplete evidence. Keep every v10 artifact at its current path. Do not
move cache contents, synthesize a completion manifest, collect the runs, or
resume them under the new layout. If the old runs are resumed, they must use
their original frozen code and contract at the recorded checkout path; new
contracts follow the new layout.

Implementation should proceed in this order:

1. Apply the shared path resolver to every V4 writer and path-taking CLI.
   Branch data-path validation by protocol version in both the Phase 2 adapter
   and evaluator: keep v10's external-cache rule intact and require layout v2
   contracts to use the one repo-local cache path, outside the worker workspace.
2. Move future native fixture workspaces from the two home-cache roots into
   repo-local scratch; preserve all existing external fixture directories as
   historical evidence.
3. Build the protocol-pinned checker bundle and run the data-free path and
   sandbox preflights. Verify that outputs and the MNIST cache land under
   `results/v4/`, symlink escapes and out-of-root output
   arguments fail, candidate workers cannot read the cache or write outside
   their declared files, and failure scratch remains recoverable.
4. Freeze a new contract schema with relative output paths and the storage
   layout version, using the hashed preflight and fixture evidence.
5. Only then launch any new primary run with a fresh protocol-scoped root.

The v10 MNIST cache remains untouched for its old contracts. New runs create or
reuse the repository-local cache only after the sandbox has demonstrated that
candidate workers cannot read it. The separate EvE checkout is not part of this
migration.
