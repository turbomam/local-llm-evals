# nmdc-ebs, batch 20260928T212758178587Z: three runs per model

Run 2026-09-28 from commit `a34c930` with no uncommitted changes, on local models only: the same 20 cases as batch `20260928T205926561402Z`, three runs per model, 300 calls, none failed. The runner sets no temperature, so each server's default sampling applies. Scored with `just score-ontology`, no judge. Answers the question in https://github.com/turbomam/local-llm-evals/issues/9 (Measure run-to-run spread on the NMDC task).

Each cell is the lowest and highest count across the three runs, out of 20 answers per run.

| model | machine | label matches ENVO | exact | descendant | ancestor | unrelated |
|---|---|---|---|---|---|---|
| `qwen3.8:27b` | M5 Max | 18-19 | 9-10 | 2 | 0-1 | 8 |
| `gpt-oss:120b` | M5 Max | 18-19 | 9 | 2 | 1 | 8 |
| `qwen3-coder:30b` | M5 Max | 19 | 8-9 | 1-2 | 4 | 6 |
| `fm` (`system`) | M5 Max | 18 | 1-2 | 0 | 16-17 | 2 |
| `fm` (`system`) | M1 Air | 17-19 | 1-2 | 0 | 12-15 | 3-7 |

## What this shows

- **The gap between the Ollama models and Apple `fm` is real.** 8 to 10 exact against 1 to 2, with no overlap across runs.
- **The three Ollama models cannot be ranked on 20 cases.** Their exact counts overlap (8-9, 9, 9-10), so a one-point difference in any single run is noise. Telling them apart would need more cases, not more runs.
- **Apple `fm` on the M1 Air is the least stable.** Its unrelated count ranged from 3 to 7, as it moved between `terrestrial biome` and other guesses.
- **Label accuracy is stable at 17 to 19 of 20** for every model, so every model attaches a label to the wrong CURIE on one to three answers per run.

The 2 cases with the wrong curated CURIE for the epipelagic biome (https://github.com/microbiomedata/nmdc-ai-eval/issues/9) are counted as `suspect_reference` in `ontology.tsv`, as in the earlier batch.
