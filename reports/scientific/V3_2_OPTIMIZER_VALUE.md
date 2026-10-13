# V3.2. Measuring the contribution of the LLM to representation search

## Abstract

V3.2 separates the usefulness of a representation from the contribution of
the method used to find it. Four optimizers searched the same bounded program
space under a shared candidate-evaluation budget. The matched primary analysis
used two seeds per optimizer; six of eight runs completed 200 evaluations.
Iterative LLM search obtained a mean best fitness of 0.8587, compared with
0.8557 for genetic programming and 0.8306 for LLM proposals without feedback.
Random search did not complete either matched run. A separate three-seed
ablation favored meaningful operator names over anonymized names. These
findings suggest a role for feedback and lexical semantics within this setting,
while incomplete runs, small replication, and proposal cost restrict the claim.

## Research question

A good representation found by an LLM does not establish that the LLM was
necessary to find it. We asked whether language-guided proposals improved
search over conventional methods, and whether empirical feedback and meaningful
operation names contributed to that behavior.

## Methods

Typed random search, genetic programming, LLM proposals without evaluator
feedback, and iterative LLM search with feedback used the same V3 representation
language. Programs were limited to 128 features and expression depth six;
raw-pixel representations were excluded. Each optimizer began with the same
20 programs and was assigned 180 additional unique candidate evaluations.

Each candidate used the same 500-example MNIST training subset, validation
partition, and fixed classifier. Fitness was validation accuracy minus small
logarithmic penalties for feature dimension and runtime. Fitness is therefore
not identical to accuracy. Transfer, robustness, and later classifier comparisons
did not enter search or winner selection. The official test partition was
excluded from search.

Invalid and duplicate proposals counted toward overhead rather than the unique
evaluation budget. A hard limit of 540 proposal attempts applied to each run.
The protocol planned five seeds, but local LLM throughput led to a recorded
execution fallback. The primary comparison was restricted to matched seeds
101 and 202. Additional completed or partial runs were retained outside this
matched analysis; they were not silently pooled into its estimates.

A separate lexical-semantic ablation used three paired seeds. It changed
operator names while retaining mathematical behavior, types, signatures, and
parameter constraints. Preselected optimizer winners were subsequently frozen
and characterized using the V3.1 evaluation approach.

## Results

### Search quality and feedback

![Search trajectories and diagnostics for the matched optimizer study](../V3_2_SEARCH_CURVES.png)

**Figure 1.** Best-so-far search trajectories and optimizer diagnostics. Curves
are shown only over the candidate range reached by every included run for that
optimizer. Shading is the observed minimum-to-maximum range, not a confidence
interval. Incomplete runs are marked at their last observed evaluation.

| Search method | Completed matched runs | Mean best fitness at 200 evaluations |
|---|---:|---:|
| Iterative LLM | 2 of 2 | 0.8587 |
| Genetic programming | 2 of 2 | 0.8557 |
| LLM without feedback | 2 of 2 | 0.8306 |
| Typed random search | 0 of 2 | Not estimable |

Iterative LLM search exceeded genetic programming by a mean paired fitness
difference of 0.0029 and exceeded the no-feedback LLM by 0.0280. Both
comparisons favored iterative search in both seeds. With only two pairs,
bootstrap intervals and win counts remain descriptive and provide limited
information about replication beyond these runs.

Genetic programming had a higher mean fitness among its five best candidates
than iterative LLM search, by 0.0143. The search methods therefore differ
according to whether quality is assessed by the single best candidate or by
the strength of several alternatives.

### Incomplete random search and threshold attainment

The random runs stopped at 184 and 183 evaluations. Their last best fitness
values were 0.8048 and 0.8312. These are censored observations, not estimates
at 200 evaluations and not full-budget threshold failures.

Random search reached the V3 top-20 cutoff after 22 and 26 evaluations;
iterative LLM search did so after 27 and 29. The stricter frozen-finalist floor
was reached by iterative search in both runs, after 29 and 48 evaluations,
but not by random search before it stopped. Apparent efficiency therefore
depends on the threshold, and a complete-budget random comparison is unavailable.

### Lexical-semantic ablation

Meaningful operation names yielded mean final fitness 0.8585, compared with
0.6129 under anonymization. The mean paired difference was 0.2456, favoring
meaningful names in all three seeds. Its paired bootstrap interval was
0.2221 to 0.2859, conditional on these three observations.

The intervention removes lexical cues within the preserved program contract.
It does not remove all pretrained knowledge or establish that language semantics
are the only source of the difference.

### Cost and post-search characterization

Mean total runtime was approximately 49.93 minutes per iterative LLM run,
20.90 minutes without feedback, and 1.67 minutes for genetic programming.
Random runs took 1.02 minutes on average but were incomplete. These timings
describe the local execution conditions and actual work performed; they are
not a matched wall-clock-budget comparison.

The selected genetic-programming and iterative-LLM winners had similar mean
linear accuracies, 86.02% and 86.03%, and each added 1.07 percentage points
when combined with HOG under the reported linear comparison. Thus, the small
search-fitness advantage did not produce a large difference in their later
representation profiles. Characterization results were not fed back into search.

## Discussion

Feedback-guided proposals reached a stronger best candidate than proposals
without feedback in the matched runs. The advantage over genetic programming
was much smaller, and genetic programming retained stronger top-five alternatives
at much lower local proposal cost. No single ranking captures all these outcomes.

The naming ablation suggests that meaningful descriptions of operations help
the LLM navigate this program space. The conclusion remains tied to the tested
language, prompt, model, task, and sampling rules. Conventional optimizers also
encode choices about how to sample or mutate programs.

## Limitations and conclusion

The primary study uses two matched seeds rather than the planned five, and
random search has no complete matched run. The lexical ablation has three pairs.
These sample sizes limit inference. The evaluator is a fixed low-data proxy;
its fitness should not be interpreted as general representation quality.

V3.2 provides bounded evidence for the value of feedback and lexical semantics
in the tested search setting. It does not establish general LLM optimizer
superiority, a complete-budget advantage over random search, or autonomous
scientific discovery.

## Supplementary record

The [original study record](../V3_2_OPTIMIZER_VALUE.md) retains all seed-level
scores, intervals, proposal costs, threshold outcomes, incomplete-run statuses,
and winner profiles. The [execution manifest](../../results/v32/manifest.json)
documents the matched subset and retained observations.
