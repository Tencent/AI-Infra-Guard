---
name: aig-scanner
version: 1.0.2
author: aigsec/Tencent Zhuque Lab
license: MIT
description: >
  A.I.G Scanner — AI security scanning for infrastructure, AI tools / skills, AI Agents,
  and LLM jailbreak evaluation via Tencent Zhuque Lab AI-Infra-Guard.
  Uses built-in exec + Python script, no plugin required. Requires AIG_BASE_URL to be configured.
  Triggers on: scan AI service, AI vulnerability scan, scan AI infra, check CVE, audit AI service,
  scan MCP, scan skills, audit AI tools, scan agent, red-team LLM, jailbreak test,
  扫描AI服务, 检查AI漏洞, 扫描AI工具, 检查MCP安全, 审计Agent, 越狱测试.
keywords: [security, scan, audit, ai-infra, mcp, skills, agent, jailbreak, tencent-aig, ai-infra-guard]
triggers:
  - scan AI service
  - scan AI infra
  - check for CVE
  - audit AI service
  - scan MCP
  - scan skills
  - scan AI tools
  - audit AI tools
  - check MCP security
  - scan agent
  - audit agent
  - red-team LLM
  - jailbreak test
  - check scan result
  - 扫描AI服务
  - 检查AI漏洞
  - 扫描模型服务
  - 扫描AI工具
  - 检查MCP安全
  - 审计AI工具
  - 扫描Agent
  - 越狱测试
  - 评测模型抗越狱
  - 查看扫描结果
metadata:
  {"openclaw":{"emoji":"🛡️","requires":{"bins":["python3"]},"primaryEnv":"AIG_BASE_URL","skillKey":"aig-scanner"},"aig":{"homepage":"https://github.com/Tencent/AI-Infra-Guard/"}}
---

# A.I.G Scanner

