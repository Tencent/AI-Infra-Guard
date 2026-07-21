# MCP-Scan

English | **[中文](./README_zh.md)**

> An AI Agent-driven automated MCP Server security scanning and vulnerability detection tool, developed by Tencent Zhuque Lab.

## ✨ Features

- **🤖 Intelligent Agent System**: Supports single-stage (fast code audit) and three-stage (Info Collection → Code Audit → Vulnerability Review) scanning modes
- **🔍 Deep Code Analysis**: Automatically identifies project structure, tech stack, and potential security vulnerabilities
- **📊 SARIF 2.1.0 Output**: CLI mode outputs SARIF 2.1.0 JSON by default, natively consumable by GitHub Code Scanning, Azure DevOps, VS Code, and more
- **🔌 AIG Platform Integration**: Interactive scanning via the Web UI with real-time three-stage pipeline results
- **🎯 Dedicated Model Configuration**: Configure specialized LLMs for different tasks (thinking, coding, fast response, etc.)
- **📊 Security Scoring System**: Automatically calculates project security scores and risk levels
- **🛠️ Extensible Tool System**: Easily add custom tools and features
- **📝 Detailed Logging**: Full execution process logged with loguru
- **🐛 Debug Mode**: Integrated Laminar tracing for easy debugging
- **🕵️ Agent Skill Auditing**: Automatically detects and audits Agent Skill project consistency (SKILL.md vs code implementation)
- **⚡ Static Pre-scan**: Regex-based scanning for high-risk patterns (curl|bash, cloud metadata, credential theft, etc.) before Agent launch, generating prompt injection context

## 🚀 Quick Start

### 1. Clone the Project

```bash
git clone <your-repo>
cd mcp-scan
```

### 2. Install Dependencies

Recommended using `uv` (faster, auto-manages virtual environments):

```bash
uv sync
```

Or using pip:

```bash
pip install -r requirements.txt
```

### 3. Run a Scan

mcp-scan supports two usage modes:

#### Mode 1: Standalone CLI (default single-stage mode)

Outputs SARIF 2.1.0 JSON to stdout by default, suitable for CI/CD integration and fast scanning:

```bash
# Basic scan
python main.py --repo ./myproject

# Save results to a file
python main.py --repo ./myproject -o result.sarif.json

# Use a specific model
python main.py --repo ./myproject -m "anthropic/claude-3.5-sonnet"

# Provide API Key via environment variable (no --api_key needed)
export LLM_API_KEY="sk-or-v1-xxxxx"
python main.py --repo ./myproject

# Use a custom prompt
python main.py --repo ./myproject --prompt "Focus on SQL injection vulnerabilities"

# Enable debug mode
python main.py --repo ./myproject --debug

# Combined usage
python main.py --repo ./myproject \
  -m "google/gemini-2.5-pro" \
  -p "Focus on authentication and authorization issues" \
  --debug \
  -o report.sarif.json

# Dynamic analysis (targeting a running MCP Server)
python main.py \
  --server_url "http://localhost:8000/sse" \
  --prompt "Test tool poisoning vulnerabilities"
```

> **CLI mode characteristics**: Uses **single-stage scanning** by default (code audit only, ~3x faster than three-stage), outputs **SARIF 2.1.0** JSON, natively consumable by GitHub Code Scanning, Azure DevOps, GitLab Security Dashboard, VS Code Problems panel, and other SARIF-aware tools.

#### Mode 2: AIG Platform Web UI (three-stage mode)

mcp-scan is integrated into the AIG platform, enabling interactive scanning via the Web UI with real-time three-stage pipeline results displayed on the frontend.

**Steps:**

1. **Start the AIG Web service and Agent process**

```bash
# Start the Web service
go build -o ai-infra-guard ./cmd/cli/main.go
./ai-infra-guard webserver --server 127.0.0.1:8088

# In another terminal, start the Agent process
go build -o agent ./cmd/agent
AIG_SERVER=127.0.0.1:8088 ./agent
```

2. **Use via browser**

Open your browser and navigate to `http://127.0.0.1:8088`:

- Select **MCP Scan** from the left sidebar
- Add your LLM API Key and model name (e.g., `deepseek-v4-flash`) in **Model Configuration**
- Choose input method: upload a source code archive (.zip) or enter a GitHub repository URL
- Click **Start Scan**

3. **View results**

During the scan, the three-stage pipeline (Info Collection → Code Audit → Vulnerability Review) progress and results are displayed in real-time on the Web frontend, culminating in a complete report with vulnerability details, risk levels, and a security score.

