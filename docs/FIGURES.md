# Figures and conceptual diagrams

[Return to the research overview](../README.md)

## Figure 1. Representation as a hypothesis

![Handwritten variations, geometric structure, and rearranged stroke fragments](images/structural-priors.png)

Editorial illustration of an eight moving from handwritten appearance to a
geometric description and rearranged stroke fragments. This generated artwork
introduces the research idea; it is not an experimental observation.

## Figure 2. The sequence of studies

```mermaid
flowchart LR
    V1["V1<br/>Choose features"] --> V2["V2<br/>Write programs"]
    V2 --> V3["V3<br/>Express relations"]
    V3 --> V31["V3.1<br/>Challenge the bias"]
    V31 --> V32["V3.2<br/>Challenge the optimizer"]
```

Each stage addresses a question left open by the previous study. The sequence
separates representation design, evaluation of its assumptions, and attribution
of search outcomes to the optimizer.

## Figure 3. The experimental architecture

```mermaid
flowchart TD
    H[Hypothesis and mechanism] --> P[Typed representation proposal]
    P --> V[Static validation and compilation]
    V --> E[Local train and validation evaluator]
    E --> A[Evidence and quality-diversity archive]
    A --> H
    A --> F[Freeze selected programs and provenance]
    F --> C[Mechanism and nuisance interventions]
    F --> T[Transfer and learner comparisons]
    F --> B[Complementarity and robustness]
    O[Matched optimizer alternatives] --> P
```

Only training and validation evidence enters the proposal loop. Selected
representations are frozen before external tests. The matched optimizer study
changes the proposal method while retaining a shared evaluation contract.

## Figure 4. A possible next experiment loop

```mermaid
flowchart LR
    Q["Two plausible explanations"] --> X["An experiment that separates them"]
    X --> D["Observed disagreement"]
    D --> R["Revise the representation<br/>and its explanation"]
    R --> Q
```

This diagram depicts a future direction: asking which intervention could
separate competing explanations. It does not describe a completed autonomous
experiment-design capability.

## Empirical figures

The following figures belong to the scientific reports, where their sampling
protocols and limitations are described.

- [V1 learning curves](../reports/scientific/V1_OPERATOR_COMPOSITION.md#predictive-performance).
- [V2 augmentation and transfer](../reports/scientific/V2_PROGRAM_SYNTHESIS.md#search-and-augmentation).
- [V3 mechanism and transfer](../reports/scientific/V3_RELATIONAL_PRIORS.md#predictive-performance-and-representation-diversity).
- [V3.1 learning curves](../reports/scientific/V3_1_BIAS_EVALUATION.md#sample-efficiency-and-learner-dependence).
- [V3.2 search curves](../reports/scientific/V3_2_OPTIMIZER_VALUE.md#search-quality-and-feedback).

### Figure provenance

V1, V2, and V3 overview figures are rendered directly from tables in the original
experimental reports by `experiments/plot_report_figures.py`. They use published
rounded values and do not recompute experimental results. The selected panels
are also embedded in README and the corresponding scientific reports.

V3.1 and V3.2 use the existing study figures. Their interpretation belongs to
the reports' frozen evaluation protocols. Different studies' axes and outcomes
should not be combined into one performance ranking.
