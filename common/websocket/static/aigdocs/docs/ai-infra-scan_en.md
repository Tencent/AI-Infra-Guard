# AI Infra Scan

## Feature Overview
AI Infra Security Scan identifies known vulnerabilities (e.g., CVEs) in web services of AI infrastructure components  through precise fingerprint matching. This enables rapid detection of security gaps, empowering teams to mitigate risks proactively and maintain   secure, stable AI operations.

## Core Features
- **Comprehensive Coverage**: Identifies **100+ mainstream AI frameworks**, covering **1900+ known vulnerabilities** (CVEs).  
- **Flexible Deployment**: Supports **single-target**, **batch**, and **local service ** scanning.  
- **Intelligent Matching**: **YAML-based fingerprint rules** ensure high-precision detection accuracy.  
- **Extensibility**: Enables **custom vulnerability templates** and **fingerprint rules** for specialized deployment scenarios.

## Quick Start

### WebUI Interface Workflow

1.Select `AI Infra Scan` from the main page.

2.Configure Scan Targets
   - Enter single/multiple URLs or IP addresses (one per line)
   - Import target lists via `.txt` file upload
   - ✨ *IP inputs trigger comprehensive port scanning*
      (Automatically checks common open ports)

3.Select a MLLM to detect unauthenticated vulnerabilities, recommended GPT5/Gemini Pro/Sonnet4.5.

4.Click `Send Message` button to initiate automated vulnerability detection.
   Results will populate in real-time upon completion.

![image-20250717185311173](./assets/image-20250717185311173-en.png)

![image-20250717185509861](./assets/image-20250717185509861-en.png)

## Fingerprint & Vulnerability Database

### Built-in Fingerprint Repository
A.I.G includes **an extensive library of pre-configured AI component fingerprints**, accessible via the Plugin Management interface:


1. **Access plugin management**
   Navigate to `Plugin Management` (bottom-left of the main page)
2. **Review Built-in Resources**
   View all default fingerprint rules with search/filter capabilities
3. **Manage Fingerprints**
   Perform real-time operations:
   - 🔍 Search rules by name/description/contributor
   - ➕ Add custom fingerprints and associated vulnerabilities
   - ✏️ Edit existing fingerprints and associated vulnerabilities

![image-20250814173036377](./assets/image-20250814173036377-en.png)
▶️ Changes apply immediately – subsequent scans automatically utilize updated databases
![image-20250717185223588](./assets/image-20250717185223588-en.png)

## Supported AI Components & Vulnerability Coverage

A.I.G delivers comprehensive security coverage for critical AI infrastructure components. Current supported components and vulnerability statistics:

| Category                   | Component Name          | Vulnerability Count | Risk Level  |
| -------------------------- | ----------------------- | ------------------- | ----------- |
| **Model Serving** | vllm | 67 | Medium |
| | gradio | 51 | High |
| | triton-inference-server | 41 | Medium-High |
| | ollama | 32 | Medium-High |
| | tensorrt-llm | 12 | Medium-High |
| | fastchat | 9 | Medium |
| | llama-cpp | 9 | Medium-High |
| | Xinference | 3 | Low |
| | ChatRTX | 1 | Low |
| | huggingface-tgi | 1 | Medium-High |
| | kubeai | 1 | High |
| | llmstudio | 1 | Low |
| | localai | 1 | Medium |
| | tensorzero | 1 | Low |
| **LLM App Frameworks** | openwebui | 86 | Medium-High |
| | langflow | 79 | Medium |
| | mlflow | 79 | High |
| | flowise | 61 | Medium |
| | langchain | 52 | High |
| | open-webui | 44 | Medium-High |
| | Dify | 31 | High |
| | LiteLLM | 31 | Medium |
| | Chuanhugpt | 27 | Medium-High |
| | librechat | 21 | Medium |
| | anythingllm | 18 | Medium-High |
| | ragflow | 12 | Medium |
| | nextchat | 8 | Medium |
| | qanything | 8 | Medium |
| | fastgpt | 6 | Medium |
| | new-api | 5 | Medium |
| | LobeChat | 4 | Medium |
| | crewai | 4 | Critical |
| | langfuse | 4 | Low |
| | chuanhuchatgpt | 1 | Medium |
| | helicone | 1 | Medium |
| | lobehub | 1 | Medium |
| **Data Processing** | clickhouse | 26 | High |
| | dask | 3 | Low |
| | feast | 3 | Low |
| **Visualization & UI** | jupyter-server | 19 | Medium-High |
| | jupyterlab | 9 | Medium |
| | jupyter-notebook | 2 | Low |
| | marimo | 1 | Medium |
| **Workflow Orchestration** | n8n | 60 | Medium-High |
| | ray | 12 | Medium |
| | simstudioai | 9 | Medium |
| | kubeflow | 8 | Medium |
| | n8n-mcp | 4 | Medium-High |
| | 9router | 3 | High |
| **Other AI Components** | openclaw | 655 | Medium-High |
| | praisonai | 107 | Critical |
| | pyload-ng | 24 | Medium |
| | astrbot | 14 | Medium |
| | comfyui | 13 | Medium |
| | crawl4ai | 11 | Critical |
| | sglang | 9 | Medium |
| | bentoml | 6 | Medium |
| | pinchtab | 6 | Medium-High |
| | kubepi | 5 | Medium |
| | sillytavern | 5 | Medium |
| | autogpt | 4 | Medium |
| | flyto2 | 4 | Medium |
| | llamafactory | 4 | Low |
| | lmdeploy | 4 | Low |
| | lollms | 4 | Medium |
| | pipecat | 3 | Low |
| | agenticmail | 2 | Medium |
| | boxlite | 2 | Medium |
| | hermes | 2 | Critical |
| | instructlab | 2 | Low |
| | jan | 2 | Low |
| | junoclaw | 2 | Medium |
| | langroid | 2 | Critical |
| | maxkb | 2 | Medium |
| | mcp | 2 | Medium |
| | mcp sse | 2 | Medium |
| | paperclip | 2 | Medium |
| | weknora | 2 | Low |
| | pgadmin | 2 | Medium-High |
| | Clawdbot Gateway | 1 | Medium |
| | ComfyUI-Ace-Nodes | 1 | Low |
| | ComfyUI-Bmad-Nodes | 1 | Low |
| | ComfyUI-Custom-Scripts | 1 | Low |
| | ComfyUI-Impact-Pack | 1 | Low |
| | ComfyUI-Manager | 1 | Low |
| | ComfyUI-Prompt-Preview | 1 | Low |
| | agentic-flow | 1 | Medium |
| | ai-chatbot | 1 | Medium |
| | ai-code | 1 | Critical |
| | ai-copilot | 1 | Medium |
| | ai-engine-wordpress | 1 | Medium |
| | blinko | 1 | Low |
| | comfy_mtb | 1 | Low |
| | f5-tts | 1 | Medium |
| | gpt-sovits | 1 | Medium |
| | guardrails-ai | 1 | Medium |
| | langbot | 1 | Low |
| | lightrag | 1 | Low |
| | lumiverse | 1 | Low |
| | mcp-documentation-server | 1 | Medium |
| | mcp-pinot | 1 | Medium |
| | mcp-server-kubernetes | 1 | Medium |
| | mem0 | 1 | Low |
| | netlicensing-mcp | 1 | Medium |
| | network-ai | 1 | Medium |
| | nvidia-trt-llm | 1 | High |
| | qnabot-on-aws | 1 | Low |
| | suna | 1 | Medium |
| | superagi | 1 | Low |
| | text-generation-webui | 1 | Medium |
| | upsonic | 1 | Medium |
| | wallos | 1 | Low |
| | budibase | 1 | Medium |
| **AI Agent Config Security** | AI-Agent-Config | 4 | High |
| **Total** | | **1914+** | |

