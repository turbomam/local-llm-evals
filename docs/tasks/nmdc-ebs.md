# Task: nmdc-ebs

Predict `env_broad_scale` for an NMDC biosample from its study and sample metadata, answering with one ENVO term as `label [CURIE]`.

## Why this task

It is the NMDC metadata suggester's core job in miniature, and it can be scored with no judge and no spend: the curated value already exists for every case, and ENVO settles whether an answer is well formed and how far it is from the curated term.

## Cases

The `ebs-prediction` suite in https://github.com/microbiomedata/nmdc-ai-eval, pinned to commit `4e2fa04`. The suite has 100 real biosample cases, 10 for each of 10 biomes; `tasks/nmdc-ebs.yaml` takes the first 2 per biome, 20 cases. The cases, the suite's own system prompt (`predict_ebs`) and the curated answers are fetched at run time rather than copied, because that repository has no license file.

## Scoring

`just score-ontology results/runs/nmdc-ebs/<batch>` writes `results/scores/nmdc-ebs/<batch>/ontology.tsv`, one row per answer, using nmdc-ai-eval's `envo_scorer` unchanged:

| check | tier | computation |
|---|---|---|
| parses as `label [CURIE]` | 1 | `parse_label_curie` |
| CURIE exists in ENVO | 1 | ontology lookup |
| label is ENVO's label for that CURIE | 1 | string compare with the looked-up label |
| exact match with the curated term | 2 | CURIE compare |
| relationship to the curated term | 2 | ancestor (vaguer), descendant (more specific) or unrelated, by `rdfs:subClassOf` |
| hops | 2 | subclass steps between the two |
| `hierarchy_score` | 2 | nmdc-ai-eval's existing composite, kept for continuity; `docs/criteria.md` questions its weights |

Each check is reported on its own, following `docs/criteria.md`. The suite's per-template enum check is left out: its data is in nmdc-ai-eval's `datasets/` directory, not its package.

## Open question inherited from NMDC

Whether the curated values are sound enough to be ground truth is not settled. An answer that disagrees with the curated term is reported as a disagreement, not as an error, until that is checked.
