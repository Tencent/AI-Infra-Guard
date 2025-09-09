<p align="center">
    <h1 align="center"><img vertical-align=“middle” width="400px" src="img/logo-full-new.png" alt="A.I.G"/></h1>
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

**A.I.G (AI-Infra-Guard)** integrates capabilities such as AI infra vulnerability scan, MCP Server risk scan, and Jailbreak Evaluation, aiming to provide users with the most comprehensive, intelligent, and user-friendly solution for AI security risk self-examination.

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
      <h3>🔍 AI Infra Scan</h3>
      <p>Precisely identifies <b>30+</b> AI framework components<br/>Covers <b>nearly 400</b> known CVE vulnerabilities<br/>Including Ollama, ComfyUI, vLLM, etc.</p>
    </td>
    <td>
      <h3>🤖 MCP Scan</h3>
      <p>Powered by AI Agent<br />Detects <b>9 major categories</b> of MCP security risks<br/>Supports <b>source code/remote URL</b> scanning</p>
    </td>
    <td>
      <h3>⚡ Jailbreak Evaluation</h3>
      <p>Rapidly assesses Prompt security risks<br/>Includes multiple curated jailbreak evaluation datasets<br/>Quickly generates Jailbreak Evaluation reports</p>
    </td>
  </tr>
</table>
<br />

## 🖼️ Showcase

### A.I.G Main Interface
![AIG Main Page](img/background-en.png)

### AI Infra Scan
![One-click scan to discover AI component security vulnerabilities](img/ai-infra-scan-en.png)

### MCP Scan
![Intelligently analyze MCP Server security risks](img/mcp-server-en.png)

### Jailbreak Evaluation
![Comprehensively evaluate LLM security](img/model-security-en.png)

### Plugin Management
<table>
  <tr>
    <td valign="top"><img align=top src="img/plugin-1-en.png"/></td>
    <td valign="top"><img align=top src="img/plugin-2-en.png"/></td>
  </tr>
</table>

<br />

## 🚀 Quick Start
### Deployment with Docker

**System Requirements**

- Docker 20.10 or higher
- At least 4GB of available RAM
- At least 10GB of available disk space


**1. One-Click Install Script （Recommended）**
```bash
# This method will automatically install Docker and launch A.I.G with one command  
curl https://raw.githubusercontent.com/Tencent/AI-Infra-Guard/refs/heads/main/docker.sh | bash
```

**2. Run with pre-built images (Recommended)**
```bash
git clone https://github.com/Tencent/AI-Infra-Guard.git
cd AI-Infra-Guard
# This method pulls pre-built images from Docker Hub for a faster start
docker-compose -f docker-compose.images.yml up -d
```

**3. Build from source and run**
```bash
git clone https://github.com/Tencent/AI-Infra-Guard.git
cd AI-Infra-Guard
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

The extensible plugin framework​​ serves as A.I.G's architectural cornerstone, inviting community innovation through Plugin and Feature contributions.​

### Plugin Contribution Rules
1.  **Fingerprint Rules**: Add new YAML fingerprint files to the `data/fingerprints/` directory.
2.  **Vulnerability Rules**: Add new vulnerability scan rules to the `data/vuln/` directory.
3.  **MCP Plugins**: Add new MCP security scan rules to the `data/mcp/` directory.
4.  **Jailbreak Evaluation Datasets**: Add new Jailbreak evaluation datasets to the `data/eval` directory.

Please refer to the existing rule formats, create new files, and submit them via a Pull Request.

### Other Ways to Contribute
- 🐛 [Report a Bug](https://github.com/Tencent/AI-Infra-Guard/issues)
- 💡 [Suggest a New Feature](https://github.com/Tencent/AI-Infra-Guard/issues)
- ⭐ [Improve Documentation](https://github.com/Tencent/AI-Infra-Guard/pulls)
  <br />

## 🙏 Acknowledgements

We extend deep gratitude to these open-source developers:
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
