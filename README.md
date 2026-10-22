# LLMAO: LLM as biAs Optimizer

### Before a model learns, what have we already decided for it?

Linear regression begins with a strong assumption: the prediction can be
expressed as an additive, linear function of the chosen inputs. A kernel changes
what similarity means. A decision tree organizes the problem through successive
splits. A convolutional network reuses the same local filters across an image.
These choices shape what can be learned, and how much evidence learning needs.

Every learner carries an **inductive bias**: assumptions and preferences that
help it choose among explanations compatible with the training data. Some come
from the model family; others come from representation, regularization, or the
training procedure. Even a flexible neural network has them.

We usually make these choices ourselves. LLMAO asks whether a language model
can help propose them, and what an experiment would have to show before we
could trust its proposal.

![Handwritten variations, geometric structure, and rearranged stroke fragments](docs/images/structural-priors.png)

[Read the studies](reports/README.md) · [V4 exploratory release](reports/scientific/V4_EVOLVING_BIAS_LANGUAGE.md) · [Figures and diagrams](docs/FIGURES.md) · [Reproduce a version](docs/REPRODUCIBILITY.md)

**Version names:** V4 names one research study. Its primary protocol files use
IDs such as `v4-primary-11` and `v4-primary-14`. “Protocol revision 14” means a
revision within V4, not a separate V14 study or branch.

## The assumptions we bring to learning

Different models make different structures easy to express. The examples below
are useful starting points; their behavior also depends on the features,
constraints, and training choices we give them.

| Model or method | A bias it brings |
|---|---|
| Linear regression | Predictions are linear in the chosen features. Nonlinear structure must be expressed through those features. |
| Kernel methods | The kernel defines similarity and a feature space; regularization favors certain functions within that space. |
| SVM | Margin-based learning favors separating boundaries with a large margin, balanced against violations. A kernel SVM inherits the kernel's notion of similarity. |
| Decision trees | Successive splits express conditional rules. Standard axis-aligned trees partition the feature space into regions with constant predictions. |
| Neural networks | Architecture, parameter sharing, regularization, and optimization shape which functions are accessible and favored. Flexibility does not remove those preferences. |
| CNNs | Local connectivity and shared filters make recurring spatial patterns natural to learn. Convolution gives translation equivariance; invariance depends on further design choices. |
| RNNs | A shared state-update rule processes an ordered sequence. The representation of each step depends on the preceding state. |

The familiar question is which model to use. A deeper question is **which
assumptions the task deserves**. Locality is a useful starting point for images,
but it does not tell us whether a digit is best described by connectivity,
curvature, stroke order, or the location of a loop.

Two handwritten digits can differ in thousands of pixels and still mean the
same thing. A small change in where a curve closes can turn one digit into
another. Which differences should the learner preserve? Which should it ignore?
And how would we find out whether our answer is right?

## Why this project starts with representation

Representation gives us a manageable place to investigate those questions.
Keep a learner fixed and change what it sees. Its predictions then depend on
both the learner's existing bias and the assumptions encoded in the features.

For a linear classifier, for example, a representation can make a relation
available that was difficult to express in raw pixels. A graph exposes
connectivity. A sequence preserves order. A histogram keeps a distribution and
forgets where its events occurred. Each choice makes some distinctions easier
to learn and removes others.

A language model has encountered descriptions of curves, symmetry, strokes,
and shape. It may use that knowledge to propose what a representation should
preserve. We turn the proposal into a typed program and evaluate it locally.
This makes the assumption inspectable and gives us a way to intervene on the
structure it claims matters.

MNIST gives us a small, familiar setting in which to examine this process.
V4's preserved experiments explored frozen macros and their expanded
representations on one training-derived split. They did not complete the
planned primary campaign or establish transfer; the
[V4 report](reports/scientific/V4_EVOLVING_BIAS_LANGUAGE.md) states what the
evidence supports and what remains untested.

## 🔎 From inductive bias to our research question

> Can an LLM help us identify which assumptions a task rewards, express them as
> executable representations, and design evidence that challenges them?

The working question in this repository is narrower:

> Can LLM-guided program synthesis discover compact, relational, transferable
> structural priors?

A good score is a starting point. To interpret it, we ask:

- **Expression.** Can the LLM build a representation that was not supplied as a
  complete feature, or does it mostly recombine familiar summaries?
- **Mechanism.** If it says the location of a turn matters, does moving turns
  while preserving their distribution damage the representation as predicted?
- **Scope.** Does the benefit survive a different learner or a related dataset?
  Which transformations expose its assumptions?
- **Attribution.** Would another optimizer find comparable programs under the
  same budget? What changes when feedback or meaningful operator names disappear?

These questions distinguish a useful feature, an explanation supported by an
intervention, and evidence that the LLM helped find it. The studies below pursue
them separately. Proposing experiments is part of the longer-term vision;
the completed studies use bounded, predefined evaluation procedures.

## The story so far

```mermaid
flowchart LR
    V1["V1<br/>Choose features"] --> V2["V2<br/>Write programs"]
    V2 --> V3["V3<br/>Express relations"]
    V3 --> V31["V3.1<br/>Challenge the bias"]
    V31 --> V32["V3.2<br/>Challenge the optimizer"]
```

