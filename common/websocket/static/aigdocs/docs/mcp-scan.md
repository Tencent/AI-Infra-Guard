# AI工具协议扫描

A.I.G使用了基于AI Agent驱动的AI工具协议检测方案，支持MCP Server、Skills源代码安全审计与远程MCP Server URL安全扫描。

<img src= "./assets/mcp-scan.png">

> **注意**：架构内容部分仍在升级中。

<br/>
A.I.G 可检测以下常见的AI工具协议安全风险，并持续更新：

<table>
<tr>
<th>AI工具</th>
<th>风险名称</th>
<th>风险说明</th>
</tr>
<tr>
<td rowspan="9">MCP Server</td>
<td>工具投毒攻击</td>
<td>恶意MCP Server通过工具描述注入隐藏指令，操纵AI Agent执行未授权操作（例如窃取数据、执行恶意行为）。</td>
</tr>
<tr>
<td>地毯式骗局</td>
<td>恶意MCP Server在初期表现正常，但在用户批准或运行若干次后改变行为，执行恶意指令，导致难以察觉的恶意行为。</td>
</tr>
<tr>
<td>工具覆盖攻击</td>
<td>恶意MCP Server通过隐藏指令重新定义其他可信MCP Server工具的行为（例如修改邮件接收者、执行额外操作）。</td>
</tr>
<tr>
<td>恶意代码/命令执行</td>
<td>MCP Server若支持直接执行代码或命令且缺乏沙箱隔离，可能被攻击者利用在服务器或用户本地执行恶意操作。</td>
</tr>
<tr>
<td>数据窃取</td>
<td>恶意MCP Server诱导AI Agent读取并传输敏感数据（例如API密钥、SSH密钥），或直接将用户授权输入的数据发送至外部服务器。</td>
</tr>
<tr>
<td>未授权访问/鉴权不当</td>
<td>MCP Server缺乏有效授权认证或存在缺陷，导致攻击者可绕过验证访问受限资源或用户数据。</td>
</tr>
<tr>
<td>间接提示词注入</td>
<td>MCP Server将包含恶意指令的外部数据（例如网页、文档）输出给AI Agent，可能影响AI Agent的决策和行为。</td>
</tr>
<tr>
<td>包名混淆与抢注攻击</td>
<td>恶意MCP Server使用与可信服务相似的名称、工具名或描述，诱导AI Agent错误调用；或第三方抢注官方AI工具名称，植入后门。</td>
</tr>
<tr>
<td>明文存储密钥</td>
<td>MCP Server在代码或配置文件中硬编码或明文存储敏感密钥，易导致泄露风险。</td>
</tr>
<tr>
<td rowspan="5">Skills</td>
<td>语义劫持攻击</td>
<td>攻击者可以精心构造一个恶意的Skill描述，使其在语义上覆盖高频的用户意图（例如修复代码错误或优化系统性能）。当用户发出模糊指令时，Agent可能会错误地激活恶意Skill而非预期工具。</td>
</tr>
<tr>
<td>幽灵指令攻击</td>
<td>攻击者在SKILL.md中嵌入伪装成正常内容（如注释或错误处理指南）的恶意指令，Agent加载Skill时这些指令会被注入上下文，从而控制LLM执行恶意操作。</td>
</tr>
<tr>
<td>恶意后门脚本攻击</td>
<td>Skill引导Agent调用包含恶意代码的本地脚本，利用Agent的Shell权限读取SSH密钥、修改系统配置、安装后门，甚至发起反向Shell连接。</td>
</tr>
<tr>
<td>不安全SKILLS配置风险</td>
<td>allowed-tools配置不当，无需二次人工确认可以静默执行Bash等危险操作。</td>
</tr>
<tr>
<td>代码实现层漏洞</td>
<td>如命令注入与密钥硬编码（实测在内网Skills中较为常见）。</td>
</tr>
</table>

A.I.G的AI工具协议扫描能力完全由Agent驱动，检测准确性与时长取决于用户选择的大模型API。

### 添加用检测AI工具的模型API

![image-20250717174655353](./assets/mcp1.png)

![image-mcp3](./assets/mcp3.png)

## 方式一：AI工具源代码压缩包扫描

1. 选择“AI工具协议扫描”
2. 添加附件上传源代码压缩包
![image-mcp4](./assets/mcp4.png)
3. 开始扫描

## 方式二：AI工具代码仓库扫描

1. 选择“AI工具协议扫描”
2. 输入框输入代码仓库地址，如：https://github.com/xxx/mcp-server
3. 开始扫描
![image-mcp4](./assets/mcp5.png)

## 方式三：远程MCP服务扫描

1. 选择“AI工具协议扫描”
2. 输入框输入MCP服务地址 (SSE或Streamable HTTP协议)，如：http://127.0.0.1:9000/sse
3. 开始扫描
![image-mcp8](./assets/mcp8.png)

## 查看扫描状态和结果
![image-mcp6](./assets/mcp6.png)
![image-mcp7](./assets/mcp7.png)

## 推荐使用的大模型API
- GLM4.6
- DeepSeek-V3.2
- Kimi-K2-Instruct
- Qwen3-Coder-480B
- Hunyuan-Turbos

## MCP 插件

MCP扫描基于AI Agent对代码进行检测，A.I.G将MCP漏洞抽象为了插件，可以在前端查看。

