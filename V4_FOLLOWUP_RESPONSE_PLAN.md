# V4 follow-up pilot failure response

The ten-proposal follow-up ended normally on 2026-10-14 at 12:17:29 UTC.
Its scientific gate **failed**. Preserve its original contract, every candidate,
the two failed proposals, all scores, telemetry, and native transcripts. No
proposal is repaired, replaced, or counted as discovery evidence.

## Evidence driving the response

- Eight proposals had valid stage-one scores and eight distinct expanded ASTs.
- Four macro behaviors were introduced and used by their introducing valid
  candidates. None was used by a descendant. Proposal ten retained an unused
  `spatial_stroke_profile` inherited from proposal eight.
- Proposal one used an invalid open parameter schema. Proposal nine supplied
  the wrong input type to an operation requiring a Vector.
- All 32 direct native checker invocation attempts failed before structured
  feedback. The approved variable was absent; alternative interpreters lacked
  dependencies or language support. Host replay success cannot substitute for
  a successful scientific-worker tool invocation.
- Worker three created a temporary virtual environment and package symlinks
  outside the two candidate files. Its `rm -rf` cleanup request was rejected by
  automatic approval review because that command style was disallowed; the
  environment was later inventoried and moved into the ignored archive without
  changing its external symlink targets. Worker five's offline dependency
  attempt failed because `networkx` was unavailable; a later read-only check
  found its named cache directory absent. Worker nine used a temporary file
  outside the workspace for candidate edits. These are deviations from the
  declared edit boundary.
- Workspace diff and immutable-bundle monitoring did not detect host temporary
  writes. The run did not stop at the first deviation. Native transcripts must
  therefore supplement the supervisor's file checks; absence of a forbidden
  workspace diff is insufficient evidence of complete boundary compliance.

## Required implementation and configuration work

1. Use the existing interpreter-bound `run_check.sh` bundle in a separate,
   data-free native-worker integration fixture. Pin the absolute project Python
   entrypoint for dependency validation, then invoke its resolved runtime with
   explicit venv site-packages to avoid blocked macOS symlink traversal. Record
   both identities. Demonstrate valid and invalid feedback without an inherited
   interpreter variable. No extra scientific score or pilot proposal is
   permitted in this fixture.
2. Give workers an explicit failure rule: if the pinned checker cannot run,
   report the infrastructure failure and submit under the original budget.
   Never create a virtual environment, install dependencies, search outside
   the supplied workspace for interpreters, or modify unrelated files.
3. Launch the isolated native Codex worker through
   `scripts/codex-v4-sandbox` with its named workspace-only permission profile.
   Reject mixed legacy sandbox configuration and CLI policy overrides. Deny
   shell network access, external dataset reads, and temporary writes; disable
   web search, multi-agent mode, hooks, and the remote plugin catalog in the
   fixture. The automated no-model preflight must pass before the native
   fixture creates a worker. Verify the native tool path and audit transcripts
   as well as file effects. The `20261015-native-boundary-04` data-free fixture
   passed both gates; see `V4_SANDBOX_REPAIR.md`. Bind the launcher digest,
   policy, and verification evidence into the next contract before a new
   scientific pilot; config alone is insufficient enforcement evidence.
4. Clarify type contracts, especially Scalar versus Vector arguments. Prefer
   the working structural checker over manually estimated dimensions/types.
5. Clarify inherited macro reuse: retain useful inherited calls when changing
   the surrounding representation. Do not inline an inherited abstraction
   merely to rename or rewrite an equivalent computation. Reuse must remain
   genuine program use, with no added dead calls to satisfy the gate.
6. Pin a new exploratory contract and fresh G0 initialization before another
   ten-proposal pilot. Keep the original validity, use, descendant, resource,
   boundary, and eight-distinct-representation gates, with no replacement budget
   or imported prior program, macros, guidance, or population.

Run any future pilot using the ChatGPT Plus plan (not Pro) and its ordinary
allowance. Verify the active plan and available usage before launch; pause at
the limit without upgrading or using paid credits.

Primary discovery remains closed until a pilot satisfies the gates and the
final primary implementation, configuration, and canonical protocol are frozen.
The predefined primary design remains in `V4_PRIMARY_DESIGN.md`; this response
does not change its budgets or scientific acceptance criteria.
