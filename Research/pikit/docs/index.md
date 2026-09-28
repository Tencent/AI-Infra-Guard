# 🧪 pikit — Prompt Injection Kit

**A composable prompt-injection research toolkit: attacks, defenses,
indirect-injection channels, built-in agent scenarios, and integrations for
real Agent frameworks and runtimes.**

Think [`foolbox`](https://github.com/bethgelab/foolbox) /
[`cleverhans`](https://github.com/cleverhans-lab/cleverhans), but for prompt
injection.

---

> [!IMPORTANT]
> **For authorized security research, red-teaming, and building defenses only.**
> Use pikit against systems you own or are explicitly permitted to test.

---

## What is pikit?

Research on LLM/agent security keeps re-implementing the same prompt-injection
techniques from scratch. **pikit** collects the classic ones behind one small,
uniform interface so you can:

- :material-call-split: **call a known attack or defense in one line**,
- :material-shuffle-variant: **freely combine** any attack with any channel
  and any defense,
- :accessory-robot: **drive a real agent** and watch whether an injection
  actually lands, and
- :material-file-plus: **add a new method** by dropping in one file — no core
  changes.

It is a *toolbox*, not a prescriptive leaderboard: it includes reference
datasets and optional judges while leaving the threat model and success
criteria under the researcher's control.

## Key features

- 🎯 **13 attacks × 9 defenses × 16 channels × 12 built-in agents**, plus
  framework adapters and runtime integrations.
- 🔀 **Direct and indirect injection** — word a payload (attack) *and* hide it
  in a carrier (channel: web page, document, Markdown, code comment, invisible
  Unicode, or an Agent Skill).
- 🤖 **Agent testbed** — a zero-dependency function-calling loop with
  preconfigured scenarios (email / RAG / browser / coding / IM / calendar /
  finance / travel / social / file manager) and a real tool-calling backend.
- 🛡️ **Defenses as pluggable hooks** at three points of an agent's data flow.
- 🧩 **Registry-based** — contributing a method is one file + one decorator.
- 📦 **Zero-dependency core** — model SDKs (OpenAI / Anthropic / HF) are
  optional extras, imported lazily.
- 📊 **Standard benchmark datasets** — 40 test cases across direct and
  indirect injection, runnable in one command for reproducible evaluation.
- 🔌 **Framework and runtime integrations** — LangChain, OpenAI Agents SDK,
  PydanticAI, OpenClaw, and Hermes can produce the same structured traces and
  experiment results as built-in scenarios.
- 🖥️ **Safe runtime experiments** — OpenClaw/Hermes test plugins provide
  controlled content-reading tools and a simulated action tool, so researchers
  can test indirect injection without Docker, messaging channels, or real
  external side effects.
- 📈 **Reports** — save JSONL results and render a Markdown or HTML summary.

## How it fits together

An attack controls **how a payload is worded**; a channel controls **where it's
hidden**; a target/agent is **what receives it**; a defense **hardens** the
prompt. They're orthogonal and compose freely:

```
                 ┌──────────── craft() ────────────┐
   task  ──▶  attack (wording)  ──▶  channel (untrusted content)
                                          │
                                          ▼
              defense (optional hook) ─▶ agent / runtime ─▶ trace / judge / report
```

| Dimension | Question it answers | Examples |
|---|---|---|
| **attack** | How is the payload *worded*? | `context_ignoring`, `combined`, `payload_splitting` |
| **channel** | Where is it *hidden*? (indirect) | `webpage`, `skills`, `code_comment`, `unicode_hidden` |
| **defense** | How do we *harden* the prompt? | `spotlighting`, `delimiters`, `sandwich` |
| **agent/integration** | What *receives* it? | `browser`, `LangChain`, `OpenClaw`, `Hermes` |

## Supported integrations

| Integration | Interface | Indirect-injection testing |
|---|---|---|
| Built-in scenarios | Python / CLI | Controlled tools and simulated actions |
| LangChain | Python adapter | Override selected tool results and record tool calls |
| OpenAI Agents SDK | Python adapter | Override function-tool results and record actions |
| PydanticAI | Python adapter | Override typed tool results and record actions |
| OpenClaw | CLI runtime integration | Isolated profile plus bundled runtime test plugin |
| Hermes | CLI runtime integration | Isolated profile plus bundled runtime test plugin |

## Next steps

<div class="grid cards" markdown>

- :material-download: **[Install pikit](installation.md)** — get started in 30 seconds
- :material-rocket-launch: **[Quick Start](quickstart.md)** — craft your first attack
- :material-book-open-variant: **[Concepts](concepts.md)** — understand the design
- :material-database: **[Datasets](datasets.md)** — run standard benchmarks
- :material-flask: **[Jupyter Notebooks](tutorials/notebooks.md)** — 7 interactive tutorials (no API key needed)
- :material-console: **[Demos & CLI](demos.md)** — run prebuilt scenarios against a real model
- :material-shield-search: **[Runtime Indirect Injection](tutorials/runtime_indirect_injection.md)** — run OpenClaw/Hermes safely
- :material-connection: **[Framework Adapters](guide/framework-adapters.md)** — integrate LangChain, Agents SDK, and PydanticAI

</div>
