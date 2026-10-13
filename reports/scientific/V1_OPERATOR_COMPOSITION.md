# V1. Selecting useful inductive biases for handwritten digits

## Abstract

This study asks whether a language model can select a useful image
representation from a small set of human-designed features. Under a fixed
linear classifier, the selected combination of raw pixels and stroke direction
reached 86.41% mean MNIST test accuracy with 500 training examples, compared
with 84.62% for raw pixels and 93.55% for a histogram-of-oriented-gradients
(HOG) control. The result supports a modest benefit from explicit structural
information. It demonstrates selection and composition within a predefined
feature set, rather than invention of a new representation.

## Research question

A learner's inductive bias depends partly on the information presented to it.
We investigated whether an LLM could use descriptions of shape and feedback
from classification errors to select features that improve learning with few
labelled examples. The central comparison was with raw pixels under the same
classifier. HOG provided an established reference for the strength of the result.

## Methods

The search was restricted to seven feature families covering pixels, topology,
spatial structure, symmetry, stroke direction, curvature, and direction
transitions. A local Qwen language model proposed combinations and received
validation feedback. The search produced 62 unique candidates over ten
generations, including five human-designed starting candidates.

All search decisions used the official MNIST training partition, with a fixed
2,000-image validation subset. The official 10,000-image test partition was
excluded from search. Eight finalists were selected and frozen before test
evaluation. The classifier was standardized multinomial logistic regression
with fixed settings.

Final evaluation used training sizes of 250, 500, 1,000, 5,000, and 60,000,
with three training-subset seeds. Means and sample standard deviations describe
these runs. At 60,000 examples all runs used the same complete training set;
a zero standard deviation at that size does not establish absence of uncertainty.

## Results

### Predictive performance

| Representation | Dimensions | Test accuracy at 500 examples | At 5,000 examples |
|---|---:|---:|---:|
| Raw pixels and stroke direction | 792 | 86.41% ± 0.39% | 91.37% ± 0.35% |
| Raw pixels and topology | 788 | 86.41% ± 0.49% | 90.99% ± 0.64% |
| Raw pixels | 784 | 84.62% ± 0.53% | 89.04% ± 0.57% |
| HOG | 1,296 | 93.55% ± 0.45% | 96.70% ± 0.16% |
| Human topology, direction, and curvature | 20 | 62.11% ± 1.47% | 65.79% ± 0.09% |

The raw-pixel and stroke-direction representation improved mean test accuracy
by 1.79 percentage points at 500 examples. HOG remained stronger at every
training size. The compact human structural representation was substantially
weaker, although it also retained much less information than the pixel-based
candidates.

### Ablation and feedback

Removing stroke direction from the leading candidate reduced validation
accuracy from 84.15% to 81.70%. Removing pixels reduced it to 41.00%.
This supports the usefulness of the combination under the selected learner.
It does not support replacing pixels with stroke direction alone.

Feedback on targeted class confusions had mixed outcomes: among 95 recorded
comparisons, 53 confusion counts decreased, 40 increased, and two were unchanged.
The model revised its proposals, but the feedback did not reliably resolve
every targeted error. These comparisons are descriptive and are not an isolated
experiment on the causal value of feedback.

## Discussion

The experiment found a small addition to a strong pixel representation.
Its main value was to establish a controlled proposal-and-evaluation process.
The search space also imposed a clear ceiling on the claim: any successful
candidate had to be assembled from features that humans had already supplied.

The gap to HOG suggests that a useful proposal need not be competitive with
an established representation. It also motivates the next study: allow the
LLM to express compositions of atomic operations instead of selecting complete
feature operators.

## Limitations and conclusion

The findings concern one dataset and one fixed classifier. Test performance,
validation ablations, and feedback histories answer different questions and
should not be pooled as independent evidence of the same effect. The study did
not infer pen order and cannot establish an advantage of curvature over pen order.

V1 demonstrates useful feature composition in the low-data setting. It does
not establish representation invention, domain transfer, or optimizer superiority.

## Supplementary record

The [original experimental report](../FINAL_REPORT.md) retains all training-size
results, learner settings, search stopping evidence, and reproducibility details.
Historical execution guidance is in [Reproducibility](../../docs/REPRODUCIBILITY.md).
