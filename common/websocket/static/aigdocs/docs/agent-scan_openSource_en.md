# Agent Security Scan

## Introduction

Agent Security Scan provides a one-click automated security assessment for AI Agents. Powered by Red Teaming as a Service (RTaaS) capabilities, it employs a multi-stage pipeline (Information Gathering → Vulnerability Detection → Verification & Triage) to automatically identify risks such as authorization bypass, data leakage, indirect injection, and tool abuse, generating standardized security reports.

It currently supports various integration methods including Dify, Coze, and custom HTTP endpoints. Detection results are classified and graded according to industry standards (OWASP Top 10 for Agentic Applications), helping developers quickly identify and remediate security issues in Agent-based applications.

## Quick Start

![Agent Security Scan Dashboard](./assets/image-agentscan.png)

1.  **Select Task Type**: Click "Agent Security Scan" on the main dashboard to enter the scan page.
2.  **Configure Planning Model and Target Agent**:
    - **Target Agent**: Select or add the Agent to be tested (Dify / Coze / HTTP, etc., see [Agent Configuration](#1-agent-configuration)).
    - **Planning Model (LLM)**: The scanning process is driven by a Large Language Model (LLM) that handles task planning and multi-stage reasoning (information gathering, vulnerability detection, and triage). You need to configure a planning model for the scan, including the model name, API address, and API Key (see [Planning Model Configuration](#2-planning-model-configuration)).
3.  **Start Scan and View Report**: Click "Send Message" and wait for the task to complete. Once finished, view the vulnerability list, risk levels, and remediation suggestions on the report page.

## Detailed Configuration

### 1. Agent Configuration

**Configuration Entry**: `Settings` → `Agent Configuration` → `Add / Upload YAML`

The system supports two configuration methods:
- **UI Configuration**: Fill in Agent information via the form (Recommended).
- **YAML File Upload**: Import Agent configuration by uploading a YAML file.

![Agent Configuration Entry](./assets/image-agentscan-config.png)

#### YAML File Upload

You can import Agent configurations via YAML files, which is suitable for reusing configurations or scenarios involving code-generated configs. **Sample YAML files can be downloaded from the configuration interface.**

**YAML File Format Example**:

**Dify Agent Example**:
```yaml
targets:
  - id: dify
    config:
      label: "DifyAgent (Supports English and Numbers)"
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

**Configuration Notes**:
- **File Format**: Supports YAML or JSON.
- **Field Description**:
  - `targets`: List of Agent configurations.
  - `id`: Agent type identifier (e.g., `dify`, `http`).
  - `label`: Display name of the Agent.
  - `config`: Specific configuration items (API Key, URL, Headers, etc.).
- **Validation**: The system automatically validates the configuration upon upload; error messages will be displayed if validation fails.

#### Supported Integration Methods

The system supports multiple Agent integration methods, including:
- **Dify AI**: Application conversation interface of the Dify platform.
- **Coze AI**: Bots on the Coze platform.
- **HTTP Interface**: Custom HTTP conversation endpoints (see [HTTP Interface Configuration Guide](?menu=agent-scan-http-config_en)).

#### Basic Configuration (Required)

The following basic settings are required for all Agent types:

- **Agent Name**: A custom name for the Agent, used for identification and management. Must be unique.
- **API-Key**: The authentication key for the target Agent.
  - Dify: Format reference `app-xxxx`.
  - Coze: Format reference `pat-xxxx` or the platform's specific API Key.
  - HTTP: Fill in according to the target interface's authentication method (can be configured in headers, see [HTTP Interface Configuration Guide](?menu=agent-scan-http-config_en)).

#### Advanced Configuration (Optional)

Advanced configuration options vary slightly by Agent type:

**Dify AI**:
- **Dify Endpoint Type**: Select the endpoint type, default is `Chat Message`.
- **API Base URL**: API service address, default is `https://api.dify.ai/v1`; modify to the actual address for private deployments.
- **User ID**: Identifier for the conversation user, default is `agent-user`.
- **Conversation ID**: Leave blank to start a new conversation for each scan; fill in an existing ID to continue a historical conversation.
- **Custom Inputs**: Additional input parameters in JSON format, e.g., `{"key": "value"}`.
- **Timeout (ms)**: Request timeout, default is `60000` (60 seconds).
- **Delay (ms)**: Delay between requests, default is `0`.

**HTTP Interface**: Includes configuration for request headers, body templates, response parsers, etc. See [HTTP Interface Configuration Guide](?menu=agent-scan-http-config_en).

> **Note**: Advanced configuration items for Coze AI and other internal platforms may differ; please refer to the interface prompts.

#### Agent Connection Verification

After configuration, you can use the "Agent Access Verification" feature for a quick test:

- Enter a test prompt in the "Prompt Input" box.
- Click the "Run Test" button to verify if the Agent's response is correct.
- Ensure verification passes before starting a formal scan to avoid failures due to configuration errors.

![Agent Connection Test Interface](./assets/image-agentscan-chat-demo.png)

**Connectivity Check**: Before saving or starting a scan, the system automatically tests connectivity to the target Agent. If it fails, an invalid configuration prompt will appear, requiring you to check the Agent settings.

### 2. Planning Model Configuration

The scanning module employs an LLM-driven multi-stage pipeline: a planning model handles task decomposition, detection strategy formulation, and report generation. Therefore, you must separately configure a Large Language Model "to execute the scan".

- **Supported Model Types**: Models compatible with the OpenAI API format.
- **Configuration Parameters**:
  - Model Name, e.g., `deepseek/deepseek-v3.2`, `moonshotai/kimi-k2.5`.
  - API Base URL, e.g., `https://openrouter.ai/api/v1`.
  - API Key.

> **Note**: This model is used solely for the planning and reasoning of the scanning engine and is independent of the "Target Agent being tested"; the conversational capability of the target Agent is determined by its integration method in [Agent Configuration](#1-agent-configuration).

![Planning Model Configuration](./assets/image-agentscan-process.png)

### 3. Report Display

Upon task completion, the report page displays comprehensive scan results and security analysis.

![Agent Scan Report Risk Overview](./assets/image-prompt-report-main.png)

#### Basic Information

- **Scan Target**: Name of the tested Agent.
- **Model Used**: Name of the planning model used for the scan.
- **Scan Time**: Start time of the task.
- **Duration**: Total time taken for the task.

#### Risk Overview

- **Risk Level**: Overall risk level (Critical / High / Medium / Low / Safe).
- **Security Score**: A comprehensive security score from 0-100.
- **Vulnerabilities Found**: Total number of detected vulnerabilities.
- **Risk Level Distribution**: Count of vulnerabilities by severity (Critical/High/Medium/Low).
- **Risk Category Distribution**: Distribution of vulnerabilities according to the ASI 2026 standard (ASI01–ASI10).

#### Vulnerability Details

Each vulnerability record includes the following information:

- **Risk Level**: Critical / High / Medium / Low.
- **Vulnerability Title**: Brief description of the vulnerability.
- **Risk Category**: Corresponding OWASP Top 10 for Agentic Applications
- **Vulnerability Description**: Detailed explanation, including:
  - **Location**: Where the vulnerability occurred (e.g., Agent dialogue response).
  - **Type**: Type of vulnerability (e.g., Server-Side Request Forgery via Prompt Injection).
  - **Evidence**: Detection evidence (test prompt and Agent response).
  - **Impact**: Potential impact and risk.
- **Model Input**: The test prompt that triggered the vulnerability.
- **Model Output**: The Agent's response content (showing actual vulnerability behavior).
- **Remediation Suggestion**: Targeted fix proposals and best practices.

![Agent Vulnerability Demo](./assets/image-agentscan-ssrf-demo.png)

#### Project Overview

Displays project analysis results from the information gathering phase, including Agent capabilities, technology stack, and interface information, providing context for vulnerability analysis.

![Agent Scan Report Info](./assets/image-agentscan-report-info.png)

## Detection Capabilities

Agent Security Scan leverages Red Teaming as a Service (RTaaS) driven Agent capabilities, translating professional security testing experience into an automated detection process. It simulates real-world attack scenarios through intelligent Agents to comprehensively assess the security risks of the target Agent.

- **Classification System**: Adopts the OWASP Top 10 for Agentic Applications standard to classify and describe discovered vulnerabilities. The system will continue to incorporate more authoritative security standards (such as CWE, MITRE ATT&CK) to continuously improve the classification system.
- **Detection Dimensions**: The system features built-in detection capabilities across multiple categories. During scanning, it intelligently probes based on the target Agent's capabilities, executing specific tests only when relevant capabilities are present to minimize ineffective requests. Major detection types include:
  - **Data Security**: Data leakage detection (system prompt exposure, credential leakage, PII leakage, etc.).
  - **Injection Attacks**: Indirect injection detection (RAG content injection, document injection, web content injection, etc.).
  - **Access Control**: Authorization bypass detection (privilege escalation, administrative function abuse, multi-user data access, etc.).
  - **Tool Abuse**: Tool misuse detection (SSRF, command execution, file operations, network request abuse, etc.).
