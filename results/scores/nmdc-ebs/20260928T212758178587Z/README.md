# nmdc-ebs, batch 20260928T212758178587Z: three runs per model

Run 2026-09-28 from commit `a34c930` with no uncommitted changes, on local models only: the same 20 cases as batch `20260928T205926561402Z`, three runs per model, 300 calls, none failed. The runner sets no temperature, so each server's default sampling applies. Scored with `just score-ontology`, no judge. Answers the question in https://github.com/turbomam/local-llm-evals/issues/9 (Measure run-to-run spread on the NMDC task).

Each cell is the lowest and highest count across the three runs. The counts cover the 18 cases whose curated value is sound: the 2 cases carrying the wrong CURIE for the epipelagic biome (https://github.com/microbiomedata/nmdc-ai-eval/issues/9) are left out, because a correct answer to them scores as unrelated. Every run contains all 18 cases.

| model | machine | label matches ENVO | exact | descendant | ancestor | unrelated |
|---|---|---|---|---|---|---|
| `qwen3.8:27b` | M5 Max | 16-17 | 9-10 | 2 | 0 | 6-7 |
| `gpt-oss:120b` | M5 Max | 16-17 | 9 | 2 | 0 | 7 |
| `qwen3-coder:30b` | M5 Max | 17 | 8-9 | 1-2 | 3-4 | 4-5 |
| `fm` (`system`) | M5 Max | 16 | 1-2 | 0 | 14-15 | 2 |
| `fm` (`system`) | M1 Air | 15-17 | 1-2 | 0 | 12-14 | 3-5 |

These are observed ranges from three runs, not confidence intervals.

## What this shows

- **The Ollama models were exact far more often than Apple `fm`**: 8 to 10 against 1 to 2 of 18, in every run.
- **This experiment does not rank the three Ollama models.** Their observed ranges overlap. Separating them would take more runs to pin down each model's expected score on these cases, more cases to generalize beyond them, or both, with an analysis that estimates uncertainty rather than reading minimums and maximums.
- **Apple `fm` moved most between runs on the M1 Air**, where its ancestor and unrelated counts each shifted by two as it moved between `terrestrial biome` and other guesses.
- **Every model attached a label to the wrong CURIE on one to three of 18 answers per run.**
