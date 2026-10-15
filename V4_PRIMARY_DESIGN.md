# V4 primary study decisions

Status: **design fixed before primary discovery; implementation pins pending**.
This document resolves the scientific choices below. It does not authorize an
unvalidated primary launch or change either exploratory pilot. Bind these
choices, the common-program manifest, and the final implementation/configuration
digests into the canonical protocol before primary discovery. Preserve this
document and record any later change as a versioned amendment.

## Account and execution

Use the ChatGPT Plus plan (not Pro) and its ordinary Codex allowance. Run
`gpt-6-luna` with max reasoning through `codex_tmux`, one worker. Set EvE's
`driver.executable` to `scripts/codex-v4-sandbox`, which installs the named
`llmao-v4-workspace-only` permission profile. Deny external dataset reads,
undeclared writes, shell network access, `/tmp`, and `$TMPDIR`; reject legacy
sandbox settings that override the profile. Disable web search, multi-agent
mode, and the remote plugin catalog. Use an isolated Codex home without a
custom model provider. Require the automated sandbox preflight and native
fixture evidence described in `V4_SANDBOX_REPAIR.md`, then bind the final
sources, policy, and runtime into the contract before scientific launch.
Do not use Pro, paid credits, plan upgrades, or rate-limit resets.
Before each worker launch, verify the active plan is Plus and check its current
ordinary allowance; pause at the account limit instead of changing plans or
buying credits.

Use the same EvE workspace/example selection machinery and a cap of 32
read-only solver examples across conditions. Pin the selection code and
resolved context settings; do not change them between language conditions.
Each run starts with the same twenty initial ASTs and its own subsequent
evidence only. Fixed iterative conditions keep optimizer guidance immutable;
EvE conditions may evolve their own newly initialized guidance. Both share
the driver, evidence schema, context cap, learner, and resource counters.
During joint discovery, solver edits are limited to language/program JSON.
During frozen-language evaluation, solver edits are limited to program JSON;
the entire selected language is evaluator-owned and immutable.

Discovery seeds are `[1101, 1202, 1303, 1404, 1505]`. Fresh-search seeds are
`[101, 202, 303, 404, 505]`, independent of discovery. These identify optimizer
randomness and run identity; the fixed MNIST split and learner still use seed
42. Reuse each fresh-search seed across matched conditions for paired analysis.
Run each seed's six conditions in the listed order, rotated left by the seed's
zero-based index: G0/fixed, GH/fixed, G*/fixed, G0/EvE, GH/EvE, G*/EvE.
Execute workers serially. Record wall-clock dates and exact backend identifiers;
model or implementation changes require an amendment and prevent pooling
unmatched execution versions.

## Budgets and failures

Each discovery or fresh-search run targets **200 unique successfully evaluated
expanded ASTs**, including the twenty common starting ASTs and 180 adaptive
evaluations. `V4_INITIAL_PROGRAMS.json` fixes their order and canonical identity.
Every condition evaluates those base ASTs under its frozen language; no
discovered representation, guidance revision, example, or population is imported.

The adaptive proposal cap is **540**, including invalid, repeated, timed-out,
and failed proposals. Exact expanded-AST repeats do not advance the unique
evaluation budget, even when macro spelling or language identity differs.
Retain every proposal, its original score/failure, structural identity, tokens,
and timing. Do not replace an exhausted attempt cap with extra proposals.

Each run has a **500,000,000 total reported model-token cap**, counting input
plus output across solver and optimizer activity. Cached input remains part
of input; do not add cache-read tokens a second time. Record cache usage
separately. Seed evaluations consume no model tokens. All conditions use the
same cap and accounting. The token limit is a resource bound, not a promise
that a Plus allowance can execute the run continuously.

Each proposal receives at most **80 native turns and 3,600 seconds**. Zero
automatic boundary repairs. Structural checks consume the same allowance.
Evaluator subprocesses receive at most 1,800 seconds, with identical limits
across conditions. Track optimizer overhead, feature, learner, inference, and
active search time separately. Account waiting time is reported separately
from active execution time.

At an ordinary account limit, preserve durable state and pause launches until
ordinary allowance becomes available. Do not reset candidate, attempt, token,
or native-turn counters. Resuming an unfinished worker uses its remaining
allowance; a terminal timed-out or failed proposal remains a consumed attempt.
Boundary or official-test violations terminate the affected run immediately.
An exhausted proposal/token cap, terminal infrastructure failure, or missing
unique evaluation leaves the run **incomplete**, with its observed trajectory
retained. Do not extrapolate its final score or AUC to the full budget.

## Discovery objective and language selection

Keep the existing V3.2 stage-one score and learner unchanged. Define

```text
C(G) = number of invented macros in the complete language inventory
discovery_fitness = stage_one_fitness - 0.0005 * C(G)
```

The maximum eight-macro penalty is 0.004. Names, descriptions, and serialized
byte counts contribute no penalty. Retain body complexity, expanded program
size, unused inventory, and canonical bytes as separate diagnostics. This
simple cost rewards a smaller vocabulary without rewarding persuasive prose.
It applies only to joint discovery. Fresh-search fitness uses the unchanged
stage-one score in all frozen languages.

