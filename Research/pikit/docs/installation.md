# Installation

pikit requires **Python 3.9+** and has a **zero-dependency core** — attacks,
defenses, channels, and the mock target work out of the box with no
third-party packages.

## From source (recommended)

```bash
git clone https://github.com/NY1024/pikit.git
cd pikit

pip install -e .                 # core: attacks + defenses + channels (zero deps)
```

## Optional extras

Model SDKs are installed only when you need a specific backend:

```bash
pip install -e ".[openai]"       # + OpenAI / OpenAI-compatible (vLLM, Ollama, DashScope)
pip install -e ".[anthropic]"    # + Anthropic Claude
pip install -e ".[hf]"           # + local HuggingFace transformers
pip install -e ".[all,dev]"      # everything + pytest
```

| Extra | Packages | When to install |
|---|---|---|
| `openai` | `openai>=1.0` | OpenAI API, vLLM, Ollama, DashScope/Qwen, LM Studio |
| `anthropic` | `anthropic>=0.39` | Anthropic Claude models |
| `hf` | `torch>=2.0`, `transformers>=4.40` | Local HuggingFace models |
| `dev` | `pytest>=7.0` | Running the test suite |

## Verify the install

```bash
python -c "from pikit import attacks, defenses, channels; print(attacks.list())"
# ['combined', 'context_ignoring', 'context_flooding', 'cross_channel',
#  'escape', 'fake_completion', 'format_confusion', 'important_instructions',
#  'naive', 'obfuscation', 'payload_splitting', 'prefix_injection',
#  'stealth_instruction']
```

## Run the test suite

The full test suite is offline (no API key required):

```bash
pytest
```

## Configuring model access

Real backends read credentials from the **environment** — never hardcode a key
or pass it on the command line.

```bash
cp .env.example .env            # then edit .env with your real key
set -a; source .env; set +a     # export the vars into your shell
```

| Variable | Meaning |
|---|---|
| `OPENAI_API_KEY` | Key for an OpenAI-compatible endpoint |
| `OPENAI_BASE_URL` | Endpoint URL; omit for OpenAI. DashScope/Qwen: `https://dashscope.aliyuncs.com/compatible-mode/v1` |
| `ANTHROPIC_API_KEY` | Key for Anthropic Claude |
| `PIKIT_MODEL` | Default model id for the demos (optional) |

`.env` is gitignored. If a key was ever pasted on a command line or committed,
**rotate it** — a leaked secret can't be un-leaked.
