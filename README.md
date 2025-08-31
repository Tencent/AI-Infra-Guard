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
    <a href="https://deepwiki.com/Tencent/AI-Infra-Guard">
        <img src="https://deepwiki.com/badge.svg" alt="Ask DeepWiki">
    </a>
</p>
<h4 align="center">
    <p>
        <a href="https://tencent.github.io/AI-Infra-Guard/">Documentation</a> |
        <a href="./README_ZH.md">中文</a> |
        <a href="#">English</a>
    <p>
</h4>

<p align="center">
    <h3 align="center">🚀 AI Red Teaming Platform by Tencent Zhuque Lab</h3>
</p>

**A.I.G (AI-Infra-Guard)** integrates capabilities such as AI infrastructure vulnerability scanning, MCP Server risk detection, and LLM security assessments, aiming to provide users with the most comprehensive, intelligent, and user-friendly solution for AI security risk self-examination.

## Table of Contents
- [✨ Features](#-features)
- [🖼️ Showcase](#-showcase)
- [🚀 Quick Start](#-quick-start)
- [🙏 Contribution Guide](#-contribution-guide)
- [💬 Join the Community](#-join-the-community)
- [📄 License](#-license)


## ✨ Features

<table>
  <tr>
    <td>
      <h3>🔍 AI Infrastructure Vulnerability Scanning</h3>
      <p>Precisely identifies <b>30+</b> AI framework components<br/>Covers <b>nearly 400</b> known CVE vulnerabilities<br/>Including Ollama, ComfyUI, vLLM, etc.</p>
    </td>
    <td>
      <h3>🤖 MCP Server Security Detection</h3>
      <p>Powered by AI Agent<br />Detects <b>9 major categories</b> of MCP security risks<br/>Supports <b>source code/remote URL</b> scanning</p>
    </td>
    <td>
      <h3>⚡ LLM Security Assessment</h3>
      <p>Rapidly assesses Prompt security risks<br/>Includes multiple curated jailbreak evaluation datasets<br/>Quickly generates LLM security assessment reports</p>
    </td>
  </tr>
</table>
<br />

## 🖼️ Showcase

### A.I.G Main Interface
![AIG Main Page](img/background.png)

### AI Infrastructure Vulnerability Scanning
![One-click scan to discover AI component security vulnerabilities](img/ai-infra-scan.png)

### MCP Server Security Detection
![Intelligently analyze MCP Server security risks](img/mcp-server.png)

### LLM Security Assessment
![Comprehensively evaluate LLM security](img/model-security.png)

### Plugin Management
<table>
  <tr>
    <td valign="top"><img align=top src="img/plugin-1.png"/></td>
    <td valign="top"><img align=top src="img/plugin-2.png"/></td>
  </tr>
</table>

<br />

## 🚀 Quick Start
### Deployment with Docker

**System Requirements**

- Docker 20.10 or higher
- At least 4GB of available RAM
- At least 10GB of available disk space

First, clone this project:
```bash
git clone https://github.com/Tencent/AI-Infra-Guard.git
cd AI-Infra-Guard
```

After installing the [Docker environment](https://docs.docker.com/get-started/get-docker/), you can deploy the A.I.G service in either of the following ways:

**1. Run with pre-built images (Recommended)**
```bash
# This method pulls pre-built images from Docker Hub for a faster start
docker-compose -f docker-compose.images.yml up -d
```
**2. Build from source and run**
```bash
# This method builds a Docker image from local source code and starts the service
docker-compose up -d
```

Once the service is running, you can access the A.I.G web interface at:
`http://localhost:8088`

**Directory Structure**

| Directory/File      | Description                                                 | Mount Path                      |
|---------------------|-------------------------------------------------------------|---------------------------------|
| `uploads/`          | Uploads directory                                           | `/ai-infra-guard/uploads`       |
| `db/`               | Database file directory                                     | `/ai-infra-guard/db`            |
| `data/`             | Knowledge base data directory (fingerprints, vulnerabilities) | `/ai-infra-guard/data`          |
| `logs/`             | Application log directory                                   | `/ai-infra-guard/logs`          |

<br />

## 📝 Contribution Guide

One of A.I.G's core strengths is its rich and highly configurable plugin system. We welcome community contributions of high-quality plugins and features.

### Plugin Contribution Rules
1.  **Fingerprint Rules**: Add new YAML fingerprint files to the `data/fingerprints/` directory.
2.  **Vulnerability Rules**: Add new vulnerability detection rules to the `data/vuln/` directory.
3.  **MCP Plugins**: Add new MCP security detection rules to the `data/mcp/` directory.
4.  **Model Evaluation Datasets**: Add new model evaluation datasets to the `data/eval` directory.

Please refer to the existing rule formats, create new files, and submit them via a Pull Request.

### Other Ways to Contribute
- 🐛 [Report a Bug](https://github.com/Tencent/AI-Infra-Guard/issues)
- 💡 [Suggest a New Feature](https://github.com/Tencent/AI-Infra-Guard/issues)
- ⭐ [Improve Documentation](https://github.com/Tencent/AI-Infra-Guard/pulls)
  <br />

## 🙏 Acknowledgements

We thank the following security teams for their professional collaboration:
<table>
  <tr>
    <td width="33%"><img src="img/keen_lab_logo.svg" alt="Keen Lab"></td>
    <td width="33%"><img src="img/wechat_security.png" alt="WeChat Security"></td>
    <td width="33%"><img src="img/fit_sec_logo.png" alt="Fit Security"></td>
  </tr>
</table>

<br>

Thanks to all the developers who have contributed code to the A.I.G project:

<a href="https://github.com/Tencent/AI-Infra-Guard/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=Tencent/AI-Infra-Guard" />
</a>

<br>

## 💬 Join the Community

<div>
  <img src="img/wechatgroup.png" alt="WeChat Group" width="200">
  <p><b>Scan the WeChat QR code to join the A.I.G community group</b></p>
</div>
For collaboration inquiries or feedback, please contact us at: zhuque(at)tencent.com

<br><br>

## 📄 License

This project is licensed under the **MIT License**. See the [License.txt](./License.txt) file for details.

<div>

[![Star History Chart](https://api.star-history.com/svg?repos=Tencent/AI-Infra-Guard&type=Date)](https://star-history.com/#Tencent/AI-Infra-Guard&Date)

</div>
