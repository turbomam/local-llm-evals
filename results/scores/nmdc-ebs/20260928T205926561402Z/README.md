# nmdc-ebs, batch 20260928T205926561402Z

Run 2026-09-28 from commit `596ca05` with no uncommitted code changes (`repo_dirty: false` in every run file), on local models only: 20 cases (2 per biome) from the ebs-prediction suite in microbiomedata/nmdc-ai-eval at `4e2fa04`, one run each. Scored with `just score-ontology`, no judge. Per-answer detail is in `ontology.tsv`. This is a pilot, not a benchmark: 20 cases, one run.

| model | machine | parses | CURIE exists | label matches ENVO | exact | exact, sound reference | descendant | ancestor | unrelated |
|---|---|---|---|---|---|---|---|---|---|
| `gpt-oss:120b` | M5 Max | 20 | 20 | 20 | 10 | 10 | 2 | 1 | 7 |
| `qwen3.8:27b` | M5 Max | 20 | 20 | 20 | 9 | 9 | 2 | 1 | 8 |
| `qwen3-coder:30b` | M5 Max | 20 | 20 | 18 | 8 | 8 | 1 | 5 | 6 |
| `fm` (`system`) | M5 Max | 20 | 20 | 18 | 2 | 2 | 0 | 16 | 2 |
| `fm` (`system`) | M1 Air | 20 | 20 | 19 | 1 | 1 | 0 | 15 | 4 |

All counts are out of 20 answers.

## What this shows

- **Apple `fm` answers vaguely.** 15 of 20 answers on the Air and 13 of 20 on the M5 were `terrestrial biome [ENVO:00000446]`, an ancestor of most curated values. It follows the format but rarely picks a specific biome.
- **The three Ollama models pick specific biomes** and are exact on 8 to 10 of 20. Most misses are neighbouring biomes, which only the tier 2 split tells apart from nonsense.
- **Models sometimes attach a label to the wrong CURIE.** For example `temperate forest biome [ENVO:01000174]`, where ENVO's label for that CURIE is forest biome. The label-matches column catches these; an exact-match score would count them only as misses.
- **Single runs are not stable.** An earlier run of the same 100 calls, discarded because it recorded a commit that did not contain the task, gave slightly different counts, for example 9 exact and 18 label matches for `gpt-oss:120b` against 10 and 20 here. Treat differences of one or two between models as noise until runs are repeated.

## One curated value is wrong

2 of the 20 cases have the curated value `oceanic epipelagic zone biome [ENVO:01000036]`, but `ENVO:01000036` is oceanic mesopelagic zone biome; the epipelagic term is `ENVO:01000035`. Models that answered the correct `ENVO:01000035` would be scored unrelated to the reference. The scorer checks every curated value against ENVO and counts these as `suspect_reference` in `ontology.tsv`. This is the error recorded in https://github.com/microbiomedata/nmdc-ai-eval/issues/9 (Data: 289 rows have wrong CURIE for oceanic epipelagic zone biome); it affects 10 of the 100 suite cases.
