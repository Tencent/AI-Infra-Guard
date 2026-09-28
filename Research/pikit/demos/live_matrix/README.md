# 06 · Live matrix — every method against a real model

Full-coverage smoke tests: **one real example per attack, defense, channel,
and agent**, run against a live OpenAI-compatible model. The goal is to
confirm each method runs end to end on a real model — and to serve as
copy-paste recipes you can learn from.

> These call a real model and cost tokens. Each method runs exactly one
> example to keep it cheap.

## Setup

Put your credentials in `.env` (copy from `.env.example` at the repo root)
and load them — **don't** paste the key on the command line:

```bash
cp .env.example .env       # edit .env with your real key
set -a; source .env; set +a
```

`.env` holds `OPENAI_API_KEY`, `OPENAI_BASE_URL`, and `PIKIT_MODEL`. It is
gitignored and no key is hardcoded — everything is read from the environment.
See the repo README's "Configuring model access" section for details.

## Scripts

| script | covers |
|---|---|
| `test_attacks_live.py` | every attack (direct injection: benign request + payload → model) |
| `test_defenses_live.py` | every defense (tainted prompt, undefended vs hardened → model) |
| `test_channels_live.py` | every channel (payload hidden in the matching sample → model) |
| `test_agents_live.py` | every agent (chat/email/rag/browser/coding/tool), real tool loop |
| `run_all.py` | all of the above in sequence |

Run one:

```bash
python demos/live_matrix/test_agents_live.py
```

Or everything:

```bash
python demos/live_matrix/run_all.py
```

## Reading the output

- Attack/defense/channel scripts print `-> injection obeyed? YES/no` based on
  whether the reply contains the canary string (`HACKED`). This is a rough
  eyeball signal, **not** a scorer — use pikit's optional judges for batch
  experiments, but validate that their criteria fit your threat model.
- Agent scripts print a full `Trace`; look for `[tainted]` (artifact
  delivered) and `SINK FIRED` (observable malicious action), then
  `-> sink fired: ...`.

A resistant model (e.g. Qwen often refuses these) yields `no` / `NONE` —
that's a real result, not a bug. Swap `PIKIT_MODEL` / endpoint to compare
models.
