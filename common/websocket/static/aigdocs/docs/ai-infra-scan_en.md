# AI Infra Scan

## Feature Overview
AI Infra Security Scan identifies known vulnerabilities (e.g., CVEs) in web services of AI infrastructure components  through precise fingerprint matching. This enables rapid detection of security gaps, empowering teams to mitigate risks proactively and maintain   secure, stable AI operations.

## Core Features
- **Comprehensive Coverage**: Identifies **100+ mainstream AI frameworks**, covering **2000+ known vulnerabilities** (CVEs).  
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
| **Model Serving** | vllm | 105 | Medium |
| | gradio | 53 | High |
| | triton-inference-server | 41 | Medium-High |
| | ollama | 35 | Medium-High |
| | tensorrt-llm | 12 | Medium-High |
| | fastchat | 10 | Medium |
| | llama-cpp | 17 | Medium-High |
| | Xinference | 5 | Low |
| | ChatRTX | 1 | Low |
| | huggingface-tgi | 1 | Medium-High |
| | kubeai | 1 | High |
| | llmstudio | 1 | Low |
| | localai | 1 | Medium |
| | tensorzero | 1 | Low |
| **LLM App Frameworks** | openwebui | 92 | Medium-High |
| | langflow | 162 | Medium |
| | mlflow | 85 | High |
| | flowise | 118 | Medium |
| | langchain | 52 | High |
| | open-webui | 44 | Medium-High |
| | Dify | 34 | High |
| | LiteLLM | 46 | Medium |
| | Chuanhugpt | 27 | Medium-High |
| | librechat | 21 | Medium |
| | anythingllm | 20 | Medium-High |
| | ragflow | 14 | Medium |
| | nextchat | 9 | Medium |
| | qanything | 9 | Medium |
| | fastgpt | 9 | Medium |
| | new-api | 11 | Medium |
| | LobeChat | 5 | Medium |
| | crewai | 5 | Critical |
| | langfuse | 4 | Low |
| | chuanhuchatgpt | 1 | Medium |
| | helicone | 1 | Medium |
| | lobehub | 1 | Medium |
| **Data Processing** | clickhouse | 26 | High |
| | dask | 3 | Low |
| | feast | 5 | Low |
| **Visualization & UI** | jupyter-server | 20 | Medium-High |
| | jupyterlab | 15 | Medium |
| | jupyter-notebook | 2 | Low |
| | marimo | 3 | Medium |
| **Workflow Orchestration** | n8n | 84 | Medium-High |
| | ray | 12 | Medium |
| | simstudioai | 9 | Medium |
| | kubeflow | 9 | Medium |
| | n8n-mcp | 4 | Medium-High |
| | 9router | 4 | High |
| **Other AI Components** | openclaw | 737 | Medium-High |
| | praisonai | 148 | Critical |
| | pyload-ng | 24 | Medium |
| | astrbot | 14 | Medium |
| | comfyui | 13 | Medium |
| | crawl4ai | 16 | Critical |
| | sglang | 22 | Medium |
| | bentoml | 7 | Medium |
| | pinchtab | 6 | Medium-High |
| | kubepi | 7 | Medium |
| | sillytavern | 5 | Medium |
| | dynamo | 7 | High |
| | autogpt | 5 | Medium |
| | flyto2 | 4 | Medium |
| | llamafactory | 4 | Low |
| | lmdeploy | 10 | Low |
| | lollms | 5 | Medium |
| | pipecat | 3 | Low |
| | agenticmail | 2 | Medium |
| | boxlite | 2 | Medium |
| | hermes | 6 | Critical |
| | instructlab | 2 | Low |
| | jan | 3 | Low |
| | junoclaw | 2 | Medium |
| | langroid | 2 | Critical |
| | maxkb | 16 | Medium |
| | mcp | 2 | Medium |
| | mcp sse | 2 | Medium |
| | paperclip | 3 | Medium |
| | weknora | 3 | Low |
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
| | ai-engine-wordpress | 2 | Medium |
| | blinko | 3 | Low |
| | comfy_mtb | 1 | Low |
| | f5-tts | 1 | Medium |
| | gpt-sovits | 1 | Medium |
| | guardrails-ai | 1 | Medium |
| | langbot | 2 | Low |
| | lightrag | 6 | Low |
| | lumiverse | 1 | Low |
| | mcp-documentation-server | 1 | Medium |
| | mcp-pinot | 1 | Medium |
| | mcp-server-kubernetes | 1 | Medium |
| | mem0 | 1 | Low |
| | netlicensing-mcp | 1 | Medium |
| | network-ai | 2 | Medium |
| | nvidia-trt-llm | 1 | High |
| | qnabot-on-aws | 1 | Low |
| | suna | 1 | Medium |
| | superagi | 1 | Low |
| | text-generation-webui | 1 | Medium |
| | upsonic | 1 | Medium |
| | nocobase | 1 | Critical |
| | sub2api | 1 | High |
| | trigger.dev | 5 | Critical |
| | mcp-atlassian | 7 | High |
| | hatchet | 5 | High |
| | mcp-searxng | 4 | High |
| | omnigent | 4 | Critical |
| | lightllm | 3 | Critical |
| | meta-ads-mcp | 3 | Critical |
| | onyx | 3 | Critical |
| | chroma | 2 | High |
| | dbhub | 2 | Critical |
| | quivr | 2 | High |
| | axolotl | 1 | High |
| | bifrost | 1 | High |
| | context7 | 1 | Critical |
| | decepticon | 1 | Critical |
| | eclipse-theia | 1 | High |
| | graphiti | 1 | High |
| | h2ogpt | 1 | Critical |
| | mcphub | 1 | High |
| | memos | 1 | Critical |
| | ms-swift | 1 | High |
| | notebooklm-mcp | 1 | High |
| | obot | 1 | Critical |
| | omniroute | 1 | Critical |
| | open-genai-stack | 1 | Critical |
| | open-generative-ai | 1 | High |
| | qwed | 1 | High |
| | trek | 1 | High |
| **AI Agent Config Security** | AI-Agent-Config | 7 | High |
| **Total** | | **2000+** | |

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