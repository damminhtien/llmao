# V2. Synthesizing compact representation programs

## Abstract

V2 examines whether a language model can construct representations by composing
atomic image and geometric operations. Two 200-candidate searches were conducted:
one excluded raw pixels, while the other permitted pixel augmentation. The best
raw-free program achieved 71.80% validation accuracy with 500 training examples
using 16 features. Frozen transfer and intervention tests revealed the limits
of its interpretation: selected programs depended on distributional summaries,
and sequence shuffling did not change predictions. The study expanded the
representation space without establishing an order-sensitive or generally
handwriting-specific prior.

## Research question

Selecting from complete feature operators limits what an LLM can propose.
We asked whether a compositional representation language would allow compact
structural descriptions to emerge, and whether their behavior would support
the proposed explanations beyond MNIST validation accuracy.

## Methods

Representations were expressed as typed compositions over images, skeletons,
graphs, paths, sequences, and numerical summaries. Type constraints limited
which operations could be composed. The discovery search prohibited raw pixels;
the augmentation search permitted them. Each evaluated 20 starting programs
and 180 subsequent proposals from a local Qwen model.

A fixed learner and validation split were used to compare candidates. A
quality-diversity archive retained programs across proposed representation
families. Both searches evaluated 200 candidates, but response batching differed
following truncation in the augmentation run. Their best scores therefore
provide descriptive outcomes rather than a controlled comparison of tracks.

Five discovery finalists were frozen before external evaluation. Transfer used
EMNIST Digits, EMNIST Letters, KMNIST, and Fashion-MNIST, with 500 and 5,000
training examples, three training seeds, and stratified samples of 2,000 images
from each official test partition. Sequence interventions tested whether the
ordering of intermediate values affected predictions. Transformation proposals
were evaluated separately using MNIST training and validation data only.

## Results

### Search and augmentation

![V2 augmentation controls and transfer](../figures/V2_AUGMENTATION_TRANSFER.png)

**Figure 1.** Left: post-search validation controls at two training sizes.
Right: frozen spatial-cycle transfer with 5,000 training examples; error bars
show standard deviations over three training seeds. Each domain uses 2,000
sampled official-test images. Panels use different evaluation partitions.

The leading discovery program combined cycle and angle summaries. It used
16 features and achieved 71.80% validation accuracy at 500 examples and 74.20%
at 5,000. The augmentation search reached 64.45% at 500 examples; although raw
pixels were allowed, its archive contained no raw-pixel representation.

A separate, post-search control added a frozen 12-dimensional angle histogram
to raw pixels. Accuracy increased from 81.70% to 85.25% at 500 examples and
from 87.65% to 91.70% at 5,000. These are validation results from the same split
used for selection. The composition was supplied after search, and is neither
an independently tested result nor a representation found by the LLM search.

Most candidates were classified as hybrid: 141 of 200 in discovery and 166 of
200 in augmentation. Several intended families remained empty. This indicated
that the archive description did not adequately distinguish behavioral structure.

### Transfer

The strongest reported transfer program, a 25-dimensional spatial cycle
summary, obtained the following mean test accuracies across three training seeds.

| Domain | 500 training examples | 5,000 training examples |
|---|---:|---:|
| EMNIST Digits | 77.28% ± 1.23% | 81.20% ± 0.10% |
| EMNIST Letters | 44.03% ± 0.53% | 49.93% ± 0.42% |
| KMNIST | 42.43% ± 0.89% | 45.38% ± 1.15% |
| Fashion-MNIST | 66.72% ± 1.11% | 70.80% ± 0.46% |

Performance on Fashion-MNIST prevents interpreting transfer as evidence of a
specifically handwriting-related mechanism. Accuracy levels across datasets
also involve different label spaces and cannot be compared as if the tasks
had equal difficulty.

### Interventions and invariance

All tested sequence shuffles preserved predictions exactly. The selected
representations therefore supplied no evidence of sequence-order dependence.
This null result is consistent with their use of distributional summaries.

A two-pixel horizontal translation passed the predefined validation rule.
Rotation, erosion, and a combined deformation did not. Averaging representations
over the accepted transformation reduced holdout validation accuracy from
74.40% to 74.20%, so passing the invariance screen did not yield an improvement
from the tested pooling procedure.

## Discussion

The representation language made new compositions expressible, but the search
still favored familiar statistical summaries. The archive grouped structurally
different programs together, making diversity difficult to interpret. A useful
transfer result also left its mechanism unresolved.

These observations motivate V3's focus on behavioral descriptors, spatial
relations, and interventions tied to a specific hypothesis. They also show why
program synthesis and inductive-bias discovery should remain distinct claims.

## Limitations and conclusion

Search maxima were selected on validation data. The post-search augmentation
control reused that data, and the two search tracks differed in proposal
batching. External evaluation used sampled official test partitions rather than
full-test estimates. The sequence interventions tested the chosen program nodes;
they do not show that order is irrelevant to handwriting generally.

V2 demonstrates bounded representation synthesis and compact transfer features.
It does not establish an order-sensitive mechanism or a universal handwriting bias.

## Supplementary record

The [original experimental report](../V2_PROGRAM_SYNTHESIS.md) retains every
transfer table, candidate identity, dataset provenance record, transformation
specification, and computational profile.
