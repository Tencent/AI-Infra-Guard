# AIG × OpenClaw — 一句话完成 AI 安全扫描

[English](./README.md)

通过 OpenClaw 对话直接调用 [AIG (AI-Infra-Guard)](https://github.com/Tencent/AI-Infra-Guard/) 的全部扫描能力，无需打开 AIG Web UI。

> **前提**：已部署 AIG 服务（本机或远程均可）。

### 安装（在 OpenClaw 对话中说）

```
# 推荐：从 GitHub Releases 安装
帮我安装并启用 AIG Scanner
下载地址：
https://github.com/Tencent/AI-Infra-Guard/releases/download/aig-scanner-v2.0.0/aig-scanner-2.0.0.zip
```

备选方案：

```bash
# 从 ClawHub 安装
clawhub install aig-scanner
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

- **推荐安装方式**：优先使用带版本号的 GitHub Release `zip` 安装包，不要依赖分支 raw 文件，也不要使用仓库级 `latest` release 指针。
- **ClawHub**：可作为备选安装来源。在中国大陆环境下可能会遇到 `Rate limit exceeded`；如果出现这个问题，直接改用 GitHub `zip` 包。
- **AIG 地址**：首次安装时请配置 `AIG_BASE_URL`，这是必填项。例如：
  - `http://127.0.0.1:8088/`
  - `https://aig.example.com/`
- **认证**：AIG 开启认证时需配置 API Key，默认为空。
- **AI Tool / Skills Scan**：需要配置分析模型（model name、API key、base URL），首次使用时在对话中告知即可。
- **大模型安全体检**：需要同时提供目标模型和评估模型配置，包括 model name、API key、base URL。
- **Agent Scan**：扫描的是 AIG 平台上已配置的 Agent，暂不支持参数提交。
- **插件版**：已从主交付路径移出，备份保存在 `.artifacts/disabled-plugins/aig-scan-plugin/`。

### 维护说明

- Skill 源码放在 `integrations/openclaw/aig-scanner/`。
- 使用下面的脚本生成发布包：

```bash
./integrations/openclaw/build-release.sh
```

- 将生成的 `dist/aig-scanner-<version>.zip` 上传到 GitHub Releases。
- 发布到 ClawHub 时，使用源码目录，不要上传 zip 包。

---

扫描能力由腾讯朱雀实验室 [A.I.G](https://github.com/Tencent/AI-Infra-Guard) 提供
