# Machines and models

What is available to test, as of 2026-09-28. Local model lists come from `ollama list` on each machine that day.

## Local machines

| machine | chip | memory | GPU | runs |
|---|---|---|---|---|
| MacBook Pro | Apple M5 Max | 128 GB unified | integrated | Ollama, Apple `fm` |
| MacBook Air | Apple M1 | 16 GB unified | integrated | Apple `fm` |
| Yoga 9 14ILL10 | Intel Core Ultra 7 258V | 32 GB | Intel Arc 140V, memory shared with the system | Ollama for Windows, through Vulkan |
| Framework Desktop | AMD Ryzen AI Max+ 395 | 128 GB unified | integrated Radeon | on order; not yet tested |

## Ollama models

| machine | model | size on disk | notes |
|---|---|---|---|
| MacBook Pro | `gpt-oss:120b` | 65 GB | sparse, 116.8B total, MXFP4 quantization, 131,072-token context, Apache 2.0 |
| MacBook Pro | `qwen3-coder:30b` | 18 GB | |
| MacBook Pro | `qwen3.8:27b` | 17 GB | 27.3B, Q4_K_M, 262,144-token context, reads images |
| MacBook Pro | `devstral:24b` | 14 GB | |
| MacBook Pro | `qwen2.5:14b` | 9.0 GB | |
| MacBook Pro | `qwen2.5vl:7b` | 6.0 GB | reads images |
| MacBook Pro | `bge-m3`, `nomic-embed-text` | 1.2 GB, 274 MB | embedding models, not for generation |
| Yoga 9 | `qwen3:32b` | 20 GB | dense |
| Yoga 9 | `qwen3:30b-a3b` | 18 GB | sparse, about 3B active per its name |
| Yoga 9 | `qwen3:14b` | 9.3 GB | dense |

The Yoga also reaches the MacBook Pro's Ollama over the home network, so it can use the larger models without running them itself.

## Remote models

| model | access | price (USD per million tokens, input/output) |
|---|---|---|
| Claude Opus 5.5 | Anthropic API, or LBL's CBORG gateway | 4 / 20 |
| Gemini | Google AI Studio free tier | free within daily limits |
| CBORG-hosted open models, e.g. `lbl/gpt-oss-120b` | CBORG, LBL staff only | free |

## Published figures for the Framework Desktop

Not measured here. From public tests of the Ryzen AI Max+ 395 with 128 GB ([MindStudio](https://www.mindstudio.ai/blog/local-llm-benchmarks-ryzen-ai-halo), [Framework community](https://community.frame.work/t/amd-strix-halo-ryzen-ai-max-395-gpu-llm-performance-tests/72521)): 256 GB/s theoretical memory bandwidth, about 210 to 215 GB/s measured; `gpt-oss-120b` at about 30 to 33 tokens/s; Vulkan reported faster than ROCm; the NPU not usable for LLM inference.
