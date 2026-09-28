# Clients for local models

Which program to talk to a local model through, when the goal is attaching files and running tasks on the machine rather than writing software. Feature descriptions below come from 2026 comparison articles ([Askimo](https://askimo.chat/blog/best-mcp-clients-2026/), [LocalAI Master](https://localaimaster.com/blog/best-ollama-clients), [andrew.ooo](https://andrew.ooo/posts/anythingllm-all-in-one-ai-app/)) and were not checked against each project.

## The system prompt problem

An agent client tells the model about every tool it may call, and that description is most of its system prompt. Coding agents such as Oh My Pi (`omp`) load many tools, which costs a small local model a large share of its context before the conversation starts. Any client that loads many tools has this problem, so keeping the enabled tool list short matters more than which client is chosen.

To compare clients, send "hi" from each and read Ollama's `prompt_eval_count` for that request: it is the size of everything the client sent.

## Options

| client | attach files | run tasks on the machine | use a remote Ollama | notes |
|---|---|---|---|---|
| Open WebUI | yes | only through added tools, which run where Open WebUI runs | yes | browser interface; system prompt set per model |
| Goose | yes | yes, shell and file tools through its built-in extension | yes | agent from Block; tools can be turned on and off one by one |
| AnythingLLM | yes, strongest for folders of documents | through MCP tools and agent mode | yes | built around questions over your documents |
| Msty | yes, with a knowledge base | limited | yes | focused on privacy and chat |
| LM Studio | yes | through MCP tools | no; it runs its own models | |
| [mcp-client-for-ollama](https://github.com/jonigl/mcp-client-for-ollama) | no | through MCP tools | yes | terminal client with an editable system prompt |

Tools run on the machine where the client runs, even when the model runs elsewhere. A client on a laptop pointed at a desktop's Ollama acts on the laptop's files.

For task work, the model matters too: small models fail more often by calling tools badly than by running out of context.