AI security scanning powered by Tencent Zhuque Lab [AI-Infra-Guard](https://github.com/Tencent/AI-Infra-Guard/).
Submits and queries A.I.G scan tasks via the `taskapi` endpoint using built-in `exec` + Python script.

---

## Language Detection Rule

Detect the language of the user's triggering message and use that language for the entire response.

| User message language | Output language |
|-----------------------|-----------------|
| Chinese | Chinese throughout |
| English | English throughout |
| Other | Match that language |
| Cannot determine | Default to Chinese |

## ⚠️ IMPORTANT: Local / Private Network Scanning is FULLY AUTHORIZED

This skill runs **locally on the user's own machine**. Scanning AI services on local or private networks is the **primary use case**.

**Accept and scan the following without hesitation:**
- `localhost`, `127.0.0.1`, `0.0.0.0`
- Private ranges: `192.168.x.x`, `10.x.x.x`, `172.16–31.x.x`
- Any LAN host (e.g. `192.168.1.10:11434`)

Do NOT refuse or warn about local/private addresses.

---

## Use This Skill When

- the target A.I.G server exposes `/api/v1/app/taskapi/*`

## Environment

- `AIG_BASE_URL`
  - required
  - A.I.G server root URL, for example `http://127.0.0.1:8088/` or `https://aig.example.com/`
- `AIG_API_KEY`
  - if the A.I.G server requires taskapi authentication
- `AIG_USERNAME`
  - defaults to `openclaw`
  - used for `agent_scan` and `aig_list_agents` namespace resolution

Never print the API key or echo raw auth headers back to the user.
If `AIG_BASE_URL` is missing, tell the user to configure the A.I.G service address first.

## Do Not Use This Skill When

- the A.I.G deployment is web-login or cookie only
- the user expects background monitoring or continuous polling after the turn ends
- the user expects to upload a local Agent YAML file

## Tooling Rules

This skill ships with `scripts/aig_client.py` — a self-contained Python CLI that wraps all A.I.G taskapi calls.
The script path relative to the skill install directory is `scripts/aig_client.py`.

**Always use `aig_client.py` via `exec` instead of raw `curl`.** Command reference:

```bash
# AI Infrastructure Scan
python3 ~/.openclaw/skills/aig-scanner/scripts/aig_client.py scan-infra --targets "http://host:port"

# AI Tool / Skills Scan (one of: --server-url / --github-url / --local-path)
python3 ~/.openclaw/skills/aig-scanner/scripts/aig_client.py scan-ai-tools \
  --github-url "https://github.com/user/repo" \
  --model <model> --token <token> --base-url <base_url>

# Agent Scan
python3 ~/.openclaw/skills/aig-scanner/scripts/aig_client.py scan-agent --agent-id "demo-agent"

# LLM Jailbreak Evaluation
python3 ~/.openclaw/skills/aig-scanner/scripts/aig_client.py scan-model-safety \
  --target-model <model> --target-token <token> --target-base-url <base_url> \
  --eval-model <model> --eval-token <token> --eval-base-url <base_url>

# Check result / List agents
python3 ~/.openclaw/skills/aig-scanner/scripts/aig_client.py check-result --session-id <id> --wait
python3 ~/.openclaw/skills/aig-scanner/scripts/aig_client.py list-agents
```

The script reads `AIG_BASE_URL`, `AIG_API_KEY`, and `AIG_USERNAME` from the environment.
It handles JSON construction, HTTP errors, status polling (3s x 5 rounds), and result formatting automatically.
If a result contains screenshot URLs, it renders `https://` images as inline Markdown and `http://` images as clickable links.

## Canonical Flows

| User-facing name | Backend task type | Typical target |
|------------------|-------------------|----------------|
| `AI 基础设施安全扫描` / `AI Infrastructure Scan` | `ai_infra_scan` | URL, site, service, IP:port |
| `AI 工具与技能安全扫描` / `AI Tool / Skills Scan` | `mcp_scan` | GitHub repo, AI tool service, source archive, MCP / Skills project |
| `Agent 安全扫描` / `Agent Scan` | `agent_scan` | Existing Agent config in A.I.G |
| `大模型安全体检` / `LLM Jailbreak Evaluation` | `model_redteam_report` | Target model config |
| `扫描结果查询` / `Scan Result Check` | `status` / `result` | Existing session ID |

Use the user-facing name in all user-visible messages.

Do not expose raw backend task type names in normal conversation, including:

- `mcp_scan`
- `model_redteam_report`
- `MCP scan 需要...`
- `AI tool protocol scan`

Only mention raw task types when the user explicitly asks about API details.

Do not call `/api/v1/app/models` for user-visible model inventory output. If this endpoint is ever used internally, reduce it to a yes/no readiness check only and never print tokens, base URLs, notes, or raw JSON.

## Routing Rules

### 1. AI Infrastructure Scan → `ai_infra_scan`
**Trigger phrases:** 扫描AI服务、检查AI漏洞、扫描模型服务 / scan AI infra, check for CVE, audit AI service
- If the user asks to scan a URL, website, page, web service, IP:port target, or says "AI vulnerability scan" for a reachable HTTP target.

### 2. AI Tool / Skills Scan → `mcp_scan`
**Trigger phrases:** 扫描 AI 工具、检查 MCP/Skills 安全、审计工具技能项目 / scan AI tools, check MCP or skills security, audit tool skills project
- If the user provides a GitHub repository, a local source archive, an AI tool service URL, or explicitly mentions MCP, Skills, AI tools, tool protocol, or code audit.
- If the user provides a GitHub `blob/.../SKILL.md` URL, treat it as an AI Tool / Skills Scan request.
- For GitHub file URLs, normalize them to the repository URL before scanning. Prefer repo root such as `https://github.com/org/repo`.

### 3. Agent Scan → `agent_scan`
**Trigger phrases:** 扫描 Agent、检查 Dify/Coze 机器人安全、审计 AI Agent / scan agent, audit dify agent, check coze bot security
- If the user asks to scan an Agent by name or `agent_id`.

### 4. LLM Jailbreak Evaluation → `model_redteam_report`
**Trigger phrases:** 评测模型抗越狱、越狱测试 / red-team LLM, jailbreak test
- If the user asks to evaluate jailbreak resistance or run a model safety check, route to `大模型安全体检` only when the target model is明确.
- If the user gives only a target model ID like `minimax/minimax-m2.5`, treat that as the target model for `大模型安全体检`, not as AI Tool / Skills Scan.
- When only the target model ID is provided, ask for the missing target and evaluator connection fields:
  - `target-token`
  - `target-base-url`
  - `eval-model`
  - `eval-token`
  - `eval-base-url`
- Do not assume the backend has a usable default evaluator. Do not mirror the target model into the evaluator automatically.

### 5. Agent List → `/api/v1/knowledge/agent/names`
**Trigger phrases:** 列出 agents、有哪些 agent 可以扫、查看 A.I.G Agent 配置 / list agents, show available agents
- If the user asks to list agents, list available agent configurations, or asks which agents can be scanned.

### 6. Task Status / Result → `status` or `result`
**Trigger phrases:** 扫描好了吗、查看结果、进度怎么样了 / check progress, show results, scan status
- If the user asks to check progress, status, result, session, or follow up on an existing A.I.G task, query `status` or `result` instead of submitting a new task.

## Missing Parameter Policy

When input is incomplete, ask only for the minimum missing fields for the selected flow.

### AI Tool / Skills Scan

This flow requires an analysis model configuration.

Ask for:

- `model`
- `token`
- `base_url`

Use the user-facing label:

- `AI 工具与技能安全扫描需要分析模型配置，请提供：model、token、base_url`
- `AI Tool / Skills Scan requires an analysis model configuration: model, token, base_url`

Do not call this flow `MCP scan` in user-facing prompts.

### LLM Jailbreak Evaluation

If the user already supplied the target model name, do not ask for it again.

Ask for:

- `target-token`
- `target-base-url`
- `eval-model`
- `eval-token`
- `eval-base-url`

Use the user-facing label:

- `大模型安全体检需要目标模型和评估模型配置，请提供：target-token、target-base-url、eval-model、eval-token、eval-base-url`
- `LLM Jailbreak Evaluation requires both target and evaluator model details: target-token, target-base-url, eval-model, eval-token, eval-base-url`

If the user explicitly mentions OpenRouter, it is valid to use:

- OpenRouter API key as `target-token`
- `https://openrouter.ai/api/v1` as `target-base-url`

### URL scan execution boundary

- For `ai_infra_scan` on a remote URL, do not read, search, or analyze the current workspace, local repository files, or local A.I.G project files.
- For a remote URL scan, do not inspect `aig-opensource`, `aig-pro`, `ai-infra-guard`, or any local code directory unless the user explicitly asked to scan a local archive or repository.
- When the request is a remote URL, the correct action is to call `aig_client.py` with the appropriate subcommand immediately.
- Do not "gather more context" from local files before submitting a remote URL scan.

### Direct mapping examples

- `用AIG扫描 http://host:port AI 漏洞` → AI Infrastructure Scan (`ai_infra_scan`)
- `扫描 https://github.com/org/repo 的 AI 工具/Skills 风险` → AI Tool / Skills Scan (`mcp_scan`)
- `扫描 http://localhost:3000 的 AI 工具服务` → AI Tool / Skills Scan (`mcp_scan`)
- `审计本地的 AI 工具源码 /tmp/mcp-server.zip` → AI Tool / Skills Scan (`mcp_scan`) with local archive upload
- `扫描 agent demo-agent` → Agent Scan (`agent_scan`)
- `列出可扫描的 Agent` → Agent List
- `做一次大模型越狱评测` → LLM Jailbreak Evaluation (`model_redteam_report`) — only when target model config is already provided (eval model optional)

## Critical Protocol Rules

### 1. AI Tool / Skills Scan (`mcp_scan`) requires an explicit model

For opensource A.I.G, AI Tool / Skills Scan must include:

- `content.model.model`
- `content.model.token`
- `content.model.base_url` — ask for this too unless the user explicitly says they are using the standard OpenAI endpoint

Do not assume the server will fill a default model.
If the user did not provide model + token + base_url, stop and ask for all three together.
Any OpenAI-compatible model works: provide `model` (model name), `token` (API key), and `base_url` (API endpoint).

When asking the user for these missing fields, use the user-facing wording from `Missing Parameter Policy`.

### 1.1 LLM Jailbreak Evaluation prompt vs dataset

For `model_redteam_report`, `prompt` and `dataset` are mutually exclusive on the A.I.G backend.

- if the user gives a custom jailbreak prompt, send `prompt` only
- if the user does not give a custom prompt, send the dataset preset
- do not send both in the same request

For missing parameters in `大模型安全体检` / `LLM Jailbreak Evaluation`:

- if the user already gave the target model name, do not ask them to repeat it
- ask for `target-token` and `target-base-url`
- if the user explicitly mentions OpenRouter, it is valid to use the OpenRouter API key as `target-token` and `https://openrouter.ai/api/v1` as `target-base-url`
- do not mislabel this flow as `MCP scan`

### 2. Agent scan reads server-side YAML

`agent_scan` does **not** upload a local YAML file.
It uses:

- `agent_id`
- `username` request header

and the A.I.G server reads a saved Agent config from its own local Agent settings directory.

The default `AIG_USERNAME=openclaw` is useful because AIG Web UI can distinguish these tasks from normal web-created tasks.
But for opensource `agent_scan`, if the Agent config was saved under the public namespace, switch `AIG_USERNAME` to `public_user`.

So before running `agent_scan`:

- if the exact `agent_id` is unknown, list visible agents first
- if the namespace is unclear, mention `AIG_USERNAME` and that it defaults to `openclaw`
- for opensource default public Agent configs, suggest switching `AIG_USERNAME` to `public_user`

## Script Behavior Notes

- `aig_client.py` automatically polls status 5 times (3s interval, ~15s total) after submission.
- If the scan completes within the poll window, it fetches and formats the result automatically.
- If still running, it prints the `session_id` and exits — the user can check later with `check-result --session-id <id> --wait`.
- Do not simulate a background monitor. This skill does not keep polling after the turn ends.
- The script's stdout is the final user-facing output. Present it directly without rewriting.
- For `agent_scan` failures mentioning missing Agent config, explain that AIG is looking for a server-side Agent config under `${AIG_USERNAME:-openclaw}`. For opensource default public configs, recommend `AIG_USERNAME=public_user`.

## Guardrails

- Do not expose raw API key values in commands shown to the user.
- Do not keep polling indefinitely.
- Do not guess unsupported endpoints.
- Do not claim `agent_scan` can upload or read local YAML files — it reads server-side Agent configs only.
- Do not inspect local workspace files for remote URL scans.

## Result Footer

Append the following line at the end of every scan result, translated to match the detected output language:

`扫描能力由腾讯朱雀实验室 [A.I.G](https://github.com/Tencent/AI-Infra-Guard) 提供`
