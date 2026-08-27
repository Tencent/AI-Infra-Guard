# MCP Server Scan

A.I.G leverages AI agents for comprehensive MCP Server and Skills security assessment, supporting both source code audits and remote URL scanning. A.I.G can detect the following common MCP Server security risks, with continuous updates:

<table>
<thead>
<tr>
<th>Risk Name</th>
<th>Description</th>
</tr>
</thead>
<tbody>
<tr>
<td>Tool Poisoning Attack</td>
<td>A malicious MCP Server injects hidden instructions through tool descriptions to manipulate the AI Agent into performing unauthorized actions (e.g., stealing data, executing malicious acts).</td>
</tr>
<tr>
<td>Rug Pull Scheme</td>
<td>A malicious MCP Server behaves normally initially but changes its behavior after user approval or several runs to execute malicious instructions, leading to hard-to-detect malicious activity.</td>
</tr>
<tr>
<td>Tool Overwriting Attack</td>
<td>A malicious MCP Server redefines the behavior of other trusted MCP Server tools through hidden instructions (e.g., modifying email recipients, performing extra operations).</td>
</tr>
<tr>
<td>Malicious Code/Command Execution</td>
<td>If an MCP Server supports direct code or command execution without proper sandboxing, it can be exploited by attackers to perform malicious operations on the server or user's local machine.</td>
</tr>
<tr>
<td>Data Theft</td>
<td>A malicious MCP Server induces the AI Agent to read and transmit sensitive data (e.g., API keys, SSH keys), or directly sends user-authorized input data to an external server.</td>
</tr>
<tr>
<td>Unauthorized Access/Improper Auth</td>
<td>The MCP Server lacks effective authorization or has flawed authentication, allowing attackers to bypass verification and access restricted resources or user data.</td>
</tr>
<tr>
<td>Indirect Prompt Injection</td>
<td>The MCP Server outputs external data containing malicious instructions (e.g., from web pages, documents) to the AI Agent, potentially influencing its decisions and behavior.</td>
</tr>
<tr>
<td>Package Name Squatting/Typosquatting</td>
<td>A malicious MCP Server uses names, tool names, or descriptions similar to trusted services to trick the AI Agent into making incorrect calls; or a third party squats an official MCP Server name to plant a backdoor.</td>
</tr>
<tr>
<td>Plaintext Key Storage</td>
<td>The MCP Server hardcodes or stores sensitive keys in plaintext within its code or configuration files, posing a high risk of leakage.</td>
</tr>
</tbody>
</table>

A.I.G's MCP Server scanning capability is entirely driven by an AI agent. The accuracy and duration of the detection depend on the Large Language Model API selected by the user.

### Add a Model API for Detection

![image-20250717174655353](./assets/image-20250814173229996-en.png)

## Method 1: MCP Server Source Code Scan

1. Select "MCP Scan"
2. Upload the MCP Server source code as an attachment
![image-mcp4](./assets/mcp4-en.png)
3. Start Scan


## Method 2: Scan an MCP Server project from GitHub
1. Select "MCP Scan"
![image-mcp5](./assets/mcp5-en.png)
2. Enter the GitHub repository URL in the input box
3. Start Scan

## Method 3: Remote MCP Service Scan

1. Select "MCP Scan"
2. Enter the MCP service address (SSE or Streamable HTTP protocol) in the input box, e.g., `http://127.0.0.1:9000/sse`
3. Start Scan
![image-mcp8](./assets/mcp8-en.png)

## Method 4: Install via pip and Scan Standalone

In addition to using the A.I.G platform, aig-mcp-scan can be installed as a standalone tool via pip, suitable for CI/CD integration or local batch auditing.

### Installation

```bash
pip install aig-mcp-scan
```

> Requires Python ≥ 3.9

### Command Line Usage

```bash
# Scan a local MCP Server project directory
aig-mcp-scan --repo /path/to/your/mcp-server \
           -m deepseek-v4-flash \
           --language en

# Or invoke as a Python module
python -m mcp_scan --repo /path/to/your/mcp-server

# Scan a remote MCP service (dynamic analysis)
aig-mcp-scan --server_url "http://localhost:8000/sse" \
           -m deepseek-v4-flash

# Save scan results to a file
aig-mcp-scan --repo /path/to/your/mcp-server -o result.sarif.json
```

### Command Line Options

