# Photosynthesis prompt, 2026-09-28

Prompt, identical everywhere: "Explain in about 300 words how photosynthesis works."

All numbers were measured on 2026-09-28. This was an exploratory first pass, run by hand before this repo's runner existed, so the method differs a little between tools (noted per table).

## Speed

### Apple `fm`, default model `system`

Script: [`scripts/fm-speed-test.zsh`](../../scripts/fm-speed-test.zsh). Output tokens are counted with `fm count-tokens`. Decode speed is output tokens divided by the time from the first streamed character to the last, so model loading and prompt processing are excluded. Both machines ran macOS 27.0 on AC power.

| machine | run | output tokens | first token (s) | decode (tokens/s) | total (s) |
|---|---|---|---|---|---|
| MacBook Pro, M5 Max, 128 GB | 1 | 339 | 0.93 | 52.2 | 7.43 |
| MacBook Pro, M5 Max, 128 GB | 2 | 361 | 0.38 | 51.0 | 7.46 |
| MacBook Pro, M5 Max, 128 GB | 3 | 354 | 0.39 | 50.9 | 7.34 |
| MacBook Air, M1, 16 GB | 1 | 454 | 3.50 | 36.4 | 15.97 |
| MacBook Air, M1, 16 GB | 2 | 393 | 0.62 | 35.6 | 11.66 |
| MacBook Air, M1, 16 GB | 3 | 409 | 0.60 | 35.6 | 12.10 |

The first run on each machine starts slower, which looks like a one-time model load. The M5 Max is about 1.4 times faster than the M1. Why the gap is that small is not known, and neither is whether both machines run the same Apple model; `fm` does not say which one it uses.

### Ollama

Decode speed comes from Ollama's own timers (`eval_count` over `eval_duration`). Output token counts include the models' hidden reasoning tokens.

| machine | model | run | output tokens | decode (tokens/s) | total (s) | notes |
|---|---|---|---|---|---|---|
| MacBook Pro, M5 Max | `gpt-oss:120b` | 1 | 552 | 74.7 | 26.02 | includes 18.2 s to load 64 GB |
| MacBook Pro, M5 Max | `gpt-oss:120b` | 2 | 637 | 75.7 | 8.46 | already loaded |
| Yoga 9, Core Ultra 7 258V, Arc 140V, 32 GB, on battery | `qwen3:14b` | 1 | 865 | 8.3 | 195.0 | `ollama ps`: 100% GPU, 11 GB |
| Yoga 9 | `qwen3:14b` | 2 | 929 | 8.5 | 109.2 | |

On the Yoga, `qwen3:30b-a3b` and `qwen3:32b` produced no results. The first `qwen3:30b-a3b` attempt failed with Ollama's `timed out waiting for llama-server to start`, and the remaining three attempts lost their SSH connection, consistent with the laptop sleeping on battery. The exact cause of each failure was not established.

Run 1 of `qwen3:14b` took 195 s in total, but 865 tokens at 8.3 tokens/s accounts for only about 104 s. Where the rest went is not known.

## Quality of the `fm` responses

The responses are in [`fm-m5-max.txt`](fm-m5-max.txt) and [`fm-macbook-air-m1.txt`](fm-macbook-air-m1.txt), produced by [`scripts/fm-responses.zsh`](../../scripts/fm-responses.zsh). These are a second set of runs; the text from the timed runs above was not kept.

Scored by one Claude session, not blind to which machine produced each response, and not calibrated against human labels. Treat the scores as a first look, not a measurement.

These scores predate [`docs/criteria.md`](../../docs/criteria.md) and do not follow it. They use a 1 to 4 scale without written anchors for accuracy, relevancy and coherence, where the criteria now call for yes/no checks and a 3-point scale with anchors. They are kept as a record of the first pass; the responses will be rescored under the documented method in phase 2.

Completeness checklist, 10 items: chloroplast; chlorophyll absorbs light; two stages named; thylakoid membranes; water split and oxygen released; ATP and NADPH made; Calvin cycle in the stroma; CO2 fixed; sugar produced; overall equation.

| run | words | accuracy (1-4) | false statements | relevancy (1-4) | completeness (/10) | coherence (1-4) | notes |
|---|---|---|---|---|---|---|---|
| M5 Max 1 | 270 | 4 | 1 | 4 | 8 | 4 | no thylakoid, no equation; "energy flow through ecosystems would cease" overstates, since chemosynthetic ecosystems exist |
| M5 Max 2 | 252 | 4 | 0 | 4 | 9 | 4 | no thylakoid |
| M5 Max 3 | 279 | 4 | 1 | 4 | 9 | 3 | no stroma; "some bacteria can perform it at night" is false; water splitting described after the Calvin cycle |
| M1 Air 1 | 247 | 4 | 0 | 3 | 10 | 4 | equation in raw LaTeX, unreadable in a terminal |
| M1 Air 2 | 241 | 4 | 0 | 4 | 9 | 4 | no equation; adds the proton gradient |
| M1 Air 3 | 240 | 4 | 0 | 4 | 9 | 4 | no equation |

All six call glucose the direct product, a textbook simplification (the Calvin cycle's output is G3P). All six are under the requested 300 words.

What this shows about the criteria: accuracy scored 4 on every response, so on a textbook prompt it does not separate anything. Completeness and false statements did the work. That is one argument for the yes/no checklist approach in [`docs/criteria.md`](../../docs/criteria.md).