Each stage begins with something the previous experiment could not tell us.

### V1: Can the LLM choose useful biases?

The first experiment lets the LLM select and combine seven human-written feature
operators while keeping the classifier fixed. A raw-pixel and stroke-direction
composition improves over raw pixels, while HOG remains stronger.

This establishes useful composition within a supplied menu. It also reveals the
boundary of that approach: the LLM cannot express a representation outside the
operators we have already designed. See the [V1 report](reports/scientific/V1_OPERATOR_COMPOSITION.md).

![V1 learning curves for stroke-direction augmentation, raw pixels, and HOG](reports/figures/V1_LEARNING_CURVES.png)

**V1.** Official MNIST test accuracy after finalist selection. Error bars show
standard deviation over three runs; at 60,000 examples the training partition
is identical across runs. Stroke-direction features help, while HOG stays ahead.

### V2: Can the LLM write representation programs?

V2 replaces the feature menu with a typed expression language. Programs compose
atomic operations over images, skeleton graphs, paths, sequences, and vectors.
A discovery track excludes raw pixels; an augmentation track permits them.
A quality-diversity archive preserves alternatives across the search space.

This expands what the LLM can express, but the experiment exposes another
limitation. The descriptor places many programs in the same `hybrid` niche,
and successful finalists mostly summarize distributions. Sequence shuffling
leaves their predictions unchanged. Strong Fashion-MNIST transfer also prevents
a handwriting-specific interpretation. See the
[V2 report](reports/scientific/V2_PROGRAM_SYNTHESIS.md).

![V2 post-search pixel augmentation and frozen spatial-cycle transfer](reports/figures/V2_AUGMENTATION_TRANSFER.png)

**V2.** Left: post-search compositions on the same validation split used for
selection, not independently tested LLM discoveries. Right: the frozen 25D
spatial-cycle representation, trained with 5,000 examples and evaluated on
2,000 official-test images per domain; bars show means and error bars show
standard deviations over three training seeds. Fashion-MNIST performance
limits a handwriting-specific interpretation.

### V3: Can the programs express useful relations?

V3 describes programs along five behavioral axes: source, order, spatial scope,
composition, and complexity. A small set of relational primitives makes spatial
conditioning, joint distributions, and relative quantities expressible.
Mechanism-balanced proposals help explore more than global histograms.

The search finds compact spatial representations, including a program relating
regional angle and centroid summaries. Targeted counterfactuals and spatial
ablations support the importance of event location. The finalists still remain
orderless, and their transfer is strongest on EMNIST Digits; KMNIST and
Fashion-MNIST expose substantial limits. Evidence supports a useful digit-domain
spatial prior, with the exact subtraction mechanism still unresolved. See the
[V3 evidence report](reports/scientific/V3_RELATIONAL_PRIORS.md), with the
[pilot](reports/V3_PILOT.md) and [search record](reports/V3_SEARCH.md).

![V3 event-location intervention and transfer relative to zoning and HOG](reports/figures/V3_MECHANISM_TRANSFER.png)

**V3.** Left: reassigning stroke-event locations while preserving the marginal
values substantially reduces accuracy on 2,000 held-out MNIST images. Right:
transfer at 5,000 training examples. Green intervals span the five finalists'
mean accuracies, not confidence intervals. The benefit is strongest on EMNIST
Digits; HOG remains stronger across domains.

### V3.1: What does a frozen bias actually contribute?

V3.1 freezes the V3 finalists and evaluates them across representation, learner,
training size, and domain. Dimension-matched HOG-PCA, learning curves,
complementarity, nuisance controls, and robustness tests make the comparison
more demanding.

The representations beat simple zoning but trail HOG-PCA at the same width.
They add predictive signal when combined with HOG under the fixed linear probe.
Sensitivity to erosion and vertical translation, alongside uneven transfer,
shows how specific their assumptions are. A bias therefore has an empirical
profile tied to its learner and domain, rather than one universal quality score.
See the [V3.1 evaluation report](reports/scientific/V3_1_BIAS_EVALUATION.md).

![V3.1 learning curves across frozen representations and classifiers](reports/V3_1_LEARNING_CURVES.png)

**V3.1.** The frozen evaluation compares representations under several learners
and training sizes. V3 beats simple zoning but trails dimension-matched HOG-PCA.
See the report for paired uncertainty estimates and complementarity results.

### V3.2: What did the LLM contribute to search?

A useful program does not establish that an LLM was necessary to find it.
V3.2 holds the typed program space, evaluator, shared seeds, and candidate budget
fixed while comparing typed random search, genetic programming, one-shot LLM
proposals, and iterative LLM search with feedback.

The matched primary analysis uses two seeds per optimizer. Iterative LLM search
finishes above one-shot proposals and slightly above genetic programming in
those paired runs. Typed random search reaches the hard proposal cap before
completing either run, so a full-budget random comparison is unavailable.
A separate three-seed lexical-semantic ablation favors meaningful operator
names over anonymized names; it isolates lexical cues only, and does not remove
all pretrained knowledge.

