# Model size, quantization, and sparse models

Background for reading the model tables in this repo. The arithmetic here is worked from stated figures; none of it is a measurement unless marked.

## Two different refinements

A model card often gives two parameter counts and a bit width. They solve different problems.

- **Quantization** stores each weight in fewer bits. It makes a model take less memory, which is what lets a large model fit on small hardware.
- **Sparsity** (mixture of experts) makes each token cheaper to compute. In the usual design it does not reduce memory, because every expert must stay loaded.

## Quantization

Weight memory is parameters times bits per weight divided by 8.

| model | parameters | bits per weight | weight memory (GB) |
|---|---|---|---|
| 3B dense | 3,000,000,000 | 16 | 6.0 |
| 3B dense | 3,000,000,000 | 4 | 1.5 |
| 3B dense | 3,000,000,000 | 2 | 0.75 |
| 20B sparse | 20,000,000,000 | 16 | 40.0 |
| 20B sparse | 20,000,000,000 | 4 | 10.0 |
| 20B sparse | 20,000,000,000 | 2 | 5.0 |

Apple's 2025 on-device model is about 3B parameters with 2-bit quantization-aware training ([tech report](https://arxiv.org/abs/2507.13575)).

What quantization costs:

- **Quality.** Rounding adds error. 8 bits is usually hard to tell apart from 16; 4 bits is the common tradeoff for local models; at 2 bits quality drops unless the model was trained for it.
- **Uneven damage.** Rare knowledge, math, long reasoning and non-English text tend to degrade first, so a model can chat well and still fail the hard cases.
- **Post-training quantization vs quantization-aware training.** Anyone can quantize downloaded weights after training, which is what most Ollama models are. Training with the rounding simulated gives better quality, but only the model's maker can do it.
- **Hard-to-compare numbers.** A benchmark reported for a model at 16 bits may not hold for the 4-bit file you run.

## Sparse models: total vs active parameters

A mixture-of-experts model splits parts of each layer into many experts and uses a small router to pick a few per token.

- **Total parameters** set memory and roughly how much the model can know.
- **Active parameters** set compute and speed.

Examples used in this repo:

| model | total | active | source |
|---|---|---|---|
| `gpt-oss:120b` | 116.8B | 5.13B | total from `ollama show`; active from [OpenAI's model card](https://arxiv.org/abs/2508.10925) |
| `qwen3:30b-a3b` | about 30B | about 3B | read from the model name, not checked |
| AFM 3 Core Advanced (Apple) | 20B | 1 to 4B | [Apple](https://machinelearning.apple.com/research/introducing-third-generation-of-apple-foundation-models) |

What sparsity costs:

- **Memory**, in the usual design: all experts stay loaded. Apple's AFM 3 Core Advanced is an exception; Apple says it keeps the model in flash storage and loads the experts a request needs ([summary](https://www.deeplearning.ai/the-batch/large-model-ai-for-apple-devices)).
- **Quality per parameter.** A rough rule of thumb puts a sparse model between a dense model of its active size and a dense model of its total size.
- **Training difficulty.** Routers can overuse a few experts.
- **Uneven speed**, when the number of active experts varies by request.

## Why speed depends on both

Producing a token mostly means reading the active weights from memory, so memory bandwidth usually limits speed more than compute does. A rough ceiling:

tokens per second ≈ memory bandwidth ÷ bytes of active weights read per token

Effective bandwidth worked from this repo's 2026-09-28 measurements (arithmetic, using file size or active parameters times bits):

| machine | model | GB read per token (approx.) | tokens/s measured | effective bandwidth (GB/s) |
|---|---|---|---|---|
| Yoga 9 | `qwen3:14b`, dense, 4-bit | 9.3 | 8.4 | about 78 |
| MacBook Pro, M5 Max | `gpt-oss:120b`, 5.13B active, about 4.25-bit | 2.7 | 75 | about 203 |

That is why the Yoga was about 9 times slower: roughly 2.6 times less bandwidth, times roughly 3.4 times more data read per token.

## Other ways models are shrunk

- **Distillation:** a large model trains a small one to imitate it.
- **Pruning:** removing parameters that contribute little. Apple's 2024 on-device model was pruned from 6.4B to about 3B ([paper](https://arxiv.org/abs/2407.21075)).
- **KV-cache compression:** the memory a model uses for the conversation so far grows with context length and can be shared or compressed.

Each trades some quality for size or speed, which is why this repo tests on real tasks rather than reading parameter counts.
