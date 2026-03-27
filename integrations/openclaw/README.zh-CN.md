# A.I.G × OpenClaw — 一句话完成 AI 安全扫描

[English](./README.md)

通过 OpenClaw 对话直接调用 [A.I.G (AI-Infra-Guard)](https://github.com/Tencent/AI-Infra-Guard/) 的全部扫描能力，无需打开 A.I.G Web UI。

> **前提**：已部署 A.I.G 服务（本机或远程均可）。

### 安装

```bash
clawhub install aig-scanner
```

备选方案：

```text
从这个源码目录安装 skill：
https://github.com/Tencent/AI-Infra-Guard/tree/main/integrations/openclaw/aig-scanner
```

### 使用

安装后直接对话：

**AI 基础设施扫描** — 检测 AI 服务漏洞与配置风险（Ollama、vLLM、Dify 等）

```
用A.I.G扫描 http://localhost:11434 的 AI 漏洞
```

**AI 工具 / Skills 安全审计** — 审计 MCP Server、Agent Skills 等项目代码或服务

```
用A.I.G扫描 https://github.com/org/repo 的 AI 工具安全
```

**AI Agent 安全扫描** — 检测 A.I.G 平台已配置的 Agent 的授权绕过、提示注入等风险

> 建议在 A.I.G Web UI 提前配置好 Agent

```
用A.I.G扫描 agent demo-agent-id
```

**大模型安全体检** — 红队测试 LLM 的抗越狱能力

```
用A.I.G扫描 给DeepSeek3.2做一次安全体检。
```

### 注意事项

- **推荐安装方式**：优先使用 ClawHub。
- **中国大陆环境回退方案**：如果 ClawHub 遇到 `Rate limit exceeded`，直接使用本仓库中的源码目录安装。
- **A.I.G 地址**：首次安装时请配置 `AIG_BASE_URL`，这是必填项。例如：
  - `http://127.0.0.1:8088/`
  - `https://aig.example.com/`
- **认证**：A.I.G 开启认证时需配置 API Key，默认为空。
- **AI Tool / Skills Scan**：需要配置分析模型（model name、API key、base URL），首次使用时在对话中告知即可。
- **大模型安全体检**：需要同时提供目标模型和评估模型配置，包括 model name、API key、base URL。
- **Agent Scan**：扫描的是 A.I.G 平台上已配置的 Agent，暂不支持参数提交。

### 维护说明

- Skill 源码放在 `integrations/openclaw/aig-scanner/`。
- 发布到 ClawHub 时，使用源码目录。
- 保持仓库源码优先，不要提交打包压缩文件。

---

扫描能力由腾讯朱雀实验室 [A.I.G](https://github.com/Tencent/AI-Infra-Guard) 提供
