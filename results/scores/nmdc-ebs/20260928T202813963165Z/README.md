# nmdc-ebs, batch 20260928T202813963165Z

Run 2026-09-28 on local models only: 20 cases (2 per biome) from the ebs-prediction suite in microbiomedata/nmdc-ai-eval at `4e2fa04`, one run each. Scored with `just score-ontology`, no judge. Per-answer detail is in `ontology.tsv`. This is a pilot, not a benchmark: 20 cases, one run.

| model | machine | parses | CURIE exists | label matches ENVO | exact | exact, sound reference | descendant | ancestor | unrelated |
|---|---|---|---|---|---|---|---|---|---|
| `gpt-oss:120b` | M5 Max | 20 | 20 | 18 | 9 | 9 | 2 | 1 | 8 |
| `qwen3-coder:30b` | M5 Max | 20 | 20 | 19 | 8 | 8 | 1 | 7 | 4 |
| `qwen3.8:27b` | M5 Max | 20 | 20 | 18 | 10 | 10 | 1 | 0 | 9 |
| `fm` (`system`) | M5 Max | 20 | 20 | 18 | 1 | 1 | 0 | 17 | 2 |
| `fm` (`system`) | M1 Air | 20 | 20 | 19 | 1 | 1 | 0 | 14 | 5 |

All counts are out of 20 answers.

## What this shows

- **Apple `fm` answers vaguely.** 14 of 20 answers on each machine were `terrestrial biome [ENVO:00000446]`, an ancestor of most curated values. It follows the format but rarely picks a specific biome.
- **The three Ollama models pick specific biomes** and are exact on 8 to 10 of 20. Their misses are mostly neighbouring biomes (a subtropical grassland for a cropland), which only the tier 2 split can tell apart from nonsense.
- **Every model fabricates a CURIE now and then.** Examples: `urban biome [ENVO:00000447]` (that CURIE is marine biome), `terrestrial biome [ENVO:00000444]` (woodland clearing). The label-matches column catches these; an exact-match score would call them simply wrong.

## One curated value is wrong

2 of the 20 cases have the curated value `oceanic epipelagic zone biome [ENVO:01000036]`, but `ENVO:01000036` is oceanic mesopelagic zone biome; the epipelagic term is `ENVO:01000035`. `gpt-oss:120b` and `qwen3.8:27b` answered the correct `ENVO:01000035` (1 and 2 answers) and were scored unrelated to the reference. The scorer now checks each curated value against ENVO and counts these as `suspect_reference` in `ontology.tsv`. This is the same error recorded in https://github.com/microbiomedata/nmdc-ai-eval/issues/9 (Data: 289 rows have wrong CURIE for oceanic epipelagic zone biome); it affects 10 of the 100 suite cases.
