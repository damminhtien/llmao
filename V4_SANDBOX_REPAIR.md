# V4 checker and sandbox repair

This repair addresses the repeated checker/runtime failures and replaces manual
sandbox experiments with an automated launch gate. It adds no scientific score,
proposal, replacement budget, or primary-study result.

## Root causes

1. The checker needed project dependencies and Python 3.14, but workers did not
   inherit the proposed interpreter variable. Calling a different Python or
   creating another environment did not repair the pinned execution contract.
2. Under the strict macOS read policy, the venv interpreter symlink traversed a
   Homebrew alias that the sandbox denied. Direct execution of the resolved
   Python runtime, with the validated venv site-packages explicitly inserted,
   ran the checker successfully. The bundle now records the original venv
   entrypoint, resolved executable, package root, versions, and launcher hash.
3. The legacy workspace-write policy admitted external reads. Removing the
   root denial restored checker execution but also admitted the outside-read
   canary. That configuration was rejected. A workspace `sandbox_mode` setting
   also conflicted with named permissions and has been removed from the fixture.
4. Hand-written shell variants mixed runtime, policy, path, and quoting changes.
   Their aggregate shell status could hide failed intermediate checks. Parsed
   configuration and a clean Git diff did not prove OS enforcement.

The initial native timeout remains an observed timeout; the remote plugin
catalog has not been established as its cause.

## Implemented boundary and launch gate

`scripts/codex-v4-sandbox` installs `llmao-v4-workspace-only` only in EvE's
isolated Codex home. It removes the driver's legacy workspace-write argument,
rejects mixed project configuration and policy-changing CLI options, and
permits only the supported driver options. The profile grants:

- read access to the workspace, minimal system runtime, project venv, and
  resolved Python runtime directory;
- write access to `candidate/{language,program}.json` and
  `solver/candidate/{language,program}.json` only;
- no shell network access or temporary-root exceptions.

The fixture disables hooks, web search, multi-agent mode, and the remote plugin
catalog. Hooks are not used as enforcement evidence. EvE's core is unchanged.

`experiments/v4_sandbox_preflight.py` executes a deterministic probe through
`codex sandbox`, without model calls or authentication. It verifies valid and
invalid checker JSON/exit codes, all four permitted writes, immutable checker,
protocol/config/candidate paths, denied external read/write, both temporary
roots, and a connection attempt to a live local listener. A complete probe
report, successful process status, unchanged hashes, and absence of probe files
are all required. Setup errors, missing JSON, and empty reports fail closed.
Evidence includes CLI version, exact command, stdout/stderr, and bundle,
wrapper, and isolated-config digests. Existing candidate probe paths are never
overwritten. Only fixture-owned canaries are cleaned up.

`experiments/v4_native_check_fixture.py` runs this gate before creating tmux or
starting a model. It does not read or revalidate Plus account usage. Native tool
outputs, transcripts, candidate hashes, bundle inventory, and Git status
provide separate postconditions. An automated regression test ensures a failed
preflight prevents worker creation.

## Reproduce the no-model preflight

Run from the repository root using the project environment. Each attempt needs
new workspace and evidence paths; failed attempts are preserved for inspection.

```sh
run_id="sandbox-$(date -u +%Y%m%dT%H%M%SZ)"
.venv/bin/python -m experiments.v4_sandbox_preflight \
  --run-id "$run_id" \
  --workspace "$HOME/Library/Caches/llmao-v4-native-check-fixtures/$run_id" \
  --evidence "results/v4/phase10_followup/native_worker_integration/$run_id.json"
```

The native fixture does not require a usage snapshot. Run
`python -m experiments.v4_native_check_fixture --help` for its arguments. The
fixture remains data-free and does not authorize a scientific launch.

## Verification on 2026-10-15

- All 41 focused checker, wrapper, preflight, native-fixture, and evaluator
  tests pass.
- Ruff and `git diff --check` pass.
- All 86 protected baseline artifact hashes remain unchanged.
- The automated preflight passes all 21 conditions, including real OS denials.
- `20261015-native-boundary-03` passes all 15 native postconditions. The final
  argument-validation hardening is checked again in `native-boundary-04`.
- `native-boundary-02` remains evidence for the earlier legacy policy's temporary
  write denials only. It does not establish the repaired read boundary.

Final native evidence digests (SHA-256):

| Artifact in `20261015-native-boundary-04/` | SHA-256 |
| --- | --- |
| `result.json` | `c1e7c9046f0c454a7394a1dc9943db5da9e08feec0efce3edb57727769353144` |
| `sandbox_preflight.json` | `c1b56c522cd53896ac7c1e8ada30b6f0197c4ffc4eef96da57ca468f1abde4df` |
| `native_transcript.jsonl` | `97c34f46e38c9e194a4a1d201c935ec97fe31165be94d3dce7abe9b3e9b0c893` |

Full local evidence is retained under the ignored directory
`results/v4/phase10_followup/native_worker_integration/`. Authentication files
are not part of the evidence or this commit.

## Remaining scientific gates

Bind final launcher/runtime/profile/source digests and this verification into a
new contract before another pilot. Worker enforcement across that complete
pilot, lineage reuse, the remaining preregistration decisions, discovery,
primary evaluation, and scientific reporting retain their TODO status. Neither
the failed pilot nor frozen V3/V3.1/V3.2 evidence is reclassified by this repair.
