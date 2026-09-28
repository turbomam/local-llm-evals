# Apple `fm` and the on-device Foundation Models

`fm` is Apple's command-line interface to the on-device Foundation Models, at `/usr/bin/fm` on macOS 27. Everything below was observed on 2026-09-28 on macOS 27.0 unless a source is given.

## What `fm` offers

- One model, `system`, described in `fm --help` as "On-device Apple Foundation Model (default)". `fm available` reports "System model available".
- `fm respond` for one prompt, `fm chat` for a session, `fm count-tokens`, `fm schema` for structured output.
- `fm serve` starts a local server compatible with OpenAI's Chat Completions API (`/v1/models`, `/v1/chat/completions`), which is how this repo calls it. Its `/v1/models` lists only `"id":"system"`.
- Options include `--use-case` (`general`, `content-tagging`), `--guardrails`, `--image`, and built-in tools (`barcode`, `ocr`).

## Which Apple model `system` is

Not known. Apple's third-generation models, announced 2026-06-08, include two for devices ([Apple](https://machinelearning.apple.com/research/introducing-third-generation-of-apple-foundation-models)):

- **AFM 3 Core**, a dense 3B model
- **AFM 3 Core Advanced**, a sparse 20B model activating 1 to 4B, "unlocked by and optimized for our most capable Apple silicon systems"

`fm` has no option to choose between them and prints nothing that identifies which one runs. The binary contains no string mentioning "advanced". It is possible the operating system picks Core Advanced on capable hardware; that is not confirmed.

Apple had published no benchmark results for the third-generation models as of this writing ([summary](https://www.deeplearning.ai/the-batch/large-model-ai-for-apple-devices)). The nearest numbers are for the 2025 on-device model: MMLU 64.4 and IFEval 82.3 after 2-bit compression, context 65K tokens ([tech report](https://arxiv.org/abs/2507.13575)). A WWDC 2026 write-up gives 8,192 tokens for the framework's context window ([dev.to](https://dev.to/hariharanjagan/whats-new-in-apples-foundation-models-framework-at-wwdc-2026-5227)), which conflicts with the 65K figure.

## Model cards and leaderboards

No model card was found, from Apple or on Hugging Face. The weights are not published. One leaderboard, the [On-Device LLM Leaderboard](https://devicemark.github.io/), uses Apple's built-in model as its baseline; its data table did not load when fetched. No entry was found on Artificial Analysis, LMArena or OpenRouter.

## Measured here

See [`results/2026-09-28-photosynthesis/`](../results/2026-09-28-photosynthesis/README.md): about 51 tokens/s on an M5 Max and about 36 tokens/s on an M1, with no clear quality difference between the two on that prompt.
