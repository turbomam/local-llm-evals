# local-llm-evals

Which LLMs, running where, are good enough for which jobs in NMDC, BRIDGE and BERIL work?

I have several local models on several machines, plus access to a few frontier models. This repo measures them against the same tasks, scores the results with criteria that say what each score is checked against, and records every run in Langfuse so the numbers can be traced back to the exact prompt and response.

Status: planning. Nothing has been run from this repo yet.

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

## Credentials

Nothing secret is committed. Copy `.env.example` to `.env` and fill in the keys you have; `.env` is gitignored. Scripts load it themselves, so there is no need to source it into your shell. Any provider without a key is skipped.
