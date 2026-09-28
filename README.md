# local-llm-evals

Which LLMs, running where, are good enough for which jobs in NMDC, BRIDGE and BERIL work?

I have several local models on several machines, plus access to a few frontier models. This repo measures them against the same tasks, scores the results with criteria that say what each score is checked against, and records every run in Langfuse so the numbers can be traced back to the exact prompt and response.

Status: planning. One exploratory pass was run by hand on 2026-09-28, before the runner existed: [photosynthesis results](results/2026-09-28-photosynthesis/README.md).

## Docs

- [Plan](docs/plan.md): phases, what is automated and what needs a person, what is out of scope
- [Evaluation criteria](docs/criteria.md): the five criteria, what each is checked against, and how formally
- [Ground truth](docs/ground-truth.md): where reference answers come from for each task
- [Machines and models](docs/machines-and-models.md): hardware and model inventory
- [Model size, quantization, and sparse models](docs/model-size-and-quantization.md): how to read parameter counts and bit widths, and why speed depends on memory bandwidth
- [Apple `fm`](docs/apple-fm.md): the on-device model, what is and is not known about it
- [Clients for local models](docs/clients.md): which program to use for file attachments and running tasks

## Goals

1. **Match models to jobs.** For each model on each machine, find which kinds of task it gets right, how fast, and at what cost.
2. **Find what can move off frontier models.** For real tasks from NMDC ([National Microbiome Data Collaborative](https://microbiomedata.org)), BRIDGE (the DOE effort NMDC's portals are moving into) and BERIL (the BER Research Observatory's agentic analysis work), find where a local model is good enough and what quality is lost.
3. **Test the scoring criteria.** Check whether the NMDC suggester squad's five criteria (accuracy, factuality, relevancy, completeness, coherence) give stable, useful scores on tasks other than the suggester's.

## Tasks

| task | program | how it is scored |
|---|---|---|
| explain photosynthesis in about 300 words | control | 10-item checklist, word count, judge |
| capability cases: 12 cases in 5 skill buckets | control | exact answer, set, or correct refusal; no judge |
| env triad (`env_broad_scale`, `env_local_scale`, `env_medium`) for 5 curated studies | NMDC | ontology checks against ENVO, no judge |
| map CSV column headers to NMDC slots | BRIDGE | slot exists, plus judge |
| answer a question from BERIL project reports | BERIL | claims checked against the retrieved passages |

## Models

| where | models |
|---|---|
| MacBook Pro, M5 Max, 128 GB | `gpt-oss:120b`, `qwen3-coder:30b`, `qwen3.8:27b` (Ollama); Apple `fm` |
| MacBook Air, M1, 16 GB | Apple `fm` |
| Yoga 9, Core Ultra 7 258V, 32 GB | `qwen3:30b-a3b` (Ollama), when plugged in |
| Framework Desktop, Ryzen AI Max+ 395, 128 GB | added when it arrives |
| remote | Claude Opus 5.5, Gemini |

The judge is always from a different model family than the model being judged.

## Tools

- **Langfuse** holds the record: one trace per run, scores attached to traces, each task stored as a Langfuse dataset.
- **Result files** follow the [dismech](https://github.com/monarch-initiative/dismech) pattern: one YAML file per run, validated against a LinkML schema by a single check command.
- **OpenViking** supplies retrieval for the BERIL task only, from a local instance.
- **LOKF** ([Linked Open Knowledge Format](https://github.com/nicholsn/lokf)) is the format for the final findings.

## Running

Needs [uv](https://docs.astral.sh/uv/) and [just](https://github.com/casey/just).

```sh
cp .env.example .env    # then fill in the keys you have
just dry-run            # which models would run, and why the others are skipped
just run photosynthesis 3                                # every runnable model, 3 runs each
just run photosynthesis 1 m5-fm-system,m5-gpt-oss-120b  # only these models
just check              # validate every result file against schema/run_result.yaml
```

Models are listed in [`config/models.yaml`](config/models.yaml), tasks in [`tasks/`](tasks/). Each run writes `results/runs/<task>/<batch>/<model>-run<N>.yaml`, and, when Langfuse keys are set, a Langfuse generation in a session named after the batch. Apple `fm` needs `fm serve --port 1976` running first.

## Credentials

Nothing secret is committed. Copy `.env.example` to `.env` and fill in the keys you have; `.env` is gitignored. Scripts load it themselves, so there is no need to source it into your shell. Any provider without a key is skipped.
