# AI-Infra-Guard 系统架构演进（v0.1 / v2.6 / v3.6.0）

> 说明：以下架构描述基于对应版本的代码目录结构与 README 文档梳理，聚焦核心模块与系统边界。

## v0.1 架构概览

**定位**：轻量化 AI 基础设施漏洞扫描工具，提供 CLI 与 WebUI 入口。

**核心架构分层**

1. **交互层**
   - CLI 入口：`cmd/` 下的命令行执行流程
   - WebUI：`common/websocket` 提供 WebSocket 服务与静态资源
2. **扫描与规则引擎层**
   - 指纹识别与漏洞匹配：`common/fingerprints`
   - 扫描执行与任务调度：`common/runner`
3. **基础能力层**
   - 通用工具库：`common/utils`
   - HTTP/指纹探测能力：`pkg/`（网络请求与扫描相关实现）
4. **数据与规则层**
   - 组件指纹：`data/fingerprints`
   - 漏洞规则：`data/vuln`

**简化调用链（文字示意）**

```
CLI/WebUI
   -> Runner 调度
      -> 指纹识别
         -> 漏洞匹配
            -> 结果输出
```

---

## v2.6 架构概览

**定位**：在 v0.1 的基础上新增 MCP Server 安全检测能力，形成“扫描 + MCP 代码分析 + WebUI”三大模块。

**核心架构分层**

1. **交互层**
   - CLI 子命令体系（`scan` / `mcp` / `webserver`）
   - WebUI：仍由 `common/websocket` 提供服务
2. **安全检测层**
   - **AI 组件漏洞扫描**：延续 v0.1 的指纹识别与漏洞匹配流程
   - **MCP Server 代码检测**：新增基于 AI Agent 的安全分析流程（由 CLI 参数驱动）
3. **基础能力层**
   - 通用工具与任务执行：`common/utils`、`common/runner`
   - 组件指纹与规则引擎：`common/fingerprints`
4. **数据与规则层**
   - 指纹规则：`data/fingerprints`
   - 漏洞库：`data/vuln`

**简化调用链（文字示意）**

```
CLI
  -> scan: Runner -> 指纹识别 -> 漏洞匹配
  -> mcp : 代码分析 Agent -> 风险报告
WebUI
  -> WebSocket API -> 调用 scan/mcp
```

---

## v3.6.0 架构概览

**定位**：完整 AI 红队平台化版本，形成“基础设施扫描 + MCP 生态安全 + Prompt 安全评测 + Web 平台”的多模块体系。

**核心架构分层**

1. **接入层**
   - CLI：`cmd/cli`，覆盖扫描、MCP、安全评测等入口
   - Agent 服务：`cmd/agent`（独立 Agent 运行时）
   - WebUI 与 API：`common/websocket` + `docs/swagger` 接口文档
2. **核心能力层**
   - **基础设施扫描**：`common/fingerprints` + `common/runner`
   - **MCP 安全分析**：`mcp-scan/`（Agent 驱动的代码审计与动态分析流程）
   - **Prompt 安全评测**：`AIG-PromptSecurity/`（评测数据集与攻击算子）
3. **服务与中间件层**
   - 中间件与鉴权：`common/middleware`
   - TRPC / 通信适配：`common/trpc`
   - Agent 管理：`common/agent`
4. **数据与规则层**
   - 基础设施指纹与漏洞库：`data/fingerprints`、`data/vuln`
   - MCP 规则与测试样例：`data/mcp`、`mcp-testcase`
   - Prompt 评测数据：`data/eval`

**简化调用链（文字示意）**

```
WebUI / CLI
  -> 调度层（Runner / Agent）
     -> 基础设施扫描（指纹 + 漏洞规则）
     -> MCP 安全分析（mcp-scan Agent）
     -> Prompt 安全评测（AIG-PromptSecurity）
  -> 报告输出（API / Web 展示）
```

---

## 版本对比要点（简表）

| 版本 | 主要能力 | 架构特征 |
| --- | --- | --- |
| v0.1 | 基础设施漏洞扫描 + WebUI | 单一扫描引擎 + 规则驱动 |
| v2.6 | 扫描 + MCP 代码检测 | CLI 子命令化 + AI Agent 介入 |
| v3.6.0 | 扫描 + MCP + Prompt 安全评测 | 平台化、多模块协作、Agent 体系完善 |
