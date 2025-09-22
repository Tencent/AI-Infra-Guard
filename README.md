<p align="center">
    <h1 align="center"><img vertical-align=“middle” width="400px" src="img/logo-full-new.png" alt="A.I.G"/></h1>
</p>
<h4 align="center">
    <p>
        <a href="https://tencent.github.io/AI-Infra-Guard/">Documentation</a> |
        <a href="./README_ZH.md">中文</a> |
        <a href="#">English</a>
    <p>
</h4>
<p align="center">
    <a href="https://github.com/Tencent/AI-Infra-Guard">
        <img alt="GitHub Stars" src="https://img.shields.io/github/stars/Tencent/AI-Infra-Guard?color=gold">
    </a>
    <a href="https://github.com/Tencent/AI-Infra-Guard">
        <img alt="GitHub Stars" src="https://img.shields.io/github/downloads/Tencent/AI-Infra-Guard/total">
    </a>
    <a href="https://github.com/Tencent/AI-Infra-Guard">
        <img alt="GitHub Stars" src="https://img.shields.io/docker/pulls/zhuquelab/aig-server.svg?color=gold">
    </a>
    <a href="https://github.com/Tencent/AI-Infra-Guard">
        <img alt="Release" src="https://img.shields.io/github/v/release/Tencent/AI-Infra-Guard?color=green">
    </a>
    <a href="https://deepwiki.com/Tencent/AI-Infra-Guard">
       <img src="https://deepwiki.com/badge.svg" alt="Ask DeepWiki">
    </a>
</p>
<p align="center">
  <a href="https://trendshift.io/repositories/13637" target="_blank"><img src="https://trendshift.io/api/badge/repositories/13637" alt="Tencent%2FAI-Infra-Guard | Trendshift" style="width: 250px; height: 55px;" width="250" height="55"/></a>
  <a href="https://www.blackhat.com/eu-25/arsenal/schedule/index.html#aigai-infra-guard-48381" target="_blank"><img src="img/blackhat.png" alt="Tencent%2FAI-Infra-Guard | blackhat" style="width: 175px; height: 55px;" width="175" height="55"/></a>
  <a href="https://github.com/deepseek-ai/awesome-deepseek-integration" target="_blank"><img src="img/awesome-deepseek.png" alt="Tencent%2FAI-Infra-Guard | awesome-deepseek-integration" style="width: 273px; height: 55px;" width="273" height="55"/></a>
</p>

<br>
<p align="center">
    <h2 align="center">🚀 AI Red Teaming Platform by Tencent Zhuque Lab</h2>
</p>

**A.I.G (AI-Infra-Guard)** integrates capabilities such as AI infra vulnerability scan, MCP Server risk scan, and Jailbreak Evaluation, aiming to provide users with the most comprehensive, intelligent, and user-friendly solution for AI security risk self-examination.

<p>
  We are committed to making A.I.G(AI-Infra-Guard) the industry-leading AI red teaming platform. More stars help this project reach a wider audience, attracting more developers to contribute, which accelerates iteration and improvement. Your star is crucial to us!
</p>
<p align="center">
  <a href="https://github.com/Tencent/AI-Infra-Guard">
      <img src="https://img.shields.io/badge/⭐-Give%20us%20a%20Star-yellow?style=for-the-badge&logo=github" alt="Give us a Star">
  </a>
</p>