After all five discovery searches, select a language from a successfully
evaluated candidate containing at least one invented macro. Choose highest
discovery fitness; break exact ties by fewer macros, lexicographically smaller
canonical language hash, smaller canonical expanded-program hash, then smaller
discovery seed. Record the full eligible table and the selection calculation.
Use no fresh-search or official-test evidence in selection. If no eligible
language exists, report failed abstraction discovery; do not manufacture G*.

Freeze the complete selected language, including unused inherited macros,
names, descriptions, signatures, parameter ranges, and bodies. Freeze compiler,
evaluator, dataset indices, and all protocol/source hashes. Discard discovery
programs, histories, optimizer guidance, and populations before fresh search.
An incomplete discovery search prevents the planned complete discovery claim;
preserve its evidence and resolve completion under the original limits before
selecting the primary language.

## Candidate AUC and primary contrast

Let `b(n)` be the best unchanged stage-one fitness among the first `n` unique
successful evaluations. Integrate from **20 through 200**, after all common
starting ASTs have been evaluated. Use the left-endpoint step convention:

```text
candidate_AUC = sum(b(n) for n in range(20, 200)) / 180
```

Thus an improvement first found at evaluation 200 affects final fitness but
has no earlier search-efficiency credit. No min-max rescaling or baseline
subtraction within a run. Report the common starting best and final best
separately. Invalid attempts and duplicates appear in attempt/token/time curves.

For each fresh seed, compute G* minus G0 AUC within each optimizer. The primary
paired difference is the mean of those two optimizer contrasts for that seed.
Report all five paired differences, their mean, and each optimizer contrast.
Use an exact one-sided sign-flip test over the 32 assignments of the five
paired seed differences. The statistic is the mean difference; include equal
statistics in the tail, with no Monte Carlo approximation. Bootstrap the five
paired seed records 10,000 times with random seed 4204 and report a two-sided
95% percentile interval for the mean. The bootstrap unit is the paired seed
record containing both optimizer contrasts, not individual candidates.

Support for the primary language-efficiency claim requires all of:

- complete, matched runs for all five seeds and all six conditions;
- mean primary AUC gain at least **0.002**;
- exact one-sided p-value at most **0.05** and bootstrap lower bound above zero;
- positive mean G* minus G0 AUC in each optimizer;
- positive primary paired difference in at least four of five seeds;
- at least one evolved macro behavior used in an adaptive candidate in each
  of at least two independent fresh-search seeds, excluding starting ASTs;
  these candidates must have distinct expanded ASTs and fitness at least their
  respective common starting-set best;
- zero protected-boundary or official-test-access violations.

These criteria assess evidence; they are not instructions to keep searching
until significance. Failure of a criterion is a valid reported outcome. With
five seeds, uncertainty and coarse exact p-values must be stated explicitly.
No primary inference uses incomplete or unmatched pairs. GH comparisons,
optimizer interaction, semantic ablation, and transfer remain secondary and
must retain their complete planned conditions and datasets.

## Secondary metrics and studies

Reuse the exact frozen V3.2 stage-one thresholds from its pinned protocol:
V3 top-20 cutoff **0.549790923187964**, V2 best **0.7144794413214341**, and
V3 frozen-finalist floor **0.8556684108877517**. Preserve their source artifact
digests when binding the canonical protocol. Record first
unique evaluation, cumulative proposal count, cumulative tokens, and active
time reaching each threshold; non-reaching runs are right-censored at their
actual observed budget. These thresholds are descriptive and do not determine
language selection or the primary acceptance rule.

Token curves use cumulative input-plus-output tokens with cached input counted
once. For complete matched comparisons, integrate their best-so-far step curves
from zero through the smallest final cumulative token count in the matched
six-condition seed block; divide by that common bound. Publish that bound and
all six full trajectories. This token AUC is secondary; it measures an equal
observed token range and does not extend a run beyond its recorded consumption.

Semantic ablation uses the same five fresh-search seeds, both optimizers, and
the same budgets. Anonymize only macro names/descriptions, preserve parameter
contracts and behavior, and verify bit-identical outputs before launch.
Report paired semantic-minus-anonymous contrasts without changing primary
criteria after observation.

Transfer uses all four specified datasets: EMNIST Digits, EMNIST Letters,
KMNIST, and Fashion-MNIST. Freeze training-only splits and fingerprints before
search. Run G0 and the frozen MNIST G* with both optimizers and all five seeds
under the same budgets. Transfer the language only. Additional transfer-language
evolution is a separately marked exploratory analysis; it cannot alter the
frozen-language transfer comparison. GH human comparison and the optimizer
interaction use the full primary six-condition evidence.

## Remaining launch requirements

- Finish the ten-proposal follow-up and audit every original and additional gate.
- Demonstrate the interpreter-bound checker through native scientific worker tools.
- Integrate the tested pure `v4/objective.py` scoring function into a
  finalized-protocol discovery evaluator. Implement and verify budget counters, resume rules,
  frozen GH/G* compilation, analysis, and complete run manifests.
- Pin clean LLMAO and EvE checkouts, compiler/evaluator/context/worker sources,
  interpreter dependencies, and the common initial-program digest.
- Bind this design into the canonical protocol, remove resolved pending entries,
  hash the final protocol, and verify it before primary discovery.

Until these requirements pass, the canonical pilot protocol remains its
historical draft and no primary result has been produced.