![image-20250814105330552](./assets/image-20250814105330552.png)

MCP插件模板如下，关键的是`prompt_template`字段，用提示词告诉大模型漏洞类型和应该如何扫描。

```yaml
info:
  id: "auth_bypass"
  name: "Authentication Bypass Detection"
  description: "Detect possible authentication bypass vulnerabilities in MCP code"
  author: "Zhuque Security Team"
  categories:
    - code

prompt_template: |
  As a professional cybersecurity analyst, you need to precisely detect authentication bypass vulnerabilities in MCP code. This detection requires extremely high accuracy - only report when you find concrete evidence of authentication bypass risks.

  ## Vulnerability Definition
  Authentication bypass refers to an attacker's ability to gain unauthorized access by circumventing the system's authentication mechanisms without providing valid credentials.

  ## Detection Criteria (Must meet at least one concrete evidence)

  ### 1. Hardcoded Credential Vulnerabilities
  **Required Conditions:**
  - Discovery of plaintext stored real credentials (not test/example data)
  - Credentials have actual system access privileges
  - Ability to obtain valid authentication information directly through code
  - Existence of backdoors that bypass normal authentication processes

  **Code Patterns:**
  - Hardcoded API keys, passwords, tokens
  - Universal passwords or backdoor accounts
  - Special parameters or flags that bypass authentication

  ### 2. JWT Security Flaws
  **Required Conditions:**
  - Missing or bypassable JWT signature verification
  - Use of weak signature algorithms (e.g., none, HS256 with weak keys)
  - JWT key leakage or predictability
  - JWT replay attack vulnerabilities

  **Detection Points:**
  - verify=False or skipping signature verification
  - Using fixed or weak JWT keys
  - Missing timestamp verification (exp, iat)
  - Allowing algorithm=none JWT

  ### 3. OAuth Authentication Flaws
  **Required Conditions:**
  - Missing or loose redirect_uri validation
  - Missing state parameter leading to CSRF attacks
  - client_secret leakage or hardcoding
  - Authorization code reuse or no time limits

  ### 4. Session Management Vulnerabilities
  **Required Conditions:**
  - Session fixation attacks
  - Session hijacking risks (missing secure/httponly flags)
  - Missing session timeout mechanisms
  - Missing Cross-Site Request Forgery (CSRF) protection

  ### 5. Authentication Logic Bypass
  **Required Conditions:**
  - Conditional bypass in authentication check logic
  - Logic errors in permission judgment
  - Ability to skip steps in multi-step authentication process
  - Missing or misconfigured authentication middleware

  ## Technical Detection Methods

  ### Code Pattern Recognition
  **High-Risk Patterns:**
  - if user == "admin" and password == "hardcoded_password"
  - jwt.decode(token, verify=False)
  - session['authenticated'] = True  # Setting without verification
  - @app.route('/admin')  # Missing authentication decorator

  ### Configuration File Analysis
  - Check security of authentication-related configurations
  - Verify if default credentials have been changed
  - Analyze completeness of access control lists

  ### API Endpoint Security
  - Identify sensitive interfaces lacking authentication protection
  - Check correct application of authentication middleware
  - Verify granularity and completeness of permission control

  ## Exclusion Conditions (Do not report the following)

  ### Normal Development Scenarios
  - Mock authentication in test code
  - Temporary credentials in development environment
  - Fixed test data in unit tests
  - Placeholder credentials in example code

  ### Security Practices
  - Correctly implemented OAuth2.0 flows
  - Secure JWT implementations (strong signatures, complete verification)
  - Comprehensive session management mechanisms
  - Appropriate RBAC permission control

  ### Configuration Management
  - Credentials managed through environment variables
  - Implementations using key management services
  - Correct configuration file permission settings

  ## Verification Requirements
  1. **Vulnerability Exploitability**: Must be able to construct actual attack paths
  2. **Impact Assessment**: Clearly define access privileges after bypassing authentication
  3. **Technical Details**: Provide specific vulnerability principle analysis
  4. **Remediation Suggestions**: Provide clear security hardening solutions

  ## Strict Judgment Standards
  - **Default Configuration**: If it's framework default configuration with documentation, do not report
  - **Test Identifiers**: Do not report those containing test, demo, example, mock keywords
  - **Development Environment**: Do not report configurations clearly used for development debugging
  - **Correct Implementation**: Do not report authentication implementations that follow security best practices
  - **Permission Verification Project Level Assessment**: If no permission verification exists, assess whether the project information collection indicates an important project (i.e., capable of operating local host or database operations). If the project is not important, do not report

  ## Input Data
  Source code path: {{ .CodePath }}
  Directory structure:
  ------
  {{ .DirectoryStructure }}
  ------

  ## Output Requirements
  Only output when finding concrete authentication bypass vulnerabilities:
  - Specific file paths and line numbers
  - Complete vulnerability code snippets
  - Technical analysis: vulnerability principles and exploitation methods
  - Impact assessment: privileges obtainable after bypassing authentication
  - Attack paths: specific exploitation steps
  - Remediation suggestions: detailed security hardening solutions

  **Strict Requirement: Must provide complete vulnerability exploitation paths and impact analysis. Remain silent when no concrete evidence exists.** 
```

