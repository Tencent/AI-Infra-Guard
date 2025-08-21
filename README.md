<<<<<<< HEAD
# 🛡️ A.I.G（AI-Infra-Guard）
[中文版](./README_CN.md)  

A comprehensive, intelligent, easy-to-use, and lightweight AI Infrastructure Vulnerability Assessment and MCP Server Security Analysis Tool, developed by Tencent Zhuque Lab.

**工具反馈问卷**
> A.I.G（AI-Infra-Guard）年初发布至今一直保持快速迭代中，为了打造更全面、智能、易用的全新的AI安全红队平台并吸引更多用户共建，在此特别邀请您参与一个5分钟的用户需求调研，对于有价值的反馈将我们后续会安排寄送腾讯特色小礼品，感谢大家的关注与支持。

https://doc.weixin.qq.com/forms/AJEAIQdfAAoAbUAxgbhAIQCNfZu1TQeRf

## Table of Contents

- [🚀 Quick Preview](#-quick-preview)
- [✨ Project Highlights](#-project-highlights)
- [📋 Feature Description](#-feature-description)
- [🤝 MCP Security Certification and Cooperation](#mcp-security-certification-and-cooperation)
- [📦 Installation and Usage](#-installation-and-usage)
  - [Installation](#installation)
  - [Command Line Structure](#command-line-structure)
  - [Usage](#usage)
    - [WebUI Visual Operation](#webui-visual-operation)
    - [Security Vulnerability Scanning (scan)](#security-vulnerability-scanning-scan)
    - [MCP Server Scanning (mcp)](#mcp-server-scanning-mcp)
- [📊 Covered MCP Security Risks](#-covered-mcp-security-risks)
- [📊 Covered AI Component Vulnerabilities](#-covered-ai-component-vulnerabilities)
- [🔍 Component Fingerprinting Rules](#-component-fingerprinting-rules)
  - [Example: Gradio Fingerprint Rule](#example-gradio-fingerprint-rule)
  - [Fingerprint Matching Syntax](#fingerprint-matching-syntax)
- [🤝 Contribution](#-contribution)
- [📄 License](#-license)

## 🚀 Quick Preview

**MCP Server Code/Online Service Analysis**
<br>
<img src="img/mcp-en.png" alt="MCP Server Code Detection Preview" height="600">
<br>

**Infrastructure Vulnerability Scanning**
<br>
<img src="img/scan-en.png" alt="Infrastructure Detection Preview" height="600">
<br>

## ✨ Project Highlights

*   **Comprehensive Security Assessment Capabilities**
  *   Supports analysis of 9 common MCP security risks, continuously updated.
  *   Supports identification of 28 AI component frameworks, covering 200+ vulnerability fingerprints.
  *   Supports private deployment for easy integration into internal security scanning pipelines.
*   **Intelligent and User-Friendly Experience**
  *   MCP security analysis driven by AI Agent for one-click intelligent analysis.
  *   AI component vulnerability scanning supports custom fingerprints and YAML vulnerability rules.
  *   Out-of-the-box usability with no complex configuration required, providing a Web interface for visual operation.
*   **Lightweight Design**
  *   Core components are concise and efficient.
  *   Small binary size and low resource consumption.
  *   Cross-platform support (Windows/MacOS/Linux).

## 🤝 MCP Security Certification and Cooperation
AI Infra Guard is committed to providing professional MCP security analysis and certification solutions. We welcome MCP marketplaces, developer platforms, and hosting providers to integrate our tool into their pre-listing security scanning process for MCP Servers and display the scan results in the MCP marketplace, collectively building a safer MCP ecosystem.

If you are interested in cooperating with us, please contact Tencent Zhuque Lab at zhuque [at] tencent.com.

We also welcome you to share your implementation cases within the MCP community.

## 📋 Feature Description

AI Infra Guard consists of three core modules:

1.  **AI Component Vulnerability Scanning (`scan`)**: Detects known security vulnerabilities in web-based components within AI infrastructure.
2.  **MCP Security Analysis (`mcp`)**: Analyzes security risks in MCP Server code based on AI Agent.
3.  **WebUI Mode (`webserver`)**: Enables the web-based visual operation interface.

## 📦 Installation and Usage

### Installation

Download the latest version suitable for your operating system from the [Releases](https://github.com/Tencent/AI-Infra-Guard/releases) page.

### Command Line Structure

AI Infra Guard uses a subcommand structure:

```bash
./ai-infra-guard <subcommand> [options]
```

Main subcommands:

*   `scan`: Executes AI component security vulnerability scanning.
*   `mcp`: Executes MCP Server code security analysis.
*   `webserver`: Starts the Web interface server.

### Usage

#### WebUI Visual Operation

Start the web server, listening on `127.0.0.1:8088` by default:

```bash
./ai-infra-guard webserver
```

Specify the listening address and port:

```bash
./ai-infra-guard webserver --ws-addr <IP>:<PORT>
```
*Example: `./ai-infra-guard webserver --ws-addr 0.0.0.0:9090`*

#### AI Component Vulnerability Scanning (`scan`)

**Local One-Click Detection** (Scans common local service ports):

```bash
./ai-infra-guard scan --localscan
```

**Scan a Single Target**:

```bash
./ai-infra-guard scan --target <IP/Domain>
```
*Example: `./ai-infra-guard scan --target example.com`*

**Scan Multiple Targets**:

```bash
./ai-infra-guard scan --target <IP/Domain1> --target <IP/Domain2>
```
*Example: `./ai-infra-guard scan --target 192.168.1.1 --target example.org`*

**Read Targets from a File**:

```bash
./ai-infra-guard scan --file target.txt
```
*The `target.txt` file should contain one target URL or IP address per line.*

**View Full Parameters for the `scan` Subcommand**:

```bash
./ai-infra-guard scan --help
```

**`scan` Subcommand Parameter Description**:

```
Usage:
  ai-infra-guard scan [flags]

Flags:
      --ai                      Enable AI analysis (requires LLM Token configuration)
      --check-vul               Validate the effectiveness of vulnerability templates
      --deepseek-token string   DeepSeek API token (for --ai feature)
  -f, --file string             File path containing target URLs
      --fps string              Fingerprint template file or directory (default: "data/fingerprints")
      --header stringArray      Custom HTTP request headers (can be specified multiple times, format: "Key:Value")
  -h, --help                    Show help information
      --hunyuan-token string    Hunyuan API token (for --ai feature)
      --lang string             Response language (zh/en, default: "zh")
      --limit int               Maximum requests per second (default: 200)
      --list-vul                List all available vulnerability templates
      --localscan               Perform local one-click scan
  -o, --output string           Result output file path (supports .txt, .json, .csv formats)
      --proxy-url string        HTTP/SOCKS5 proxy server URL
  -t, --target stringArray      Target URL (can be specified multiple times)
      --timeout int             HTTP request timeout in seconds (default: 5)
      --vul string              Vulnerability database directory (default: "data/vuln")
```

#### MCP Server Security Risk Analysis (`mcp`)

This feature automatically analyzes security issues in MCP Server code using an AI Agent.

**Basic Usage** (Uses OpenAI API by default, requires Token):

```bash
./ai-infra-guard mcp --code <source_code_path> --model <model_name> --token <api_token> [--base-url <api_base_url>]
```
*Example: `./ai-infra-guard mcp --code /path/to/mcp/server --model gpt-4 --token sk-xxxxxx`*

**Specify Output Format**:

```bash
./ai-infra-guard mcp --code <source_code_path> --model <model_name> --token <api_token> --csv results.csv --json results.json
```

**View Full Parameters for the `mcp` Subcommand**:

```bash
./ai-infra-guard mcp --help
```

**`mcp` Subcommand Parameter Description**:

```
Usage:
  ai-infra-guard mcp [flags]

Flags:
      --base-url string   LLM API base URL (optional, overrides default OpenAI URL)
      --code string       Path to the MCP Server source code to scan (required)
      --csv string        Output results to a CSV file path
  -h, --help              Show help information
      --json string       Output results to a JSON file path
      --log string        Log file save path
      --model string      AI model name (required, e.g., gpt-4, gpt-3.5-turbo)
      --plugins string    Specify enabled plugins list (comma-separated, optional)
      --token string      LLM API token (required)
```

## 📊 Covered MCP Security Risks

AI Infra Guard can analyze the following common MCP security risks, with continuous updates:

| Risk Name                   | Risk Description                                                                                                                                                                                                                            |
|-----------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Tool Poisoning Attack       | Malicious MCP Server injects hidden instructions via tool descriptions to manipulate the AI Agent into performing unauthorized actions (e.g., data exfiltration, executing malicious code or commands).                                                    |
| Rug Pull                | Malicious MCP Server behaves normally initially but changes behavior after user approval or several runs to execute malicious instructions, leading to difficult-to-detect malicious activities.                                                    |
| Tool Shadowing Attack      | Malicious MCP Server uses hidden instructions to redefine the behavior of other trusted MCP Server tools (e.g., modifying email recipients, executing unauthorized operations).                                                               |
| Malicious Code/Command Execution | If an MCP Server supports direct code or command execution without proper sandboxing, attackers could exploit it to execute malicious operations on the server or user's local machine.                                                        |
| Data Exfiltration           | Malicious MCP Server induces the AI Agent to exfiltrate sensitive data (e.g., API keys, SSH keys) or directly transmits user-authorized input data to external servers.                                                                     |
| Unauthorized Access/Authentication | MCP Server lacks effective authorization/authentication mechanisms or has flaws, allowing attackers to bypass verification and access restricted resources or user data.                                                                               |
| Indirect Prompt Injection   | MCP Server outputs external data containing malicious instructions (e.g., web pages, documents) to the AI Agent, potentially compromising the AI Agent's integrity and leading to unintended actions.                                                               |
| Package Name Squatting      | Malicious MCP Server uses names, tool names, or descriptions similar to trusted services to trick the AI Agent into invoking malicious services; or a third party squats on an official MCP Server name to distribute malware or implant backdoors. |
| Insecure Storage of Sensitive Keys | MCP Server hardcodes or stores sensitive keys in plaintext within code or configuration files, leading to potential key leakage risks.                                                                                                          |

## 📊 Covered AI Component Vulnerabilities

AI Infra Guard supports detection of known vulnerabilities in various AI-related components:

| Component Name           | Vulnerability Count |
|--------------------------|---------------------|
| anythingllm              | 8                   |
| langchain                | 33                  |
| Chuanhugpt               | 0                   |
| clickhouse               | 22                  |
| comfy_mtb                | 1                   |
| ComfyUI-Prompt-Preview   | 1                   |
| ComfyUI-Custom-Scripts   | 1                   |
| comfyui                  | 1                   |
| dify                     | 11                  |
| fastchat-webui           | 0                   |
| fastchat                 | 1                   |
| feast                    | 0                   |
| gradio                   | 42                  |
| jupyterlab               | 6                   |
| jupyter-notebook         | 1                   |
| jupyter-server           | 13                  |
| kubeflow                 | 4                   |
| kubepi                   | 5                   |
| llamafactory             | 1                   |
| llmstudio                | 0                   |
| ollama                   | 7                   |
| open-webui               | 8                   |
| pyload-ng                | 18                  |
| qanything                | 2                   |
| ragflow                  | 2                   |
| ray                      | 4                   |
| tensorboard              | 0                   |
| vllm                     | 4                   |
| xinference               | 0                   |
| triton-inference-server  | 7                   |
| **Total**                | **200+**            |

*Note: The vulnerability database is continuously updated.*

## 🔍 Component Fingerprinting Rules

AI Infra Guard uses YAML-based rules for web component fingerprinting and vulnerability matching.

*   **Fingerprint Rules**: Stored in the `data/fingerprints` directory.
*   **Vulnerability Rules**: Stored in the `data/vuln` directory.

### Example: Gradio Fingerprint Rule (`data/fingerprints/gradio.yaml`)

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
      # Match if the response body contains Gradio-specific JavaScript configuration or elements
      - body="<script>window.gradio_config = {" || body="document.getElementsByTagName(\"gradio-app\");"
```

### Fingerprint Matching Syntax

#### Match Locations

*   `title`: HTML page title
*   `body`: HTTP response body
*   `header`: HTTP response header
*   `icon`: Hash value (e.g., MurmurHash3) of the website's favicon

#### Logical Operators

*   `=`: Fuzzy contains match (case-insensitive)
*   `==`: Exact equals match (case-sensitive)
*   `!=`: Not equals match
*   `~=`: Regular expression match
*   `&&`: Logical AND
*   `||`: Logical OR
*   `()`: Used for grouping to change operator precedence

## 🤝 Contribution

We welcome community contributions!

*   **Report Issues**: [Submit an Issue](https://github.com/Tencent/AI-Infra-Guard/issues)
*   **Submit Code**: [Create a Pull Request](https://github.com/Tencent/AI-Infra-Guard/pulls)
## Wechat Group
![](img/wechatgroup.png)

## 📄 License

This project is open-sourced under the **MIT License**. For details, please refer to the [License.txt](./License.txt) file.

---
[![Star History Chart](https://api.star-history.com/svg?repos=Tencent/AI-Infra-Guard&type=Date)](https://star-history.com/#Tencent/AI-Infra-Guard&Date)
=======
                       
<p align="center">
    <h1 align="center">🛡️ A.I.G (AI-Infra-Guard)</h1>
</p>
<p align="center">
    <a href="https://github.com/Tencent/AI-Infra-Guard">
        <img alt="GitHub Stars" src="https://img.shields.io/github/stars/Tencent/AI-Infra-Guard?color=gold">
    </a>
    <a href="https://github.com/Tencent/AI-Infra-Guard">
        <img alt="License" src="https://img.shields.io/badge/license-MIT-blue">
    </a>
    <a href="https://github.com/Tencent/AI-Infra-Guard">
        <img alt="Release" src="https://img.shields.io/github/v/release/Tencent/AI-Infra-Guard?color=green">
    </a>
</p>
<h4 align="center">
    <p>
        <a href="https://tencent.github.io/AI-Infra-Guard/">帮助文档</a> |
        <a href="#">中文</a> |
        <a href="./README_EN.md">英文</a>
    <p>
</h4>

<p align="center">
    <h3 align="center">🚀 腾讯朱雀实验室推出的一站式 AI 红队安全测试平台</h3>
</p>
  

  

**A.I.G (AI-Infra-Guard)** 集成AI基础设施漏洞扫描、MCP Server风险检测与大模型安全体检等能力，旨在为用户提供最全面、智能与易用的AI安全风险自查解决方案。


## 目录
- [✨ 核心功能](#-核心功能)
- [🖼️ 功能展示](#-功能展示)
- [🚀 快速开始](#-快速开始)
- [🙏 贡献指南](#-贡献指南)
- [💬 加入社区](#-加入社区)
- [📄 开源协议](#-开源协议)


## ✨ 核心功能

<table>
  <tr>
    <td>
      <h3>🔍 AI 基础设施漏洞扫描</h3>
      <p>精准识别 <b>30+</b> AI 框架组件<br/>覆盖 <b>近400个</b> 已知 CVE 漏洞<br/>如 Ollama、ComfyUI、vLLM 等</p>
    </td>
    <td>
      <h3>🤖 MCP Server 安全检测</h3>
      <p>基于AI Agent驱动<br />检测 <b>9 大类</b>MCP安全风险<br/>支持<b>源代码/远程URL</b>扫描</p>
    </td>
    <td>
      <h3>⚡ 大模型安全体检</h3>
      <p>快速接入评估模型Prompt安全性<br/>内置多个主流&独家评测集<br/>快速获取大模型安全体检报告</p>
    </td>
  </tr>
</table>
<br />

## 🖼️ 功能展示

### A.I.G 主界面
![AIG首页](img/background.png)

### AI 基础设施漏洞扫描
![一键扫描发现 AI 组件安全漏洞](img/ai-infra-scan.png)

### MCP Server 安全检测
![智能分析 MCP Server 安全风险](img/mcp-server.png)

### 大模型安全体检
![全面评估大模型安全性](img/model-security.png)

### 插件管理
<table>
  <tr>
    <td valign="top"><img align=top src="img/plugin-1.png"/></td>
    <td valign="top"><img align=top src="img/plugin-2.png"/></td>
  </tr>
</table>

<br />

## 🚀 快速开始
### Docker 一键部署

**系统要求**

- Docker 20.10 或更高版本
- 至少 4GB 可用内存
- 至少 10GB 可用磁盘空间

首先，克隆本项目：
```bash
git clone https://github.com/Tencent/AI-Infra-Guard.git
cd AI-Infra-Guard
```

然后安装好[Docker相关环境](https://docs.docker.com/get-started/get-docker/)，您可以选择以下任一方式部署A.I.G服务：

**1. 使用预构建镜像运行 (推荐)**
```bash
# 此方法会从 Docker Hub 拉取预构建的镜像，启动速度更快
docker-compose -f docker-compose.images.yml up -d
```
**2. 从源码构建并运行**
```bash
# 此方法会使用本地代码构建 Docker 镜像并启动服务
docker-compose up -d
```

服务启动后，即可访问A.I.G的 Web 界面：
`http://localhost:8088`

**目录说明**

| 目录/文件      | 说明               | 挂载路径                      |
|------------|------------------|---------------------------|
| `uploads/` | 上传文件存储目录         | `/ai-infra-guard/uploads` |
| `db/`      | 数据库文件目录          | `/ai-infra-guard/db`      |
| `data/`    | 知识库数据目录（指纹库、漏洞库） | `/ai-infra-guard/data`    |
| `logs/`    | 应用日志目录           | `/ai-infra-guard/logs`    |

<br />

## 📝 贡献指南

A.I.G 的核心能力之一就是其丰富且可快速配置的插件系统。我们欢迎社区贡献高质量的插件和功能。

### 贡献插件规则
1.  **指纹规则**: 在 `data/fingerprints/` 目录下添加新的 YAML 指纹文件
2.  **漏洞规则**: 在 `data/vuln/` 目录下添加新的漏洞检测规则
3.  **MCP 插件**: 在 `data/mcp/` 目录下添加新的 MCP 安全检测规则
4.  **模型评测集**: 在 `data/eval` 目录下添加新的模型评测集

请参考现有规则格式，创建新文件并通过 Pull Request 提交。

### 其他贡献方式
- 🐛 [报告 Bug](https://github.com/Tencent/AI-Infra-Guard/issues)
- 💡 [提出新功能](https://github.com/Tencent/AI-Infra-Guard/issues)
- ⭐ [改进文档](https://github.com/Tencent/AI-Infra-Guard/pulls)
<br />

## 🙏 致谢

感谢以下安全团队的专业共建:
<table>
  <tr>
    <td width="33%"><img src="img/keen_lab_logo.svg" alt="Keen Lab"></td>
    <td width="33%"><img src="img/wechat_security.png" alt="WeChat Security"></td>
    <td width="33%"><img src="img/fit_sec_logo.png" alt="Fit Security"></td>
  </tr>
</table>

<br>

感谢为 A.I.G 项目贡献代码的开发者：

<a href="https://github.com/Tencent/AI-Infra-Guard/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=Tencent/AI-Infra-Guard" />
</a>

<br>

## 💬 加入社区

<div>
  <img src="img/wechatgroup.png" alt="微信群" width="200">
  <p><b>微信扫码加入 A.I.G 交流群</b></p>
</div>
如您有合作需求或问题反馈，可以通过以下邮箱联系我们: zhuque(at)tencent.com

<br><br>

## 📄 开源协议

本项目基于 **MIT 许可证** 开源。详细信息请查阅 [License.txt](./License.txt) 文件。

<div>

  [![Star History Chart](https://api.star-history.com/svg?repos=Tencent/AI-Infra-Guard&type=Date)](https://star-history.com/#Tencent/AI-Infra-Guard&Date)

</div>
>>>>>>> opensource