> **Note**: The vulnerability database is continuously updated. Regular scanning of high-risk components is recommended.

## Fingerprint Matching Rule Details

### Rule Structure

AI Infra Guard uses YAML format to define fingerprint matching rules, which mainly include the following parts:

```yaml
info:
  name: Component Name
  author: Rule Author
  severity: Information Level
  metadata:
    product: Product Name
    vendor: Vendor Name
http:
  - method: HTTP Request Method
    path: Request Path
    matchers:
      - Matching Conditions
```

### Example: Dify Fingerprint Rule

```yaml
info:
  name: dify
  author: Tencent Zhuque Lab
  severity: info
  metadata:
    product: dify
    vendor: dify
http:
  - method: GET
    path: '/'
    matchers:
      - body="<title>Dify</title>" || icon="97378986"
version:
  - method: GET
    path: '/console/api/version'
    extractor:
      part: header
      group: 1
      regex: 'x-version:\s*(\d+\.\d+\.?\d+?)'
```

### Matcher Syntax Explanation

#### Match Locations

| Location | Description             | Example                                   |
| -------- | ----------------------- | ----------------------------------------- |
| `title`  | HTML page title         | `title="Gradio"`                          |
| `body`   | HTTP response body      | `body="gradio-config"`                    |
| `header` | HTTP response header    | `header="X-Gradio-Version: 3.34.0"`       |
| `icon`   | Website favicon hash    | `icon="d41d8cd98f00b204e9800998ecf8427e"` |

#### Logical Operators

| Operator | Description                               | Example                                                      |
| -------- | ----------------------------------------- | ------------------------------------------------------------ |
| `=`      | Fuzzy contains match (case-insensitive)   | `body="gradio"`                                              |
| `==`     | Exact equals match (case-sensitive)       | `header="Server: Gradio"`                                    |
| `!=`     | Not equals match                          | `header!="Server: Apache"`                                   |
| `~=`     | Regular expression match                  | `body~="Gradio v[0-9]+.[0-9]+.[0-9]+"`                       |
| `&&`     | Logical AND                               | `body="gradio" && header="X-Gradio-Version"`                 |
| `||`     | Logical OR                                | `body="gradio" || body="Gradio"`                             |
| `()`     | Grouping to change precedence             | `(body="gradio" || body="Gradio") && header="X-Gradio-Version"` |

## Operational Best Practices


1.**Schedule Regular Scans**: Schedule weekly comprehensive scans of your AI infrastructure to promptly identify emerging vulnerabilities.

2.**Prioritize High-Risk Components**: Focus scanning resources on components with high vulnerability densities, such as Gradio, LangChain, and ClickHouse.

3.**Extend with Custom Rules**: Enhance detection capabilities for organization-specific AI components by adding custom fingerprint rules.

4.**Integrate into CI/CD Pipelines**: Embed security scanning into the continuous integration (CI) process for AI applications to implement shift-left security.

5.**Track Vulnerability Remediation**: Establish a tracking mechanism for vulnerabilities discovered during scans to ensure timely remediation.

By leveraging the AI Infra Scan service, you can effectively identify potential security risks within your AI systems, providing robust assurance for building a secure and reliable AI infrastructure.