# Plan

## Phases

Each phase has a done state, so it is clear when to stop.

Status, 2026-09-28: phase 1 is done for the M5 Max and the MacBook Air; the Yoga, Gemini and Claude rows wait on hardware and keys. Phase 2 has a working scorer (`just score`) and a pilot run on the photosynthesis batch with local provisional judges; the final Gemini judge, sending scores to Langfuse (https://github.com/turbomam/local-llm-evals/issues/5, Send judge scores to Langfuse), and judge calibration against human labels are still to do. `just score` rescores every run each time it is called; there is no score cache. Phase 2 is not done until those are.

1. **Runner and records.** One script sends a prompt to any OpenAI-compatible endpoint (Ollama, `fm serve`, Gemini, CBORG, Anthropic) and writes one result YAML file per run plus a Langfuse trace. Done when the photosynthesis task has results for every model in [`machines-and-models.md`](machines-and-models.md).
2. **Scoring.** Tier 1 and 2 scorers from [`criteria.md`](criteria.md); the NMDC env triad scorer is imported from [nmdc-ai-eval](https://github.com/microbiomedata/nmdc-ai-eval) without changes; judged criteria use written 3-point anchors. Done when every result file has scores and Langfuse holds the same scores.
3. **Domain tasks.** NMDC env triad, then BRIDGE CSV mapping, then BERIL questions. Done when each has one full set of results.
4. **Write-up.** The README answers its three questions, one table per question, each saying how the answer is known. Findings are also written as LOKF concept files and validated. Done when someone who was not involved can rerun one task from the docs alone.

## Where each tool fits

| tool | role | skip if |
|---|---|---|
| Langfuse | one trace per run; scores attached to traces; each task stored as a Langfuse dataset so each round of runs is an experiment | never; it is the record |
| result files, dismech style | one YAML file per run, validated against a LinkML schema by one check command | never; they are the documentation |
| OpenViking | retrieval for the BERIL task, from a local instance only | the local instance can't be started quickly |
| LOKF | format for the final findings, validated with `linkml validate -s lokf.yaml` | time runs short; it is the last step |

## Who does what

Automated by the runner and scorers:

- running every task on every reachable model, including over SSH to other machines
- timing and token counts
- writing and validating result files
- scoring that needs no judge, and running the judge for scoring that does
- sending traces, scores and datasets to Langfuse
- regenerating results tables from the result files

Needs a person:

| item | why |
|---|---|
| creating API keys and putting them in `.env` | secrets are never handled by scripts or agents |
| keeping laptops awake and plugged in during runs | physical |
| approving paid frontier runs | spend |
| hand-checking ground truth for the CSV mapping task | the reference has to come from a person |
| labeling a few dozen outputs to calibrate the judge | a judge is trusted only after it is checked against people |
| confirming any data is public before it is committed | this repo is public |
| approving what the write-up claims | it is published under a person's name |

## Out of scope

- debugging the Yoga, or Ollama on Intel graphics
- changing nmdc-ai-eval or the NMDC suggester repo; this repo imports from them
- the shared BERIL OpenViking server
- a general-purpose harness; one runner script and one model list are enough

## Frameworks

Reused rather than written: Langfuse datasets, experiments and LLM judges for running and recording; RAGAS formulas for factuality and relevancy; CheckEval-style yes/no questions for completeness; nmdc-ai-eval's `envo_scorer` for ENVO terms. [Inspect AI](https://inspect.aisi.org.uk/models.html) is a complete alternative harness with Ollama support and built-in judge scorers; it is not used because it keeps its own logs alongside Langfuse.

Written here: task files, checklists and anchors, the runner, and the code that sends scores to Langfuse.