## Table of Contents
- [✨ Features](#-features)
- [🖼️ Showcase](#-showcase)
- [🚀 Quick Start](#-quick-start)
- [📖 User Guide](#-user-guide)
- [📝 Contribution Guide](#-contribution-guide)
- [🙏 Acknowledgements](#-acknowledgements)
- [💬 Join the Community](#-join-the-community)
- [📖 Citation](#-citation)
- [📚 Papers](#-papers)
- [📄 License](#-license)


## ✨ Features


1.  **🔍 Detect AI Infra Risk:** Precisely identifies 30+ AI framework components, Covers nearly 400 known CVE vulnerabilities, Including Ollama, ComfyUI, vLLM, etc.

2. **🤖 Detect MCP Server Risk:** Powered by AI Agent, Detects 9 major categories of MCP security risks, Supports source code/remote URL scanning.

3. **⚡ Jailbreak Evaluation:** Rapidly assesses Prompt security risks, Includes multiple curated jailbreak evaluation datasets, Cross-model security performance comparison.

4. **🖥️ Intuitive Web Interface:** Modern, user-friendly web UI for seamless operation, One-click scanning with real-time progress tracking, Comprehensive Analysis Reports.

5. **🌍 Multi-Language Support:** 🇨🇳 Chinese and 🇺🇸 English interface, Localized documentation and help.

6. **🖵 Cross-Platform Compatibility:** 🐧 Linux, 🍎 macOS, and 🪟 Windows support, Docker-based deployment.

7. **💰 Free & Open Source with MIT license**



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
![Plugin Management](img/plugin-gif.gif)

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
<br>
<br>
## 📖 User Guide

Visit our online documentation: [https://tencent.github.io/AI-Infra-Guard/](https://tencent.github.io/AI-Infra-Guard/)

For more detailed FAQs and troubleshooting guides, visit our [documentation](https://tencent.github.io/AI-Infra-Guard/).
<br />
<br>

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

Thanks to all the developers who have contributed to the A.I.G project:
<br />
<table style="border: none; border-collapse: inherit;">
  <tr>
    <td width="33%" style="border: none;"><img src="img/keen_lab_logo.svg" alt="Keen Lab" height="85%"></td>
    <td width="33%" style="border: none;"><img src="img/wechat_security.png" alt="WeChat Security" height="85%"></td>
    <td width="33%" style="border: none;"><img src="img/fit_sec_logo.png" alt="Fit Security" height="85%"></td>
  </tr>
</table>
<a href="https://github.com/Tencent/AI-Infra-Guard/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=Tencent/AI-Infra-Guard" />
</a>
<br>
<br>
We are deeply grateful to the following teams and organizations for their trust, and valuable feedback in using A.I.G.
Your contributions have been instrumental in making A.I.G a more robust and reliable AI Red Team platform.
<br>
(待确定后改为logo)

- **Tencent**
- **DeepSeek**

#### 📊 User Registration
If you are using A.I.G, please let us know! Your usage is very important to us (new registrations will be prioritized in order, with dedicated support for priority Q&A and Pro Version):
 💬 [Submit Usage Registration](https://github.com/Tencent/AI-Infra-Guard/issues)

<br>

## 💬 Join the Community

### 🌐 Online Discussions
- **GitHub Discussions**: [Join our community discussions](https://github.com/Tencent/AI-Infra-Guard/discussions)
- **Issues & Bug Reports**: [Report issues or suggest features](https://github.com/Tencent/AI-Infra-Guard/issues)

### 📱 WeChat Community
<div>
  <img src="img/wechatgroup.png" alt="WeChat Group" width="200">
  <p>Scan the WeChat QR code to join the A.I.G community group</p>
</div>

### 📧 Contact Us
For collaboration inquiries or feedback, please contact us at: zhuque@tencent.com



### 🌟 Thank You to Our Stargazers!

We are deeply grateful to all the developers who have starred our repository!
<div align="center">
  <img src="img/stargazers.png" alt="Stargazers" width="100%">
</div>

Thank you to users from **Peking University, Google, Alibaba, Tsinghua University, ByteDance, Microsoft, Amazon, Huawei, Meituan, Douban, HFUT, cuit**, and many more amazing stargazers!

<p align="center">
  ⭐ Every star encourages us to keep improving and innovating! ⭐
</p>
<p align="center">
    🚀 Help us reach more developers by starring this repository. 🚀
</p>

<p align="center">
  <a href="https://github.com/Tencent/AI-Infra-Guard">
      <img src="https://img.shields.io/badge/⭐-Give%20us%20a%20Star-yellow?style=for-the-badge&logo=github" alt="Give us a Star">
  </a>
</p>

</div>

[![Star History Chart](https://api.star-history.com/svg?repos=Tencent/AI-Infra-Guard&type=Date)](https://star-history.com/#Tencent/AI-Infra-Guard&Date)
<br>
<br>

## 📖 Citation

If you use A.I.G in your research or product, please cite:

```bibtex
@misc{Tencent_AI-Infra-Guard_2025,
  author={{Tencent Zhuque Lab}},
  title={{AI-Infra-Guard: A Comprehensive, Intelligent, and Easy-to-Use AI Red Teaming Platform}},
  year={2025},
  howpublished={GitHub repository},
  url={https://github.com/Tencent/AI-Infra-Guard}
}
```
<br>

## 📚 Related Papers

We are deeply grateful to the research teams who have used A.I.G in their academic work and contributed to advancing AI security research:

[1] Yongjian Guo, Puzhuo Liu, et al. **"Systematic Analysis of MCP Security."** arXiv preprint arXiv:2508.12538 (2025). [[pdf]](https://arxiv.org/abs/2508.12538)  
[2] Zexin Wang, Jingjing Li, et al. **"A Survey on AgentOps: Categorization, Challenges, and Future Directions."** arXiv preprint arXiv:2508.02121 (2025). [[pdf]](https://arxiv.org/abs/2508.02121)  
[3] Yixuan Yang, Daoyuan Wu, Yufan Chen. **"MCPSecBench: A Systematic Security Benchmark and Playground for Testing Model Context Protocols."** arXiv preprint arXiv:2508.13220 (2025). [[pdf]](https://arxiv.org/abs/2508.13220)

📧 If you have used A.I.G in your research, we would love to hear from you! [Contact us here](#-join-the-community).
<br>
<br>

## 📄 License

This project is licensed under the **MIT License**. See the [License.txt](./License.txt) file for details.

<div>
