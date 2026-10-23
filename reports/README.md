# Research reports

These reports present the studies as a sequence of scientific questions.
Each separates methods, results, interpretation, and limitations. They summarize
preserved evidence; this layout update did not rerun any experiment.

| Study | Question | Scientific report |
|---|---|---|
| V1 | Can the LLM select useful features under a fixed learner? | [Operator composition](v1/V1_OPERATOR_COMPOSITION.md) |
| V2 | Can it compose compact representation programs? | [Program synthesis](v2/V2_PROGRAM_SYNTHESIS.md) |
| V3 | Do spatial relations provide a useful structural prior? | [Relational priors](v3/V3_RELATIONAL_PRIORS.md) |
| V3.1 | Where does the frozen representation help or fail? | [Bias evaluation](v3.1/V3_1_BIAS_EVALUATION.md) |
| V3.2 | What does the LLM contribute to the search procedure? | [Optimizer value](v3.2/V3_2_OPTIMIZER_VALUE.md) |
| V4 | What emerges when the representation language can evolve, and has its reuse been tested? | [Evolving bias language](v4/V4_EVOLVING_BIAS_LANGUAGE.md) |

Naming: V4 is the study. IDs such as `v4-primary-14` identify a primary-protocol
revision within that study, not a separate research version.

## Reading the evidence across versions

V1 reports independent MNIST test results after selection. V2 and V3 search
scores are validation results, with external tests and interventions conducted
after freezing. V3.1 evaluates a fixed representation set; V3.2 compares search
procedures using a penalized validation objective. These quantities answer
different questions and should not form a single accuracy leaderboard.

The sequence supports useful feature composition, compact spatial representations,
and some complementarity with HOG. It also exposes domain-limited transfer,
weaknesses against dimension-matched HOG-PCA, and limited replication in the
optimizer study. Findings should be read together with those qualifications.
V4's spotlight is two partial discovery trajectories with distinct spatial and
skeleton abstraction inventories and best recorded discovery fitness near
0.91. E1–E4 then distinguish targeted expression, selected expanded-program
quality, and observed adoption in a separate frozen pilot language. The
primary campaign did not complete, so the study closes as exploratory without
a causal abstraction-utility, search-efficiency, or generalization claim.

## Figures

Conceptual illustrations and diagrams are in [Figures](../docs/FIGURES.md).
Empirical learning and search curves appear in the corresponding scientific
reports with captions and interpretation.

## Supplementary experimental records

Version-specific reports and figures now live together under `reports/vN/`.
The root index remains the entry point. Detailed records retain their tables
and findings; current local links follow the new organization.

- [V1 full record](v1/FINAL_REPORT.md).
- [V2 full record](v2/V2_PROGRAM_SYNTHESIS_FULL.md).
- [V3 pilot](v3/V3_PILOT.md), [search](v3/V3_SEARCH.md), and [evidence](v3/V3_EVIDENCE.md).
- [V3.1 full evaluation](v3.1/V3_1_BIAS_EVALUATION_FULL.md).
- [V3.2 full optimizer study](v3.2/V3_2_OPTIMIZER_VALUE_FULL.md).
- [V4 exploratory report and evidence manifest](v4/V4_EVOLVING_BIAS_LANGUAGE.md).

Historical implementations remain identified in the
[version guide](../README.md), and execution instructions are in
[Reproducibility](../docs/REPRODUCIBILITY.md). See the
[document layout guide](../docs/VERSIONED_RESEARCH.md) for the directory map and
hash audit.
