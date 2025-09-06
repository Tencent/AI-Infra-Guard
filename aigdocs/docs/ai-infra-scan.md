# AI Infra Scan

## Feature Overview
AI Infra Security Scan identifies known vulnerabilities (e.g., CVEs) in web services of AI infrastructure components  through precise fingerprint matching. This enables rapid detection of security gaps, empowering teams to mitigate risks proactively and maintain   secure, stable AI operations.

## Core Features
- **Comprehensive Coverage**: Identifies **36 mainstream AI frameworks**, covering **404 known vulnerabilities** (CVEs).  
- **Flexible Deployment**: Supports **single-target**, **batch**, and **local service ** scanning.  
- **Intelligent Matching**: **YAML-based fingerprint rules** ensure high-precision detection accuracy.  
- **Extensibility**: Enables **custom vulnerability templates** and **fingerprint rules** for specialized deployment scenarios.

## Quick Start

### WebUI Interface Workflow



1.**Call Scan Service**
   Select `AI Infra Scan` from the main page.

2.**Configure Scan Targets**
   In the target input field:
   - Enter single/multiple URLs or IP addresses (one per line)
   - Import target lists via `.txt` file upload
   - ✨ *IP inputs trigger comprehensive port scanning*
      (Automatically checks common open ports)

3.**Execute Security Assessment**
   Click `Send Message` button to initiate automated vulnerability detection.
   Results will populate in real-time upon completion.

![image-20250717185311173](./assets/image-20250717185311173-en.png)

![image-20250717185509861](./assets/image-20250717185509861-en.png)

## Fingerprint & Vulnerability Database

### Built-in Fingerprint Repository
A.I.G includes **an extensive library of pre-configured AI component fingerprints**, accessible via the Plugin Management interface:


1.**Access plugin management**
   Navigate to `Plugin Management` (bottom-left of the main page)

2.**Review Built-in Resources**
   View all default fingerprint rules with search/filter capabilities

3.**Manage Fingerprints**
   Perform real-time operations:
   - 🔍 Search rules by name/description/contributor
   - ➕ Add custom fingerprints and associated vulnerabilities
   - ✏️ Edit existing fingerprints and associated vulnerabilities

![image-20250814173036377](./assets/image-20250814173036377-en.png)
▶️ Changes apply immediately – subsequent scans automatically utilize updated databases
![image-20250717185223588](./assets/image-20250717185223588-en.png)

## Supported AI Components & Vulnerability Coverage

A.I.G delivers comprehensive security coverage for critical AI infrastructure components. Current supported components and vulnerability statistics:

| Category                   | Component Name          | Vulnerability Count | Risk Level |
| -------------------------- | ----------------------- | ------------------- | ---------- |
| **Model Serving**          | gradio                  | 42                  | High       |
|                            | ollama                  | 7                   | Medium-High|
|                            | triton-inference-server | 7                   | Medium-High|
|                            | vllm                    | 4                   | Medium     |
|                            | xinference              | 0                   | Low        |
| **LLM App Frameworks**     | langchain               | 33                  | High       |
|                            | dify                    | 11                  | High       |
|                            | anythingllm             | 8                   | Medium-High|
|                            | open-webui              | 8                   | Medium-High|
|                            | ragflow                 | 2                   | Medium     |
|                            | qanything               | 2                   | Medium     |
| **Data Processing**        | clickhouse              | 22                  | High       |
|                            | feast                   | 0                   | Low        |
| **Visualization & UI**     | jupyter-server          | 13                  | Medium-High|
|                            | jupyterlab              | 6                   | Medium     |
|                            | jupyter-notebook        | 1                   | Low        |
|                            | tensorboard             | 0                   | Low        |
| **Workflow Orchestration** | kubeflow                | 4                   | Medium     |
|                            | ray                     | 4                   | Medium     |
| **Other AI Components**    | comfyui                 | 1                   | Low        |
|                            | comfy_mtb               | 1                   | Low        |
|                            | ComfyUI-Prompt-Preview  | 1                   | Low        |
|                            | ComfyUI-Custom-Scripts  | 1                   | Low        |
|                            | pyload-ng               | 18                  | Medium     |
|                            | kubepi                  | 5                   | Medium     |
|                            | llamafactory            | 1                   | Low        |
| **Total**                  |                         | **200+**            |            |

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

### Example: Gradio Fingerprint Rule

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