> **How it works**: When a scan task is submitted from the Web UI, the Go backend dispatches it to the Agent process, which automatically invokes mcp-scan with `--aig-mode`. Structured JSON logs are output to stdout via `mcpLogger`, parsed by the Go backend, and pushed to the frontend in real-time. Users do not need to manually run the `--aig-mode` command.

## 📖 CLI Options Reference

| Option | Shorthand | Description | Default |
|--------|-----------|-------------|---------|
| `--repo` | - | **Required** for static scanning. Path to the project to scan (can be omitted when using `--server_url` for dynamic analysis) | - |
| `--prompt` | `-p` | Custom scan prompt | "" |
| `--model` | `-m` | LLM model name | `deepseek/deepseek-v3.2-exp` |
| `--api_key` | `-k` | API key (falls back to env vars `LLM_API_KEY`/`OPENAI_API_KEY`/`OPENROUTER_API_KEY`) | From env vars |
| `--base_url` | `-u` | API base URL | `https://openrouter.ai/api/v1` |
| `--debug` | - | Enable debug mode (includes Laminar tracing) | `False` |
| `--server_url` | - | Remote MCP server URL (enables dynamic analysis mode) | `None` |
| `--header` | - | Custom HTTP header (key:value), can be used multiple times | `[]` |
| `--language` | - | Output language (zh/en) | `zh` |
| `--aig-mode` | - | Enable AIG integration mode: outputs structured JSON logs for the Go backend. Automatically invoked by the AIG platform; not needed for standalone CLI use | `False` |
| `--output` | `-o` | Save scan results to a JSON file | `None` |

> **Configuration priority** (high to low): CLI arguments > Environment variables > Code defaults

## 📊 SARIF Output Format

CLI mode outputs **SARIF 2.1.0** JSON by default, containing:

- **rules**: Statically declares the full MCP01–MCP10 + 3 supplemental classification rules (Name Confusion, Rug Pull, Tool Shadowing), always output even if no vulnerabilities are found
- **results**: Each vulnerability maps to a rule ID, including `level` (error/warning/note), `locations` (file + line number), `partialFingerprints` (dedup hash), and `fixes` (fix suggestions)
- **properties**: Security score, primary language, LLM used, scan duration

SARIF files can be uploaded directly to GitHub Code Scanning:

```bash
# GitHub Actions example
python main.py --repo ./myproject -o results.sarif.json
# Then use github/codeql-action/upload-sarif@v3 in your workflow
```

### MCP Risk Classification

mcp-scan uses 10 MCP-specific security risk categories plus 3 supplemental classifications:

| Rule ID | Name | Description |
|---------|------|-------------|
| MCP01 | Token & Secret Exposure | Credential theft and key leakage |
| MCP02 | Privilege Escalation & Scope Creep | Overly broad tool permission definitions |
| MCP03 | Tool Poisoning Attack | Legitimate tools injected with malicious logic |
| MCP04 | Supply Chain Attack | Dependency tampering, malicious third-party servers |
| MCP05 | Command Injection & Execution | Untrusted input constructing system commands |
| MCP06 | Prompt Injection Attack | Context-injected malicious instructions hijacking the model |
| MCP07 | Insufficient Auth & Authorization | Missing identity verification leading to privilege escalation |
| MCP08 | Missing Audit & Telemetry | Lack of tamper-proof call logs |
| MCP09 | Shadow MCP Server | Unauthorized MCP instances deployed |
| MCP10 | Context Injection & Over-sharing | Sensitive context leaking across sessions |
| Name Confusion | Name Confusion Attack | Similar names inducing incorrect tool calls |
| Rug Pull Attack | Rug Pull Attack | Changing behavior after gaining trust |
| Tool Shadowing Attack | Tool Shadowing Attack | Redefining same-named tools to override legitimate behavior |

## ⚙️ Configuration

Create a `.env` file or set environment variables in your system. The program auto-loads `.env` on startup and also recognizes system environment variables.

#### Main LLM Configuration

```bash
# OpenRouter API Key (required)
OPENROUTER_API_KEY=your-api-key-here

# Default model
DEFAULT_MODEL=deepseek/deepseek-v3.2-exp

# API base URL
DEFAULT_BASE_URL=https://openrouter.ai/api/v1
```

#### Dedicated LLM Configuration

Configure specialized models for different tasks, each with its own API key and base URL:

```bash
# Thinking model (for deep reasoning)
THINKING_MODEL=google/gemini-2.5-pro
THINKING_BASE_URL=https://openrouter.ai/api/v1
THINKING_API_KEY=  # Optional, uses main API key if not set

# Coding model (for code generation and analysis)
CODING_MODEL=anthropic/claude-sonnet-4.5
CODING_BASE_URL=https://openrouter.ai/api/v1
CODING_API_KEY=  # Optional, uses main API key if not set
```

