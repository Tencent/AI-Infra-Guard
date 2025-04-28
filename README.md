# 🛡️ AI Infrastructure Security Assessment System

[中文版](./README_CN.md)  

AI Infra Guard is the industry's first AI infrastructure security tool deeply integrated with MCP security detection. It provides comprehensive, intelligent MCP service code security scanning and AI infrastructure vulnerability detection features.

- Version 2 is now live, introducing AI Agent-based MCP Server code security scanning.

## 🚀 Quick Preview

**MCP Server Code Detection**  
<img src="img/mcp.png" height="600"><br>
**Infrastructure Detection**  
<img src="img/scan.png" height="600"><br>

## 🚀 Project Highlights

* **More comprehensive security detection capabilities**
  * Supports detection of 9 common MCP security risks, with continuous updates.
  * Supports identification of 28 AI component frameworks, covering over 200 vulnerability fingerprints.
  * Can be deployed privately, suitable for integration into internal security scanning pipelines.

* **Smarter, more user-friendly functionality**
  * MCP security detection is powered by AI Agent analysis, with reduced false positives and omissions.
  * AI component vulnerability scanning supports custom fingerprints and vulnerability YAML rules.
  * Out-of-the-box, no complex configuration, with a Web interface for visual operations.

* **Lightweight**
  * Core components are simple and efficient.
  * Small binary size, low resource usage.
  * Cross-platform support.

## 📋 Feature Description

The three core modules of AI Infra Guard:

1. **AI Component Security Scan (scan)** - Detect traditional web security vulnerabilities in AI component systems via command line.
2. **MCP Security Detection (mcp)** - Detect security issues in MCP Server code based on AI Agent via command line.
3. **WebUI Mode (webserver)** - Provides a Web visual operation interface.

## 📦 Installation and Usage

### Installation

