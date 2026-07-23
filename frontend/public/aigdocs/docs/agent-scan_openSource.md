# Agent 安全扫描

## 简介

Agent 安全扫描提供面向 AI Agent 的一键安全检测，基于红队即服务（RTaaS）驱动的 Agent 能力，通过多阶段流水线（信息收集 → 漏洞检测 → 验证整理）自动发现授权绕过、数据泄露、间接注入、工具滥用等风险，并生成标准化报告。

目前支持 Dify、Coze、自定义 HTTP 等多种 Agent 接入方式。检测结果按 OWASP Top 10 for Agentic Applications 标准分类定级，帮助开发者快速识别并修复 Agent 类应用的安全问题。

## 快速开始

![Agent 安全扫描主界面](./assets/image-agentscan.png)

1. **选择任务类型**：在主界面点击「Agent 安全扫描」进入扫描页面。  
2. **配置规划模型与目标 Agent**：
    - **目标 Agent**：选择或添加待检测的 Agent（Dify / Coze / HTTP 等，详见 [Agent 配置](#1-agent-配置)）。
   - **规划模型（LLM）**：扫描流程由大模型驱动任务规划与多阶段推理（信息收集、漏洞检测、漏洞整理），需配置用于扫描的规划模型，包括模型名称、API 地址、API Key 等（详见 [规划模型配置](#2-规划模型配置)）。  
3. **启动扫描并查看报告**：点击「开始扫描」，等待任务完成后在报告页查看漏洞列表、风险等级及修复建议。  

## 详细配置介绍

### 1. Agent 配置

**配置入口**：`设置` → `Agent配置` → `新增/上传YAML`

系统支持两种配置方式：
- **界面配置**：通过表单填写 Agent 信息（推荐）
- **YAML 文件上传**：上传 YAML 配置文件导入 Agent 配置

![Agent 配置入口](./assets/image-agentscan-config.png)

#### YAML 文件上传

支持通过 YAML 文件导入 Agent 配置，适用于复用配置或通过代码生成配置的场景。**可在配置界面下载样例 YAML 文件**。

**YAML 文件格式示例**：

**Dify Agent 示例**：
```yaml
targets:
  - id: dify
    config:
      label: "DifyAgent(支持英文及数字)"
      dify_type: chat
      apiBaseUrl: "https://api.dify.ai/v1"
      apiKey: "app-xxxx"
      extra:
        user: agent-user
        conversation_id: ""
        inputs: "{}"
      timeout_ms: 60000
      delay: 0
```

**配置说明**：
- **文件格式**：支持 YAML 或 JSON 格式
- **字段说明**：
  - `targets`：Agent 配置列表
  - `id`：Agent 类型标识（如 `dify`、`http`）
  - `label`：Agent 显示名称
  - `config`：具体配置项（API Key、URL、请求头等）
- **配置验证**：上传后系统会自动校验配置有效性，失败会提示错误信息

#### 支持的接入方式

系统支持多种 Agent 接入方式，包括：
- **Dify AI**：Dify 平台的应用对话接口
- **Coze AI**：扣子（Coze）平台的机器人
- **HTTP接口**：自定义 HTTP 对话端点（详见 [HTTP 接口配置指南](?menu=agent-scan-http-config)）

#### 基础配置（必填）

所有 Agent 类型均需填写以下基础配置：

- **Agent名称**：Agent 的自定义名称，用于标识和管理，需保证唯一性
- **API-Key**：目标 Agent 的认证密钥
  - Dify：参考格式为 `app-xxxx`
  - Coze：参考格式为 `pat-xxxx`
  - HTTP：根据目标接口的认证方式填写（可在请求头中配置，详见 [HTTP 接口配置指南](?menu=agent-scan-http-config)）

#### 高级配置（选填）

不同 Agent 类型的高级配置项略有差异：

**Dify AI**：
- **Dify端点类型**：选择端点类型，默认 `聊天消息`（Chat 模式）
- **API基础URL**：API 服务地址，默认 `https://api.dify.ai/v1`；非公网部署需修改为实际地址
- **用户ID**：用于标识对话用户，默认 `agent-user`
- **对话ID**：留空则每次扫描开始新对话；填写已有对话 ID 可继续历史对话
- **自定义输入**：JSON 格式的额外输入参数，如 `{"key": "value"}`
- **超时时间（毫秒）**：请求超时时间，默认 `60000`（60 秒）
- **延迟（毫秒）**：每次请求间的延迟时间，默认 `0`

**HTTP接口**：配置项包括请求头、请求体模板、响应解析器等，详见 [HTTP 接口配置指南](?menu=agent-scan-http-config)。

> **说明**：Coze AI 和其他内网平台的高级配置项会有所不同，具体以界面提示为准。



#### Agent 接入验证

配置完成后，可选择使用「Agent接入验证」功能进行快速测试：

- 在「Prompt Input」输入框中输入测试 prompt
- 点击「运行测试」按钮，查看 Agent 的回复是否正确
- 验证通过后再启动正式扫描，避免因配置错误导致扫描失败

![Agent 接入测试界面](./assets/image-agentscan-chat-demo.png)

**连通性校验**：保存或启动扫描前，系统会自动对目标 Agent 进行连通性测试；若失败会提示配置无效，需检查 Agent 配置是否正确。


### 2. 规划模型配置

扫描模块采用 LLM 驱动的多阶段流水线：由规划模型负责任务拆解、检测策略与报告生成等推理与规划，因此需要单独配置「用于执行扫描的」大语言模型。

- **支持的模型类型**：兼容 OpenAI API 格式的模型
- **配置参数**：
  - 模型名称，例如：`deepseek/deepseek-v3.2`、`moonshotai/kimi-k2.5`
  - API 基础 URL，例如：`https://openrouter.ai/api/v1`
  - API 密钥

> **说明**：该模型仅用于扫描引擎的规划与推理，与「被检测的目标 Agent」相互独立；目标 Agent 的对话能力由其在 [Agent 配置](#1-agent-配置) 中的接入方式决定。

![规划模型配置](./assets/image-agentscan-process.png)


### 3. 报告展示

任务完成后，报告页会展示完整的扫描结果与安全分析。

![Agent 扫描报告风险总览](./assets/image-prompt-report-main.png)

#### 基本信息

- **扫描目标**：被检测的 Agent 名称
- **使用模型**：用于扫描的规划模型名称
- **扫描时间**：任务执行的开始时间
- **扫描时长**：任务执行的总耗时

#### 风险概览

- **风险等级**：整体风险等级（高危/中危/低危/安全）
- **安全评分**：0-100 分的综合安全评分
- **发现漏洞**：检测到的漏洞总数
- **风险等级分布**：按高危/中危/低危统计的漏洞数量分布
- **风险分类分布**：按 OWASP Top 10 for Agentic Applications（ASI01–ASI10）统计的漏洞分布

#### 漏洞详情

每条漏洞包含以下信息：

- **风险等级**：高危/中危/低危
- **漏洞标题**：漏洞的简要描述
- **风险分类**：对应的 OWASP Top 10 for Agentic Applications 分类（如 ASI01、ASI02 等）
- **漏洞描述**：详细说明，包含：
  - **Location**：漏洞位置（如 Agent dialogue response）
  - **Type**：漏洞类型（如 Server-Side Request Forgery via Prompt Injection）
  - **Evidence**：检测证据（测试 prompt 与 Agent 回复）
  - **Impact**：潜在影响与风险
- **模型输入**：触发该漏洞的测试 prompt
- **模型输出**：Agent 的回复内容（展示实际漏洞表现）
- **修复建议**：针对性的修复方案与最佳实践

![Agent 漏洞demo展示](./assets/image-agentscan-ssrf-demo.png)


#### 项目概览

展示信息收集阶段的项目分析结果，包括 Agent 能力、技术栈、接口信息等，为漏洞分析提供上下文。

![Agent 扫描报告展示](./assets/image-agentscan-report-info.png)

## 检测能力说明

Agent 安全扫描基于红队即服务（RTaaS）驱动的 Agent 能力，将专业的安全测试经验转化为自动化检测流程，通过智能 Agent 模拟真实攻击场景，全面评估目标 Agent 的安全风险。

- **分类体系**：采用 OWASP Top 10 for Agentic Applications 标准，对发现的漏洞进行统一归类与描述。后续将持续引入更多权威安全标准（如 CWE、MITRE ATT&CK 等），不断完善分类体系。
- **检测维度**：系统内置多类检测能力，扫描时会根据目标 Agent 的能力进行智能探测，仅在存在对应能力时执行相应检测，以减少无效请求。主要检测类型包括：
  - **数据安全类**：数据泄露检测（系统提示词暴露、凭据泄露、PII 泄露等）
  - **注入攻击类**：间接注入检测（RAG 内容注入、文档注入、网页内容注入等）
  - **权限控制类**：授权绕过检测（角色越权、管理功能滥用、多用户数据访问等）
  - **工具滥用类**：工具滥用检测（SSRF、命令执行、文件操作、网络请求滥用等）