#### Debug & Logging Configuration

```bash
# Laminar API Key (for debug mode tracing)
LAMINAR_API_KEY=your-laminar-api-key

# Log level
LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR
```

## 📁 Project Structure

```
mcp-scan/
├── agent/                  # Agent core implementation
│   ├── agent.py           # Main Agent (single-stage/three-stage scan dispatch)
│   └── base_agent.py      # Base Agent class (challenge mechanism + result truncation)
├── tools/                  # Tool modules
│   ├── registry.py        # Tool registration system
│   ├── thinking/          # Thinking tool
│   ├── finish/            # Finish tool
│   ├── file/              # File operation tools
│   └── execute/           # Code execution tools
├── utils/                  # Utility functions
│   ├── config.py          # Configuration management
│   ├── llm.py             # LLM base wrapper
│   ├── llm_manager.py     # LLM manager (multi-model support)
│   ├── loging.py          # Logging configuration
│   ├── parse.py           # XML parsing
│   ├── project_analyzer.py # Project analysis tools
│   ├── extract_vuln.py    # Vulnerability extraction (structured file/line localization)
│   ├── pre_scan.py        # Static pre-scan (14 high-risk pattern regex detection)
│   ├── sarif_formatter.py # SARIF 2.1.0 formatter (MCP01-MCP10 rule system)
│   ├── tool_context.py    # Tool context
│   └── aig_logger.py      # Structured logging
├── prompt/                 # Prompt templates
│   ├── system_prompt.md   # System prompt
│   ├── agents/            # Per-stage Agent prompts
│       ├── project_summary.md # Info collection (incl. Skill detection)
│       ├── code_audit.md      # Code audit (incl. Skill consistency audit)
│       └── vuln_review.md     # Vulnerability review
├── main.py                 # Main entry (with --aig-mode and SARIF output logic)
├── pyproject.toml          # Project config (version 0.2.0, Python >=3.9)
├── py.typed                # PEP 561 type marker
├── requirements.txt        # Dependencies
├── env.example            # Environment variable template
└── README.md              # This document
```

## 🔧 How It Works

### Scan Modes

mcp-scan supports two scanning modes, switched via the `--aig-mode` flag:

#### Single-Stage Mode (CLI default, without `--aig-mode`)

```
1. Static Pre-scan
   ├── Regex scan for 14 high-risk pattern categories
   └── Generate prompt injection Agent context

2. Code Audit
   ├── Inject project directory tree as context
   ├── LLM-driven deep code analysis
   ├── Challenge mechanism to detect sensitive patterns in tool results
   └── Tool result truncation to prevent context overflow

3. Output SARIF 2.1.0 JSON
```

~3x faster than three-stage, suitable for CI/CD integration and quick scans.

#### Three-Stage Mode (`--aig-mode`)

```
1. Information Collection
   ├── Analyze project structure
   ├── Identify tech stack
   └── Identify project type (regular project / Agent Skill)

2. Code Audit
   ├── Deep code analysis
   ├── Identify security issues
   └── If Agent Skill, perform consistency audit (Intent Alignment Check)

3. Vulnerability Review
   ├── Consolidate discovered vulnerabilities
   ├── Assess risk levels
   └── Generate detailed report
```

Outputs structured JSON to stdout via `mcpLogger` for the AIG platform Go backend to parse.

### Agent Skill Audit

If a `SKILL.md` file exists in the project root, the tool automatically triggers an **Agent Skill consistency audit**:
- **Intent Alignment**: Compares `SKILL.md` descriptions with code implementations in `scripts/`.
- **Hidden Behavior Detection**: Checks for hidden functionality not mentioned in the description.
- **Output Format Validation**: Verifies code output matches the described expected format.

## 🤝 Development

It is recommended to use `uv` for local development environment management (supports Python >=3.9).
To initialize the dev environment:

```bash
uv sync --extra dev --extra test
```

Before committing, it is recommended to run at least:

```bash
uv run ruff check . --fix
uv run ruff format .
```

### Running Tests

```bash
uv run pytest
```

### Viewing Logs

Log files are located in the project root directory, named `agent_YYYYMMDD_HHMMSS.log`.

## 📄 License

MIT License

## 🙏 Acknowledgments

Tencent Zhuque Lab AI-Infra-Guard project team.

---

**Note**: This tool is intended for legitimate security testing and code auditing only. Do not use it for unauthorized system testing.
