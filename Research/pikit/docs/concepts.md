# Concepts

Understanding pikit's design comes down to four orthogonal dimensions and a
few key terms. For detailed definitions of **taint point**, **sink**,
**canary**, and **tainted artifact**, see the [Terminology](terminology.md)
page.

## The four dimensions

pikit decomposes prompt injection into four independent axes that compose
freely:

```
                 ┌──────────── craft() ────────────┐
   task  ──▶  attack (wording)  ──▶  channel (carrier, indirect only)
                                          │
                                          ▼
              defense (optional hook) ──▶ target / agent  ──▶  trace you read
```

| Dimension | Question it answers | Count | Examples |
|---|---|---|---|
| **Attack** | How is the payload *worded*? | 9 | `context_ignoring`, `combined`, `obfuscation` |
| **Channel** | Where is it *hidden*? (indirect) | 6 | `webpage`, `skills`, `unicode_hidden` |
| **Defense** | How do we *harden* the prompt? | 6 | `spotlighting`, `delimiters`, `sandwich` |
| **Target / Agent** | What *receives* it? | model backends, built-in scenarios, and external harnesses | `openai:…`, `browser`, `openclaw`, `hermes` |

**The key insight**: these are orthogonal. Any attack can be paired with any
channel, any defense can be applied to any agent, and the combinatorial space
is what makes pikit useful for systematic research.

## Direct vs. indirect injection

| Term | Meaning |
|---|---|
| **Direct injection** | The attacker controls the prompt/message sent directly to the model. |
| **Indirect injection** | The payload is hidden in external data the model *reads* (page, doc, email, skill) — the dangerous case for agents. |

An **Attack** handles the *wording* in both cases. A **Channel** is only
needed for indirect injection — it hides the (already worded) payload inside
a data artifact.

## Core interfaces

All four dimensions share minimal, uniform interfaces:

```python
class Attack:
    def inject(self, prompt: str, injected_task: str) -> str: ...

class Defense:
    def apply(self, prompt: str, instruction: str = None) -> str: ...

class Channel:
    def taint(self, data: str, payload: str) -> str: ...

class Target:
    def query(self, prompt: str, system: str = None, **kw) -> str: ...
    def chat(self, messages, tools=None, system=None, **kw) -> ChatResponse: ...
```

Attacks and defenses are both **plain prompt-text transformers** — they take a
string and return a string. This is what makes them freely composable: any
attack output can be fed into any defense, and vice versa.

## The agent testbed

An **Agent** wraps a `Target` and exposes `run()` → `Trace`. The agent
testbed models two critical concepts for indirect injection:

- **Taint point** — a compromised tool whose return value is the attacker's
  tainted artifact (e.g. `fetch_url` returns a malicious web page).
- **Sink** — an externally-observable action the attacker wants to trigger
  (e.g. `send_email`, `run_command`, `post_form`).

The `Trace` records every step so you can judge — manually — whether the
injection succeeded:

```python
trace = agent.run("Summarize the page at http://site")
trace.sink_calls      # tool calls that hit a sink
trace.tainted_steps  # steps that carried the injected artifact
print(trace)          # human-readable step-by-step log
```

pikit deliberately renders **no verdict** — it makes the signals easy to see
but leaves the judgement to you.

## Defense hooks

The same `Defense` objects used for direct injection can be slotted into
three points of an agent's data flow via `DefenseHooks`:

| Hook point | Defends against | Key for |
|---|---|---|
| `system` | Model being talked out of its instructions | Direct injection |
| `user` | Incoming user message | Direct injection |
| `tool_result` | Untrusted tool output re-entering the model | **Indirect injection** |

The `tool_result` hook is the most valuable for indirect injection — it's the
layer through which an attacker's tainted artifact re-enters the model.

## The registry

Every attack, defense, channel, and agent scenario registers itself under a
short string key via a decorator. This means:

```python
attacks.get("context_ignoring")   # → ContextIgnoringAttack class
attacks.list()                    # → ['combined', 'context_ignoring', ...]
```

Adding a new method is one file + one decorator — no core changes. See
[Extending pikit](extending.md).
