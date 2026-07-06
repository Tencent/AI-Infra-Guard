# aig-skill-scan

English | **[中文](./README_zh.md)**

> AI Native Agent Skill security auditing tool — an LLM-driven multi-stage code audit and vulnerability review pipeline.

`aig-skill-scan` is a subproject of [Tencent AI-Infra-Guard](https://github.com/Tencent/AI-Infra-Guard), purpose-built for static security auditing of AI Agent Skill projects (OpenClaw Skills, etc.). It runs a three-stage pipeline powered by LLM-driven deep analysis:

1. **Info Collection** — project structure, language, entry-point identification
2. **Code Audit** — parallel multi-skill auditing (data leakage, tool abuse, indirect injection, authorization bypass, etc.)
3. **Vulnerability Review** — deduplication, false-positive filtering, severity scoring, report generation

Vulnerability classification follows the [SkillTrustBench](https://github.com/Tencent/AI-Infra-Guard) T01–T09 taxonomy. Verdicts: `malicious` (clear attack intent) / `suspicious` (vulnerability present but no clear attack intent) / `normal` (benign).

---

## Installation

```bash
# From PyPI
pip install aig-skill-scan

# Or from source (development)
git clone https://github.com/Tencent/AI-Infra-Guard.git
cd AI-Infra-Guard/skill-scan
pip install -e .
```

Requires Python ≥ 3.9.

---

## Quick Start

### Command Line

```bash
# Set API key via environment variable
export LLM_API_KEY="your-api-key"

# Scan a local Skill project directory
aig-skill-scan --repo /path/to/your/skill \
           -m deepseek-v4-flash \
           --language en \
           -o result.json

# Or invoke as a module
python -m skill_scan --repo /path/to/your/skill
```

Full options:

```
aig-skill-scan --help
```

| Option | Description | Default |
| --- | --- | --- |
| `--repo` | Path to the Skill project directory to scan (required) | — |
| `-m, --model` | LLM model name | `deepseek-v4-flash` |
| `-k, --api_key` | API key (falls back to env vars if omitted) | — |
| `-u, --base_url` | API base URL | `https://openrouter.ai/api/v1` |
| `-p, --prompt` | Custom scan prompt (optional) | — |
| `--language` | Output language: `zh` / `en` | `zh` |
| `--debug` | Enable debug mode | `false` |
| `--aig-mode` | Enable AIG integration mode (emit structured JSON to stdout for the Go backend; not needed for standalone use) | `false` |
| `-o, --output` | Save the scan result as a JSON file | — |

> `--aig-mode` is intended for the AI-Infra-Guard platform backend. When enabled, it writes `newPlanStep`/`statusUpdate`/`toolUsed` structured JSON lines to stdout. Do **not** enable it when using `pip install` standalone — it will pollute your terminal with JSON.

### Programmatic Usage

```python
import asyncio
import os
from skill_scan.agent.agent import Agent
from skill_scan.utils.llm import LLM
from skill_scan.utils.aig_logger import mcpLogger

async def run():
    # API key must be read from environment variables, never hardcoded
    api_key = os.environ.get("LLM_API_KEY")
    if not api_key:
        raise RuntimeError("LLM_API_KEY environment variable must be set")

    llm = LLM(model="deepseek-v4-flash",
              api_key=api_key,
              base_url="https://openrouter.ai/api/v1",
              context_window=128_000)

    agent = Agent(llm=llm, debug=False, language="en")
    # Uncomment the next line if you need structured JSON logs (e.g. integrating into another system)
    # mcpLogger.enable()
    result = await agent.scan("/path/to/your/skill", "", "en")
    print(result)

asyncio.run(run())
```

---

## Configuration

All configuration is injected via environment variables or a `.env` file. `aig-skill-scan` looks for `.env` in this order:

1. Package root (`site-packages/skill_scan/.env` — rarely used post-install)
2. Current working directory (`./.env` — recommended)

Key environment variables:

| Variable | Description | Default |
| --- | --- | --- |
| `LLM_API_KEY` / `OPENAI_API_KEY` | LLM API key (**must be set via environment variable, never hardcode**) | — |
| `LLM_MODEL` / `OPENAI_MODEL` | Default model | `deepseek-v4-flash` |
| `LLM_BASE_URL` / `OPENAI_BASE_URL` | Default base URL | `https://openrouter.ai/api/v1` |
| `DEFAULT_MODEL_CONTEXT_WINDOW` | Main model context window | `128000` |
| `LOG_LEVEL` | Log level | `INFO` |

---

## Architecture

```
skill_scan/
├── agent/              # Three-stage ScanPipeline orchestration
│   ├── agent.py        # Agent class, dispatches Info → Audit → Review
│   └── base_agent.py   # LLM loop + tool-calling base class
├── tools/              # XML-schema tool registry
│   ├── registry.py     # @register_tool decorator
│   ├── dispatcher.py   # ToolDispatcher, routes tool calls
│   ├── file/ ls/ grep/ dir/ base64_decode/ thinking/ finish/
│   └── *_schema.xml    # XML schemas consumed by the LLM
├── utils/
│   ├── llm.py          # OpenAI-compatible client
│   ├── prompt_manager.py# Prompt template loader (from skill_scan/prompt/)
│   ├── aig_logger.py   # AIG integration logger (off by default, enabled via --aig-mode)
│   ├── extract_vuln.py # <vuln> XML extraction and parsing
│   ├── project_analyzer.py # Language detection + calc_skill_score
│   └── pre_scan.py     # Pre-scan, generates project summary
├── prompt/             # Packaged prompt templates
│   ├── system_prompt.md
│   ├── compact.md  next_prompt.md  format_report.md
│   └── agents/         # Per-stage prompts
└── main.py             # CLI entry point (cli / main / parse_args)
```

---

## Scoring

`calc_skill_score` mirrors mcp-scan's `calc_mcp_score`:

| Severity | Deduction |
| --- | --- |
| Critical | -100 |
| High | -40 |
| Medium | -25 |
| Low / Info | -10 |

Final skill score = `max(0, 100 - Σ deductions)`.

---

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Lint / format
ruff check skill_scan
ruff format skill_scan

# Build locally
python -m build

# Install and test locally
pip install dist/aig_skill_scan-0.1.0-py3-none-any.whl
aig-skill-scan --help
```

---

## License

Apache License 2.0. Any redistribution or derivative work must clearly state
"Based on Tencent Zhuque Lab AI-Infra-Guard" in its documentation or UI and
link to the original repository at <https://github.com/Tencent/AI-Infra-Guard>.
See [NOTICE](./NOTICE) for details.