| Option | Description | Default |
| --- | --- | --- |
| `--repo` | Path to the MCP Server project directory to scan (required for static scanning) | — |
| `--server_url` | Remote MCP server URL (enables dynamic analysis mode) | — |
| `-m, --model` | LLM model name | `deepseek/deepseek-v3.2-exp` |
| `-k, --api_key` | API key (falls back to env vars if omitted) | — |
| `-u, --base_url` | API base URL | `https://openrouter.ai/api/v1` |
| `-p, --prompt` | Custom scan prompt (optional) | — |
| `--header` | Custom HTTP header (key:value), can be used multiple times | `[]` |
| `--language` | Output language: `zh` / `en` | `zh` |
| `--debug` | Enable debug mode | `false` |
| `-o, --output` | Save scan results; **SARIF 2.1.0 JSON when `--aig-mode` is off, internal-schema JSON when it's on** | — |

### Environment Variables

Configuration can also be provided via environment variables or a `.env` file:

| Variable | Description | Default |
| --- | --- | --- |
| `LLM_API_KEY` / `OPENAI_API_KEY` | LLM API key | — |
| `LLM_MODEL` | Default model | `deepseek/deepseek-v3.2-exp` |
| `LLM_BASE_URL` | Default base URL | `https://openrouter.ai/api/v1` |

### SARIF Output Format

CLI mode outputs **SARIF 2.1.0** JSON by default, containing the full MCP01–MCP10 plus 3 supplemental classification rules (Name Confusion, Rug Pull, Tool Shadowing). Rules are always output even if no vulnerabilities are found. SARIF files can be uploaded directly to GitHub Code Scanning, Azure DevOps, GitLab Security Dashboard, and other SARIF-aware tools.

For more details, see the [aig-mcp-scan README](https://github.com/Tencent/AI-Infra-Guard/tree/main/mcp-scan).

## View Scan Status and Results
![image-mcp6](./assets/mcp6-en.png)![image-mcp7](./assets/mcp7-en.png)

## Recommended Large Language Model APIs
- Hy3
- GLM-5.2
- DeepSeek-V4
- Kimi-K3
- Qwen3-Coder-480B-A35B-Instruct

## Multi-Turn Automated Red Teaming

A.I.G includes a built-in multi-turn automated red-teaming module for MCP Servers. Three LLM roles — Attacker, Target, and Evaluator — collaborate to perform adversarial testing against MCP Server source code.

### Supported Attack Strategies

| Strategy | Description |
|----------|-------------|
| **Crescendo** | Progressive multi-turn escalation: establish trust → probe boundaries → escalate gradually → launch attack |
| **TAP** (Tree of Attacks with Pruning) | Generates multiple attack variants per round, then uses a two-stage pruning process to retain the optimal path, advancing layer by layer |

### Predefined Attack Targets (OWASP Agentic Top 10 aligned)

| Target ID | Description |
|-----------|-------------|
| `data_exfiltration` | Data exfiltration |
| `indirect_prompt_injection` | Indirect prompt injection |
| `ssrf_via_agent` | SSRF via agent |
| `rce_via_tool` | RCE via tool |
| `privilege_escalation` | Privilege escalation |
| `tool_poisoning` | Tool poisoning |

### Usage

```python
import asyncio
from mcp_scan.redteam import RedTeamOrchestrator, generate_report

async def main():
    orch = RedTeamOrchestrator(
        api_key="your-api-key",
        base_url="https://openrouter.ai/api/v1",
        model="deepseek/deepseek-v4-pro",
        repo_dir="path/to/your/mcp/server/repo",
    )
    result = await orch.run("data_exfiltration", strategy_name="crescendo", max_total_rounds=8)
    print(generate_report(result))

asyncio.run(main())
```

The red-teaming module code is located in `mcp-scan/mcp_scan/redteam/`. Install dependencies first (`uv sync` or `pip install -r requirements.txt`) from the `mcp-scan` project root directory.

## MCP Plugins

MCP scanning is powered by an AI agent that inspects the code. A.I.G. modularizes MCP vulnerabilities into plugins, which can be viewed or edited in the frontend.

![image-20250814105330552](./assets/image-20250814105330552-en.png)

The MCP plugin template is shown below. The key field is `prompt_template`, which defines the prompt to instruct the large language model about the vulnerability type and the scanning method.

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
  - **Default Configuration**: If it's a framework's default configuration with documentation, do not report.
  - **Test Identifiers**: Do not report items containing keywords like test, demo, example, mock.
  - **Development Environment**: Do not report configurations clearly used for development and debugging.
  - **Correct Implementation**: Do not report authentication implementations that follow security best practices.
  - **Project-Level Permission Verification Assessment**: If no permission verification exists, assess whether the project's nature indicates it is critical (e.g., capable of operating on the local host or database). If the project is not critical, do not report.

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

