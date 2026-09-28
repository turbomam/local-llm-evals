# Evaluation criteria

The five criteria come from the NMDC AI suggester squad's evals discussion on 2026-09-18: accuracy, factuality, relevancy, completeness, coherence. This page says how each is scored here and what it is checked against.

## The organizing rule

Group criteria by what a score is checked against. A criterion is well defined when its definition is a computation, and it is separable from its neighbours when it is checked against a different thing. Criteria with nothing to check against (helpfulness, fluency, tone) are the ones published metric lists disagree about most, and this repo does not score them.

## Tiers

These tiers come from a 2026-09-22 draft of metric criteria for NMDC metadata suggestion. Different tiers use different scales.

| tier | checked against | judge? | scale |
|---|---|---|---|
| 1 | a formal spec (a regex, an ontology lookup, a schema, an exact answer) | no | yes or no |
| 2 | ontology structure | no | 0 to 1, reported as two parts: information missed and false information asserted |
| 3 | the request or a source text | yes | 3 points with written anchors: supported, partially supported, unsupported |
| 4 | the execution trace | no | counts, always with the denominator |

A 10-point scale on a judgement with no reference gives false precision and poor agreement between runs, so none is used.

## The five criteria

| criterion | checked against | computation here | existing method |
|---|---|---|---|
| accuracy | a reference answer | exact match, set match, or ontology distance | RAGAS Factual Correctness; `envo_scorer` in [nmdc-ai-eval](https://github.com/microbiomedata/nmdc-ai-eval) for ENVO terms |
| factuality | a source: retrieved passages, a knowledge base, or search | split the response into atomic claims, count the unsupported ones | [FActScore](https://arxiv.org/abs/2305.14251), [SAFE](https://arxiv.org/abs/2403.18802), RAGAS Faithfulness |
| relevancy | the request | judge, 3-point; includes following explicit instructions such as length | RAGAS Response Relevancy |
| completeness | a per-task checklist | yes/no per item, reported as items present out of the total | [CheckEval](https://arxiv.org/abs/2403.18771) |
| coherence | depends on the task | for prose, judge with anchors; for NMDC env triads, the three values checked against each other and against the GOLD ecosystem path already on the sample record | [G-Eval](https://arxiv.org/abs/2303.16634) for prose |

Two things these five miss, worth adding as tier 1 checks where they apply: whether the output is valid against its format (IDs, JSON, schema), and whether the model declines to answer when it should instead of guessing.

## How formal

Each task's page states, for every criterion it uses: what the score is checked against, the computation, the scale, and for judged criteria the exact judge prompt, stored with a version.

The judge is always from a different model family than the model being scored.

A judge's scores are calibrated before they are trusted: a person labels a few dozen outputs and the agreement between judge and person is reported.

Every task runs at least three times per model, and the spread between runs is reported alongside the scores.

Accuracy and factuality overlap unless each names what it is checked against. The first photosynthesis pass showed this: accuracy scored 4 of 4 on all six responses, while completeness and false-statement counts separated them. See [`results/2026-09-28-photosynthesis/`](../results/2026-09-28-photosynthesis/README.md).