Download link: [https://github.com/Tencent/AI-Infra-Guard/releases](https://github.com/Tencent/AI-Infra-Guard/releases)

### Command Line Structure

AI Infra Guard adopts a subcommand structure, providing three main subcommands:

```
ai-infra-guard [subcommand] [options]
```

Available subcommands:

- `scan`: Perform security vulnerability scanning.
- `mcp`: Perform MCP Server code security detection.
- `webserver`: Start the Web interface server.

### Usage

#### WEBUI Visualization

```
./ai-infra-guard webserver [--ws-addr 127.0.0.1:8088]
```

#### Security Vulnerability Scan (scan)

**Local Scan**

```
./ai-infra-guard scan --localscan
```

**Single Target**

```
./ai-infra-guard scan --target [IP/domain] 
```

**Multiple Targets**

```
./ai-infra-guard scan --target [IP/domain] --target [IP/domain]
```

**Read from File**

```
./ai-infra-guard scan --file target.txt
```

**Full Parameters**

```
./ai-infra-guard scan --help
```

Output:

```
Executes the raw scan function to scan the specified target for security vulnerabilities.

Usage:
  ai-infra-guard scan [flags]

Flags:
      --ai                      Enable AI analysis
      --check-vul               Validate vulnerability templates
      --deepseek-token string   DeepSeek API token
  -f, --file string             Path to the file containing target URLs
      --fps string              Fingerprint template file or directory (default "data/fingerprints")
      --header stringArray      HTTP request headers, can specify multiple, e.g.: --header "key:value" --header "key:value"
  -h, --help                    help for scan
      --hunyuan-token string    Hunyuan API token
      --lang string             Response language zh/en (default "zh")
      --limit int               Max requests per second (default 200)
      --list-vul                List vulnerability templates
      --localscan               One-click local scan
  -o, --output string           Output file path
      --proxy-url string        Proxy server URL
  -t, --target stringArray      Target URL, can specify multiple, e.g.: --target xx.com --target aa.com
      --timeout int             Request timeout in seconds (default 5)
      --vul string              Vulnerability database directory (default "data/vuln")
```

#### MCP Server Scan

MCP scan detects security issues in MCP Server based on AI Agent's automatic code analysis.

**Basic Usage**
The default LLM API interface uses OPENAI, customizable.

```
./ai-infra-guard mcp --code [source code path] --model [model name] --token [API token] --base-url 
```

**Specify Output Format**

```
./ai-infra-guard mcp --code [source code path] --model [model name] --token [API token] --csv results.csv --json results.json
```

**Full Parameters**

```
./ai-infra-guard mcp --help
```

Output:

```

Usage:
  ai-infra-guard mcp [flags]

Flags:
      --base-url string   LLM API base URL
      --code string       Source code path
      --csv string        Output CSV file path
  -h, --help              help for mcp
      --json string       Output JSON file path
      --log string        Log save path
      --model string      AI model name
      --plugins string    List of plugins, separated by commas
      --token string      API token
```

## 📊 MCP Security Risk Coverage

| Risk Name               | Risk Description                                                                                                                                                                                          |
|-------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Tool Poisoning Attack    | Malicious MCP services insert hidden instructions via tool descriptions to manipulate AI into executing unauthorized actions, stealing sensitive data, or performing malicious activities.                      |
| Carpet Scam              | Malicious MCP services alter behavior after initial approval or a few normal operations, changing from harmless tools to malicious ones, making it difficult for users to detect.                          |
| Tool Overlay Attack      | Malicious MCP services redefine behaviors of trusted MCP tools via hidden instructions, such as modifying email recipients or executing additional operations.                                            |
| Malicious Code/Command Execution | MCP services support executing code or commands without sandbox isolation, allowing attackers to execute malicious operations in hosted servers or local environments.                                 |
| Data Theft               | Malicious MCP services induce AI to read and transmit sensitive data (e.g., API keys, SSH keys), or directly send user-authorized input to external servers.                                               |
| Unauthorized Access/Authentication Flaw | MCP services lack proper authentication or authorization, allowing attackers to bypass validation and access restricted resources or user data.                                                      |
| Indirect Prompt Injection | MCP services output external data (e.g., web pages, documents) to AI dialogues, which may affect AI decisions and behavior if it contains malicious instructions.                                         |
| Package Name Confusion and Typosquatting | MCP client installed services have names or descriptions similar to official services, which could lead to incorrect AI calls or third-party services hijacking the official MCP services, introducing backdoors. |
| Plaintext Key Storage    | Sensitive MCP services hard-code or store plaintext keys in code or files, risking data leakage.                                                                                                          |

## 📊 AI Component Vulnerability Coverage

| Component Name           | Vulnerability Count |
|-------------------------|---------------------|
| anythingllm             | 8                   |
| langchain               | 33                  |
| Chuanhugpt              | 0                   |
| clickhouse              | 22                  |
| comfy_mtb               | 1                   |
| ComfyUI-Prompt-Preview  | 1                   |
| ComfyUI-Custom-Scripts  | 1                   |
| comfyui                 | 1                   |
| dify                    | 11                  |
| fastchat-webui          | 0                   |
| fastchat                | 1                   |
| feast                   | 0                   |
| gradio                  | 42                  |
| jupyterlab              | 6                   |
| jupyter-notebook        | 1                   |
| jupyter-server          | 13                  |
| kubeflow                | 4                   |
| kubepi                  | 5                   |
| llamafactory            | 1                   |
| llmstudio               | 0                   |
| ollama                  | 7                   |
| open-webui              | 8                   |
| pyload-ng               | 18                  |
| qanything               | 2                   |
| ragflow                 | 2                   |
| ray                     | 4                   |
| tensorboard             | 0                   |
| vllm                    | 4                   |
| xinference              | 0                   |
| triton-inference-server | 7                   |

## 🔍 Fingerprint Matching Rules

AI Infra Guard is based on web fingerprint recognition components, with fingerprint rules in the [data/fingerprints](./data/fingerprints) directory and vulnerability matching rules in the [data/vuln](./data/vuln) directory.

### Example: Gradio Fingerprint Rule

```yaml
info:
  name: gradio
  author: Security Team
  severity: info
  metadata:
    product: gradio
    vendor: gradio
http:
  - method: GET
    path: '/'
    matchers:
      - body="<script>window.gradio_config = {" || body="document.getElementsByTagName(\"gradio-app\");"
```

### 🛠️ Fingerprint Matching Syntax

#### Match Locations

- Title
- Body
- Header
- Icon hash

#### Logical Operators

- `=` Fuzzy match
- `==` Exact match
- `!=` Not equal
- `~=` Regex match
- `&&` And
- `||` Or
- `()` Grouping parentheses

## 🤝 Contributing

We welcome community contributions! Feel free to submit [PR](https://github.com/Tencent/AI-Infra-Guard/pulls) and [Issues](https://github.com/Tencent/AI-Infra-Guard/issues).

## Star History

[![Star History Chart](https://api.star-history.com/svg?repos=Tencent/AI-Infra-Guard&type=Date)](https://star-history.com/#Tencent/AI-Infra-Guard&Date)

## 📄 License

"AI Infra Guard" is licensed under the MIT License except for third-party components.  
Visit [License.txt](./License.txt)

---

💡 **Tip**: Stay updated and protect your AI infrastructure and MCP security!

---

I hope this helps! Let me know if you need any further adjustments!