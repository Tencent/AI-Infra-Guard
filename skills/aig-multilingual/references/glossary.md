# AIG Multilingual Glossary — Do Not Translate

## Brand & Product Names
These terms must appear verbatim in ALL language versions. Never localize, transliterate, or adapt them.

| Term | Notes |
|------|-------|
| `A.I.G` | Always with dots. Never write `AIG` in prose. |
| `AI-Infra-Guard` | Hyphenated, exact casing. |
| `ClawScan` | One word, CamelCase. |
| `EdgeOne ClawScan` | Two words, never split or merged. |
| `Zhuque Lab` | Keep English form. Chinese `朱雀实验室` allowed only in Chinese README. |
| `Tencent` | Keep English in all non-Chinese versions. |
| `OpenClaw` | Keep English. |
| `TutorBot` | Keep English. |

## Security / AI Technical Terms
Keep in English across all languages (do not translate or transliterate).

| Term | Bad Example |
|------|-------------|
| `MCP` | ~~MCP-Server~~ (DE), ~~MCP서버~~ (KR) |
| `MCP Server` | No hyphen, no camelCase merge |
| `Agent` / `Agent Scan` | ~~에이전트 스캔~~ preferred form is `Agent Scan` |
| `LLM` | Never spell out in non-EN languages |
| `RAG` | Never localize |
| `CVE` | Never localize |
| `GHSA` | Never localize |
| `PoC` | Never localize |
| `Jailbreak` / `Jailbreak Evaluation` | Keep English |
| `AIG-PromptSecurity` | Directory name, keep exact |
| `mcp-scan` | Module name, keep exact |
| `agent-scan` | Module name, keep exact |
| `ClawHub` | Keep English |
| `DeepWiki` | Keep English |

## Infrastructure / Ecosystem Terms

| Term | Notes |
|------|-------|
| `Docker` | Never localize |
| `GitHub` | Never localize |
| `WebSocket` | Never localize |
| `Python` / `Go` | Never localize |
| `CLI` | Keep as is |
| `API` | Keep as is |
| `HTTP` / `HTTPS` | Keep as is |

## Version Numbers & Dates
- Version tags like `v4.1.3` — keep verbatim
- Dates like `2026-04-09` — keep ISO format, do not localize to local date conventions
- Changelog section headers — keep English if they are anchor-link targets

## Code Blocks
Everything inside ` ```bash `, ` ```yaml `, ` ```json `, ` ```go `, ` ```python ` etc. must be **100% identical** to the English source. No exceptions.
