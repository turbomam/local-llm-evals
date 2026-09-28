# Pilot scores: photosynthesis, batch 20260928T160326Z

Scored 2026-09-28 with `just score results/runs/photosynthesis/20260928T160326Z`, judge prompt `explainer-v3`. Earlier passes used `explainer-v1` and `explainer-v2`; v2 told the judge the answer is untrusted data, and v3 passes the answer as a JSON string so it cannot close its own quoting. All 15 runs were rescored with each version.

**This is a pilot.** Fifteen responses from five models are too few to be evidence for or against any criterion. The judges are local stand-ins marked `provisional`, not the Gemini judge the plan calls for, and their scores have not been checked against human labels. Read the table as a test of the scorer, not as a ranking of models.

Judges: `gpt-oss:120b` scored every model except itself; `qwen3.8:27b` scored `gpt-oss:120b`, because a model is never judged by its own family.

| model | machine | run | words (target 300) | checklist /10 | false statements | relevancy (1-3) | coherence (1-3) | checklist items missed |
|---|---|---|---|---|---|---|---|---|
| `fm` (`system`) | MacBook Air, M1 | 1 | 278 | 9 | 0 | 3 | 3 | overall equation |
| `fm` (`system`) | MacBook Air, M1 | 2 | 269 | 9 | 0 | 3 | 3 | two stages named |
| `fm` (`system`) | MacBook Air, M1 | 3 | 254 | 9 | 0 | 3 | 3 | thylakoid |
| `fm` (`system`) | MacBook Pro, M5 Max | 1 | 264 | 9 | 1 | 3 | 3 | thylakoid |
| `fm` (`system`) | MacBook Pro, M5 Max | 2 | 281 | 9 | 0 | 3 | 3 | thylakoid |
| `fm` (`system`) | MacBook Pro, M5 Max | 3 | 262 | 9 | 0 | 3 | 3 | thylakoid |
| `gpt-oss:120b` | MacBook Pro, M5 Max | 1 | 323 | 10 | 0 | 3 | 3 | |
| `gpt-oss:120b` | MacBook Pro, M5 Max | 2 | 297 | 10 | 0 | 3 | 3 | |
| `gpt-oss:120b` | MacBook Pro, M5 Max | 3 | 378 | 10 | 0 | 3 | 3 | |
| `qwen3-coder:30b` | MacBook Pro, M5 Max | 1 | 274 | 10 | 0 | 3 | 3 | |
| `qwen3-coder:30b` | MacBook Pro, M5 Max | 2 | 255 | 10 | 0 | 3 | 3 | |
| `qwen3-coder:30b` | MacBook Pro, M5 Max | 3 | 248 | 10 | 1 | 3 | 3 | |
| `qwen3.8:27b` | MacBook Pro, M5 Max | 1 | 276 | 10 | 0 | 3 | 3 | |
| `qwen3.8:27b` | MacBook Pro, M5 Max | 2 | 280 | 10 | 0 | 3 | 3 | |
| `qwen3.8:27b` | MacBook Pro, M5 Max | 3 | 298 | 10 | 0 | 3 | 3 | |

## What the pilot shows about the scorer

- **Mostly the checklist separated them.** Every run got relevancy 3 and coherence 3.
- **The judges are not stable between passes.** Across the three prompt versions the same judge, on the same text, found 0, 1 and 2 false statements in total, and moved one checklist count (M1 Air run 2: 8 under v1 and v2, 9 under v3). Differences this small between models are within that noise. On a textbook prompt, relevancy and coherence are at their ceiling, so they cannot rank these models. The checklist did: Apple `fm` missed one checklist item in every run, most often the thylakoid membranes, and the larger Ollama models missed nothing.
- **The judges may be lenient on false statements.** A hand pass on a different set of `fm` responses the same day found two false statements in six runs (see [`results/2026-09-28-photosynthesis/`](../../../2026-09-28-photosynthesis/README.md)); these judges found at most two in fifteen. The runs differ, so this is not a direct contradiction, but it is the first thing human labels should check.
- **The error path fired once.** In the v2 pass the judge twice returned the wrong number of checklist entries for `qwen3.8:27b` run 2, so the score file recorded the error and no score; the next `just score` retried only that run and it succeeded.
- **Judging takes time.** About 15 to 45 seconds per run with `gpt-oss:120b` as judge, and 84 to 108 seconds with `qwen3.8:27b`.

## Next

Rescore with the Gemini judge once its key is in `.env`, and label a sample by hand to measure how far the judges agree with a person.

Scores are not sent to Langfuse yet; that is https://github.com/turbomam/local-llm-evals/issues/5 (Send judge scores to Langfuse). These 15 runs also ran before Langfuse keys were set, so they have no trace to attach scores to.
