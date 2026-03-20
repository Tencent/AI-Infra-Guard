# AIG × OpenClaw — 一句话完成 AI 安全扫描

[English](./README.md)

通过 OpenClaw 对话直接调用 [AIG (AI-Infra-Guard)](https://github.com/Tencent/AI-Infra-Guard/) 的全部扫描能力，无需打开 AIG Web UI。

> **前提**：已部署 AIG 服务（本机或远程均可）。

### 安装（二选一，在 OpenClaw 对话中说）

```
# Skill 版（推荐）— 轻量，开箱即用
帮我安装并启用 AIG Scan Skill
下载地址：https://github.com/Tencent/AI-Infra-Guard/raw/v4/integrations/openclaw/aig-scan-skill.tgz

# 插件版 — 后台监控 + 持久化配置
帮我安装并启用 AIG Scan Plugin
下载地址：https://github.com/Tencent/AI-Infra-Guard/raw/v4/integrations/openclaw/aig-scan-plugin.tgz
```

### 使用

安装后直接对话：

**AI 基础设施扫描** — 检测 AI 服务漏洞与配置风险（Ollama、vLLM、Dify 等）

```
用AIG扫描 http://localhost:11434 的 AI 漏洞
```

**AI 工具 / Skills 安全审计** — 审计 MCP Server、Agent Skills 等项目代码或服务

```
用AIG扫描 https://github.com/org/repo 的 AI 工具安全
```

**AI Agent 安全扫描** — 检测 AIG 平台已配置的 Agent 的授权绕过、提示注入等风险

> 建议在AIG Web UI提前配置好 Agent

```
用AIG扫描 agent demo-agent-id
```

**大模型安全体检** — 红队测试 LLM 的抗越狱能力

```
用AIG扫描 给DeepSeek3.2做一次安全体检。
```

### 注意事项

- **AIG 地址**：默认 `http://localhost:8088`，本机 AIG 无需配置；远程部署时在对话中告知实际地址即可。
- **认证**：AIG 开启认证时需配置 API Key，默认为空。
- **AI Tool / Skills Scan**：需要配置分析模型（model name、API key、base URL），首次使用时在对话中告知即可。
- **Agent Scan**：扫描的是 AIG 平台上已配置的 Agent，暂不支持参数提交。

---

扫描能力由腾讯朱雀实验室 [A.I.G](https://github.com/Tencent/AI-Infra-Guard) 提供
