# aig-skill-scan

English | **[中文](./README_zh.md)**

> AI Native Agent Skill security auditing tool — an LLM-driven multi-stage code audit and vulnerability review pipeline.

`aig-skill-scan` is a subproject of [Tencent AI-Infra-Guard](https://github.com/Tencent/AI-Infra-Guard), purpose-built for static, LLM-driven security auditing of AI Agent Skill projects (OpenClaw Skills, etc.).

- **Default (single-stage) mode**: runs only the **Code Audit** stage and outputs vulnerabilities directly — faster, ideal for standalone CLI use.
- **`--aig-mode` (three-stage) mode**: the full **Info Collection → Code Audit → Vulnerability Review** pipeline, used for the AI-Infra-Guard platform's step-by-step frontend display; no need to enable it manually otherwise.

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
           -o result.sarif.json

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
| `--aig-mode` | Enable AIG integration mode: run the three-stage pipeline and emit structured JSON to stdout for the Go backend (not needed for standalone use) | `false` |
| `-o, --output` | Save the scan result to a file; **SARIF 2.1.0 JSON when `--aig-mode` is off, internal-schema JSON when it's on** | — |

> `--aig-mode` is intended for the AI-Infra-Guard platform backend. When enabled, it runs the three-stage pipeline (Info Collection → Code Audit → Vulnerability Review) and writes `newPlanStep`/`statusUpdate`/`toolUsed` structured JSON lines to stdout; `-o` also saves the internal-schema JSON in this mode. Do **not** enable it when using `pip install` standalone — it will pollute your terminal with JSON.

### Output Format (SARIF)

**When `--aig-mode` is off (default, standalone CLI use)**, the result saved via `-o` is [SARIF 2.1.0](https://docs.oasis-open.org/sarif/sarif/v2.1.0/) — the OASIS Static Analysis Results Interchange Format standard JSON, natively consumable by GitHub Code Scanning, Azure DevOps, GitLab Security Dashboard, VS Code's Problems panel, and other SARIF-aware tooling.

```json
{
  "version": "2.1.0",
  "$schema": "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/main/Schemata/sarif-schema-2.1.0.json",
  "runs": [{
    "tool": {"driver": {"name": "aig-skill-scan", "version": "0.2.1", "rules": [...]}},
    "results": [{
      "ruleId": "T04",
      "level": "error",
      "message": {"text": "..."},
      "locations": [{"physicalLocation": {"artifactLocation": {"uri": "scripts/setup.sh"}, "region": {"startLine": 12, "endLine": 18}}}],
      "partialFingerprints": {"primaryLocationLineHash": "..."},
      "fixes": [{"description": {"text": "..."}}]
    }]
  }]
}
```

- `ruleId` comes from the vulnerability's `risk_type` (the SkillTrustBench T01–T09 category code)
- `level` is normalized from the free-text severity (Critical/High/Medium/...) into SARIF's `error`/`warning`/`note`
- `locations` relies on optional structured fields (file path + line numbers) emitted by the LLM; when they can't be determined, `uri` falls back to `"."`

`--aig-mode` mode is unaffected and continues to save the original internal JSON structure via `-o` (consumed by the platform internally).

### Programmatic Usage

```python
import asyncio
import json
import os
from skill_scan.agent.agent import Agent
from skill_scan.utils.llm import LLM
from skill_scan.utils.sarif_formatter import to_sarif

async def run():
    # API key must be read from environment variables, never hardcoded
    api_key = os.environ.get("LLM_API_KEY")
    if not api_key:
        raise RuntimeError("LLM_API_KEY environment variable must be set")

    llm = LLM(model="deepseek-v4-flash",
              api_key=api_key,
              base_url="https://openrouter.ai/api/v1",
              context_window=128_000)

    # Single-stage (default), aig_mode=False
    agent = Agent(llm=llm, debug=False, language="en", aig_mode=False)
    result = await agent.scan("/path/to/your/skill", "", "en")

    # Convert to SARIF 2.1.0 format
    sarif_doc = to_sarif(result, tool_version="0.2.1", language="en")
    print(json.dumps(sarif_doc, ensure_ascii=False, indent=2))

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
├── agent/              # Agent scan pipeline (single-stage by default, three-stage with --aig-mode)
│   ├── agent.py        # Agent class, scan entry point + stage dispatch
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
│   ├── sarif_formatter.py # Internal result → SARIF 2.1.0 conversion (used when --aig-mode is off)
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
