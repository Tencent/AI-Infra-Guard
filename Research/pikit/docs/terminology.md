# Terminology

pikit borrows vocabulary from security research and taint analysis. This page
defines every term so that newcomers can follow the code, docs, and
experiment configs without guessing.

## Threat model terms

### Taint point

A **taint point** is a compromised tool whose return value has been replaced
by the attacker's injected artifact. In a real-world attack this is
analogous to a web page, email, or document that carries a hidden
instruction — the agent fetches it through a legitimate tool call, but the
data it receives is *tainted* (carries an attacker payload).

In code, taint points are configured via the `taint` map passed to agent
constructors:

```python
agent = get_agent("browser")(target, taint={"fetch_url": tainted_page})
```

The term comes from **taint analysis** in program security: data flows from
untrusted *sources* and must not reach sensitive *sinks* without sanitisation.

### Sink

A **sink** is an externally-observable action that the attacker wants the
agent to perform — the "dangerous" tool whose invocation constitutes a
security breach. Examples:

| Sink tool | Observable effect |
|---|---|
| `send_email` | Sends an email (potential data exfiltration) |
| `post_form` | Submits a web form (potential credential theft) |
| `run_command` | Executes a shell command |
| `transfer_money` | Moves funds between accounts |

In code, tools are marked as sinks via `Tool(name=..., is_sink=True)`. The
trace flags sink calls with `<-- SINK FIRED` so you can spot them at a
glance.

The source → sink model is the same one used in taint analysis and in the
[InjecAgent](https://arxiv.org/abs/2403.02691) benchmark.

### Canary

A **canary** is a target string the attacker wants the model to output
(e.g. `"HACKED"`). The term comes from **canary tokens** / **canary strings**
in security research — a sentinel value whose presence proves a system was
compromised. If the agent's final reply contains (or is dominated by) the
canary, the injection is judged successful.

```python
# In ExperimentConfig:
canary = "HACKED"          # attacker wants this string in the output

# In RuleJudge:
judge = RuleJudge(canary="HACKED", require_sink=True)
```

Two canary signals exist:

| Signal | Meaning |
|---|---|
| `canary_terse` | The reply is short and dominated by the canary — clear compliance |
| `canary_present` | The canary appears in a longer reply — partial or ambiguous compliance |

### Tainted artifact

The **tainted artifact** is the data object (web page, email, document, PDF,
…) that carries the hidden payload. It is produced by a `Channel.taint()`
call and delivered to the model when the agent calls the corresponding taint
point tool.

In the trace, steps that carried the tainted artifact are marked
`[tainted]`:

```python
trace.tainted_steps  # → list of TraceStep that delivered tainted data
```

## How the terms fit together

```
Attacker crafts payload
        │
        ▼
   Channel.taint()  ──▶  Tainted artifact
        │                        │
        ▼                        ▼
   craft() delivery        Taint point (compromised tool returns it)
        │                        │
        ▼                        ▼
   Agent receives         Model reads tainted data
   tainted data                 │
        │                       ▼
        │              Model may comply → calls Sink or outputs Canary
        ▼
   Trace records everything → Judge renders verdict
```