These observations support a bounded role for semantics and feedback in this
search space. The small matched sample and censored runs limit broader claims
about optimizer superiority or scientific discovery. See the
[V3.2 optimizer study](reports/scientific/V3_2_OPTIMIZER_VALUE.md).

![V3.2 search curves and diagnostics for matched optimizers](reports/V3_2_SEARCH_CURVES.png)

**V3.2.** Matched optimizer runs under a shared candidate-evaluation budget.
Shading is the observed min-to-max range, not a confidence interval. The primary
analysis uses two seeds per optimizer; random runs stop before 200 evaluations
and remain censored. Fitness includes complexity and runtime penalties.

## Conceptual architecture

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

The LLM supplies hypotheses and programs. The typed language limits execution
to approved primitives, and the evaluator assigns every score. Invalid programs
are rejected before evaluation. During discovery, train and validation evidence
feeds the archive and subsequent proposals; external tests follow finalist
freezing and do not feed back into candidate editing.

V3.1 evaluates the frozen representations. V3.2 changes the proposal strategy
under a shared search contract, then characterizes preselected winners after
search. These boundaries keep representation quality, mechanism evidence, and
optimizer value as separately answerable questions.

The detailed design is in
[ARCHITECTURE.md](ARCHITECTURE.md), with the original
[V1 architecture](ARCHITECTURE_V1.md) retained. The historical
[search plan](PLAN.md) and [V3.1 protocol](V3_1_PROTOCOL.md) document the study
boundaries.

## What the evidence leaves us with

The progression demonstrates that a bounded program language can turn LLM
proposals into compact, inspectable representations with measurable predictive
value. Spatial relationships matter for the selected digit tasks, and some
representations provide signal complementary to a strong handcrafted baseline.

The evidence also narrows the claim. Distributional summaries remain dominant;
compactness does not imply superiority over equally compact controls; transfer
is domain-dependent; and optimizer comparisons depend on completed budgets and
replication. The experiments do not establish a universal handwriting prior,
general LLM optimizer superiority, or autonomous scientific discovery.

One lesson recurs across the studies: a representation can be useful for reasons
that are narrower than its original explanation. Spatial summaries help on digit
tasks, yet a broad account of handwriting does not survive every transfer test.
A good search result still needs controls before we can credit the optimizer.

Detailed scores, benchmark tables, protocols, and limitations live in the version
reports.

## 🧭 Where this could lead

The longer-term ambition is to let a system propose both a representation and
the experiment that would distinguish its explanation from a competing one.

Suppose two programs perform equally well. One explanation says that digits
are identified by how often a stroke turns; another says that where those turns
occur is essential. More search for accuracy may leave them tied. An intervention
that preserves the turn distribution while reassigning locations can tell us
something a leaderboard cannot.

```mermaid
flowchart LR
    Q["Two plausible explanations"] --> X["An experiment that separates them"]
    X --> D["Observed disagreement"]
    D --> R["Revise the representation<br/>and its explanation"]
    R --> Q
```

That is a possible next research direction, beyond the completed studies here.
It would need a bounded experimental language, controls for what each
intervention changes, and a record of failed predictions. The system would also
need to recognize when its current vocabulary cannot express the distinction it
is trying to investigate.

There is a deeper constraint: we choose the primitives. They already contain
human assumptions about what might matter. A novel composition is therefore
novel within that language. Discovering when the language itself is inadequate
may be as valuable as finding its best program.

The vision is a collaborator that makes its assumptions available for inspection:
what it thinks matters, what observation would change its mind, and how far the
evidence allows its conclusion to travel. This repository is an early experiment
in building that discipline.

## 📚 Preserved versions and reading guide

`main` integrates the full sequence. Historical branches and commits retain the
implementation at each stage. The scientific reports present the findings;
the original experimental records retain full tables and frozen provenance.

| Stage | Historical source | Report |
|---|---|---|
| V1: operator composition | `1037c5b` | [Final report](reports/scientific/V1_OPERATOR_COMPOSITION.md) |
| V2: typed synthesis | `v2-program-bias-search` / `c6d3f85` (tag `v2-final`) | [Program synthesis](reports/scientific/V2_PROGRAM_SYNTHESIS.md) |
| V3: relational search | `v3-relational-bias-search` / `1e9f29b` | [Evidence](reports/scientific/V3_RELATIONAL_PRIORS.md) |
| V3.1: frozen bias evaluation | `v3.1-bias-evaluation` / `798415c` | [Bias evaluation](reports/scientific/V3_1_BIAS_EVALUATION.md) |
| V3.2: optimizer value | `v3.2-optimizer-value-study` / `85beeaf` | [Optimizer study](reports/scientific/V3_2_OPTIMIZER_VALUE.md) |

For setup and historical execution commands, see
[Development and reproduction](docs/REPRODUCIBILITY.md). Research reports record
which evidence is completed, validation-only, post-freeze, or censored. Generated
artifacts are generally local; the explicitly tracked protocols and study traces
provide the durable record included in the repository.
