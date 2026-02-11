<p align="center">
    <h1 align="center"><img vertical-align=“middle” width="400px" src="img/logo-full-new.png" alt="A.I.G"/></h1>
</p>
<h4 align="center">
    <p>
        <a href="https://tencent.github.io/AI-Infra-Guard/">Documentation</a> |
        <a href="./README_ZH.md">中文</a>
    <p>
</h4>
<p align="center">
    <a href="https://github.com/tencent/AI-Infra-Guard/stargazers">
      <img src="https://img.shields.io/github/stars/tencent/AI-Infra-Guard?style=social" alt="GitHub stars">
    </a>
    <a href="https://github.com/Tencent/AI-Infra-Guard">
        <img alt="GitHub downloads" src="https://img.shields.io/github/downloads/Tencent/AI-Infra-Guard/total">
    </a>
    <a href="https://github.com/Tencent/AI-Infra-Guard">
        <img alt="docker pulls" src="https://img.shields.io/docker/pulls/zhuquelab/aig-server.svg?color=gold">
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

**A.I.G (AI-Infra-Guard)** integrates capabilities such as AI infra vulnerability scan, MCP Server & Agent Skills scan, and Jailbreak Evaluation, aiming to provide users with the most comprehensive, intelligent, and user-friendly solution for AI security risk self-examination.

<p>
  We are committed to making A.I.G(AI-Infra-Guard) the industry-leading AI red teaming platform. More stars help this project reach a wider audience, attracting more developers to contribute, which accelerates iteration and improvement. Your star is crucial to us!
</p>
<p align="center">
  <a href="https://github.com/Tencent/AI-Infra-Guard">
      <img src="https://img.shields.io/badge/⭐-Give%20us%20a%20Star-yellow?style=for-the-badge&logo=github" alt="Give us a Star">
  </a>
</p>

<br>

> 📢 **News**:
> * A.I.G V3.6.2 AI Infrastructure Scanning now supports n8n (workflow automation platform) and adds detection for 78 CVEs across 15 AI components including Ollama. [View full changelog](./CHANGELOG.md)
> * A.I.G v3.6.1 Support Openclaw/clawdbot/moltbot Gateway unauthorized access risk detection.

## Table of Contents
- [🚀 Quick Start](#-quick-start)
- [✨ Features](#-features)
- [🖼️ Showcase](#-showcase)
- [📖 User Guide](#-user-guide)
- [🔧 API Documentation](#-api-documentation)
- [📝 Contribution Guide](#-contribution-guide)
- [🙏 Acknowledgements](#-acknowledgements)
- [💬 Join the Community](#-join-the-community)
- [📖 Citation](#-citation)
- [📚 Related Papers](#-related-papers)
- [📄 License](#-license)
<br><br>
## 🚀 Quick Start
### Deployment with Docker

| Docker | RAM | Disk Space |
|:-------|:----|:----------|
| 20.10 or higher | 4GB+ | 10GB+ |

```bash
# This method pulls pre-built images from Docker Hub for a faster start
git clone https://github.com/Tencent/AI-Infra-Guard.git
cd AI-Infra-Guard
# For Docker Compose V2+, replace 'docker-compose' with 'docker compose'
docker-compose -f docker-compose.images.yml up -d
```

Once the service is running, you can access the A.I.G web interface at:
`http://localhost:8088`
<br>

<details>
<summary><strong>📦 More installation options</strong></summary>

### Other Installation Methods

**Method 2: One-Click Install Script （Recommended）**
```bash
# This method will automatically install Docker and launch A.I.G with one command  
curl https://raw.githubusercontent.com/Tencent/AI-Infra-Guard/refs/heads/main/docker.sh | bash
```

**Method 3: Build and run from source**
```bash
git clone https://github.com/Tencent/AI-Infra-Guard.git
cd AI-Infra-Guard
# This method builds a Docker image from local source code and starts the service
# (For Docker Compose V2+, replace 'docker-compose' with 'docker compose')
docker-compose up -d
```

Note: The AI-Infra-Guard project is positioned as an AI red teaming platform for internal use by enterprises or individuals. It currently lacks an authentication mechanism and should not be deployed on public networks.

For more information, see: [https://tencent.github.io/AI-Infra-Guard/?menu=getting-started](https://tencent.github.io/AI-Infra-Guard/?menu=getting-started)

</details>

### Try the Online Pro Version
Experience the Pro version with advanced features and improved performance. The Pro version requires an invitation code and is prioritized for contributors who have submitted issues, pull requests, or discussions, or actively help grow the community. Visit: [https://aigsec.ai/](https://aigsec.ai/).
<br>
<br>

## ✨ Features

| Feature | More Info |
|:--------|:------------|
| **AI&nbsp;Infra&nbsp;Scan** | Precisely identifies ​over​ 30 AI framework components ​and covers​ over 400 known CVE vulnerabilities, ​including​ Ollama, ComfyUI, vLLM, etc. |
| **AI&nbsp;Tool&nbsp;Protocol&nbsp;Scan** | Powered by an AI Agent, Detects 14 major categories of security risks in MCP Servers and Agent Skills, Supports scanning of source code and remote URLs. |
| **Jailbreak&nbsp;Evaluation** | Assesses prompt security risks with curated datasets and multiple attack methods, Cross-model comparison. |

<details>
<summary><strong>💎 Additional Benefits</strong></summary>

- 🖥️ **Modern Web Interface**: User-friendly UI with one-click scanning and real-time progress tracking
- 🔌 **Complete API**: Full interface documentation and Swagger specifications for easy integration
- 🌐 **Multi-Language**: Chinese and English interfaces with localized documentation
- 🐳 **Cross-Platform**: Linux, macOS, and Windows support with Docker-based deployment
- 🆓 **Free & Open Source**: Completely free under the MIT license
</details>

<br />


## 🖼️ Showcase

### A.I.G Main Interface
![AIG Main Page](img/aig.gif)

### Plugin Management
![Plugin Management](img/plugin-gif.gif)

<br />


## 📖 User Guide

Visit our online documentation: [https://tencent.github.io/AI-Infra-Guard/](https://tencent.github.io/AI-Infra-Guard/)

For more detailed FAQs and troubleshooting guides, visit our [documentation](https://tencent.github.io/AI-Infra-Guard/?menu=faq).
<br />
<br>

## 🔧 API Documentation

A.I.G provides a comprehensive set of task creation APIs that support AI infra scan, MCP Server Scan, and Jailbreak Evaluation capabilities.

After the project is running, visit `http://localhost:8088/docs/index.html` to view the complete API documentation.

For detailed API usage instructions, parameter descriptions, and complete example code, please refer to the [Complete API Documentation](./api.md).
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
<br />

## 🙏 Acknowledgements

### 🎓 Academic Collaborations

We extend our sincere appreciation to our academic partners for their exceptional research contributions and technical support.

#### <img src="img/北大未来网络重点实验室2.png" height="30" align="middle"/>
<table>
  <tr>
    <td align="center" width="90">
      <a href="#">
        <img src="https://avatars.githubusercontent.com/u/0?v=4" width="70px;" style="border-radius: 50%;" alt=""/>
      </a>
      <br />
      <a href="#">
        <sub><b>Prof.&nbsp;hui&nbsp;Li</b></sub>
      </a>
    </td>
    <td align="center" width="90">
      <a href="https://github.com/TheBinKing">
        <img src="https://avatars.githubusercontent.com/TheBinKing" width="70px;" style="border-radius: 50%;" alt=""/>
      </a>
      <br />
      <a href="mailto:1546697086@qq.com">
        <sub><b>Bin&nbsp;Wang</b></sub>
      </a>
    </td>
    <td align="center" width="90">
      <a href="https://github.com/KPGhat">
        <img src="https://avatars.githubusercontent.com/KPGhat" width="70px;" style="border-radius: 50%;" alt=""/>
      </a>
      <br />
      <a href="mailto:kpghat@gmail.com">
        <sub><b>Zexin&nbsp;Liu</b></sub>
      </a>
    </td>
    <td align="center" width="90">
      <a href="https://github.com/GioldDiorld">
        <img src="https://avatars.githubusercontent.com/GioldDiorld" width="70px;" style="border-radius: 50%;" alt=""/>
      </a>
      <br />
      <a href="mailto:g.diorld@gmail.com">
        <sub><b>Hao&nbsp;Yu</b></sub>
      </a>
    </td>
    <td align="center" width="90">
      <a href="https://github.com/Jarvisni">
        <img src="https://avatars.githubusercontent.com/Jarvisni" width="70px;" style="border-radius: 50%;" alt=""/>
      </a>
      <br />
      <a href="mailto:719001405@qq.com">
        <sub><b>Ao&nbsp;Yang</b></sub>
      </a>
    </td>
    <td align="center" width="90">
      <a href="https://github.com/Zhengxi7">
        <img src="https://avatars.githubusercontent.com/Zhengxi7" width="70px;" style="border-radius: 50%;" alt=""/>
      </a>
      <br />
      <a href="mailto:linzhengxi7@126.com">
        <sub><b>Zhengxi&nbsp;Lin</b></sub>
      </a>
    </td>
  </tr>
</table>

#### <img src="img/复旦大学2.png" height="30" align="middle" style="vertical-align: middle;"/>

<table>
  <tr>
    <td align="center" width="120">
      <a href="https://yangzhemin.github.io/">
        <img src="https://avatars.githubusercontent.com/yangzhemin" width="70px;" style="border-radius: 50%;" alt=""/>
      </a>
      <br />
      <a href="mailto:yangzhemin@fudan.edu.cn">
        <sub><b>Prof.&nbsp;Zhemin&nbsp;Yang</b></sub>
      </a>
    </td>
    <td align="center" width="100">
      <a href="https://github.com/kangwei-zhong">
        <img src="https://avatars.githubusercontent.com/kangwei-zhong" width="70px;" style="border-radius: 50%;" alt=""/>
      </a>
      <br />
      <a href="mailto:kwzhong23@m.fudan.edu.cn">
        <sub><b>Kangwei&nbsp;Zhong</b></sub>
      </a>
    </td>
    <td align="center" width="90">
      <a href="https://github.com/MoonBirdLin">
        <img src="https://avatars.githubusercontent.com/MoonBirdLin" width="70px;" style="border-radius: 50%;" alt=""/>
      </a>
      <br />
      <a href="mailto:linjp23@m.fudan.edu.cn">
        <sub><b>Jiapeng&nbsp;Lin</b></sub>
      </a>
    </td>
    <td align="center" width="90">
      <a href="https://vanilla-tiramisu.github.io/">
        <img src="https://avatars.githubusercontent.com/vanilla-tiramisu" width="70px;" style="border-radius: 50%;" alt=""/>
      </a>
      <br />
      <a href="mailto:csheng25@m.fudan.edu.cn">
        <sub><b>Cheng&nbsp;Sheng</b></sub>
      </a>
    </td>
  </tr>
</table>
<br>

### 👥 Gratitude to Contributing Developers
Thanks to all the developers who have contributed to the A.I.G project, Your contributions have been instrumental in making A.I.G a more robust and reliable AI Red Team platform.
<br />
<table border="0" cellspacing="0" cellpadding="0">
  <tr>
    <td width="33%"><img src="img/keen_lab_logo.svg" alt="Keen Lab" height="85%"></td>
    <td width="33%"><img src="img/wechat_security.png" alt="WeChat Security" height="85%"></td>
    <td width="33%"><img src="img/fit_sec_logo.png" alt="Fit Security" height="85%"></td>
  </tr>
</table>
<a href="https://github.com/Tencent/AI-Infra-Guard/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=Tencent/AI-Infra-Guard" />
</a>
<br>
<br>

### 🤝 Appreciation for Our Users

We are deeply grateful to the following teams and organizations for their trust, and valuable feedback in using A.I.G.

<br>
<div align="center">
<img src="img/tencent.png" alt="Tencent" height="30px">
<img src="img/deepseek.png" alt="DeepSeek" height="38px">
<img src="img/antintl.svg" alt="Antintl" height="45px">
</div>

<br>
<br>

## 💬 Join the Community

### 🌐 Online Discussions
- **GitHub Discussions**: [Join our community discussions](https://github.com/Tencent/AI-Infra-Guard/discussions)
- **Issues & Bug Reports**: [Report issues or suggest features](https://github.com/Tencent/AI-Infra-Guard/issues)

### 📱 Discussion Community
<table>
  <thead>
  <tr>
    <th>WeChat Group</th>
    <th>Discord <a href="https://discord.gg/U9dnPnyadZ">[link]</a></th>
  </tr>
  </thead>
  <tbody>
  <tr>
    <td><img src="img/wechatgroup.png" alt="WeChat Group" width="200"></td>
    <td><img src="img/discord.png" alt="discord" width="200"></td>
  </tr>
  </tbody>
</table>

### 📧 Contact Us
For collaboration inquiries or feedback, please contact us at: [zhuque@tencent.com](mailto:zhuque@tencent.com)

### 🔗 Recommended Security Tools
If you are interested in code security, check out [A.S.E (AICGSecEval)](https://github.com/Tencent/AICGSecEval), the industry's first repository-level AI-generated code security evaluation framework open-sourced by the Tencent Wukong Code Security Team.




<br>
<br>

## 📖 Citation

If you use A.I.G in your research, please cite:

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

[1] Naen Xu, Jinghuai Zhang, Ping He et al. **"FraudShield: Knowledge Graph Empowered Defense for LLMs against Fraud Attacks."** arXiv preprint arXiv:2601.22485v1 (2026). [[pdf]](http://arxiv.org/abs/2601.22485v1)  
[2] Ruiqi Li, Zhiqiang Wang, Yunhao Yao et al. **"MCP-ITP: An Automated Framework for Implicit Tool Poisoning in MCP."** arXiv preprint arXiv:2601.07395v1 (2026). [[pdf]](http://arxiv.org/abs/2601.07395v1)  
[3] Jingxiao Yang, Ping He, Tianyu Du et al. **"HogVul: Black-box Adversarial Code Generation Framework Against LM-based Vulnerability Detectors."** arXiv preprint arXiv:2601.05587v1 (2026). [[pdf]](http://arxiv.org/abs/2601.05587v1)  
[4] Yunyi Zhang, Shibo Cui, Baojun Liu et al. **"Beyond Jailbreak: Unveiling Risks in LLM Applications Arising from Blurred Capability Boundaries."** arXiv preprint arXiv:2511.17874v2 (2025). [[pdf]](http://arxiv.org/abs/2511.17874v2)  
[5] Teofil Bodea, Masanori Misono, Julian Pritzi et al. **"Trusted AI Agents in the Cloud."** arXiv preprint arXiv:2512.05951v1 (2025). [[pdf]](http://arxiv.org/abs/2512.05951v1)  
[6] Christian Coleman. **"Behavioral Detection Methods for Automated MCP Server Vulnerability Assessment."** [[pdf]](https://digitalcommons.odu.edu/cgi/viewcontent.cgi?article=1138&context=covacci-undergraduateresearch)  
[7] Bin Wang, Zexin Liu, Hao Yu et al. **"MCPGuard : Automatically Detecting Vulnerabilities in MCP Servers."** arXiv preprint arXiv:22510.23673v1 (2025). [[pdf]](http://arxiv.org/abs/2510.23673v1)  
[8] Weibo Zhao, Jiahao Liu, Bonan Ruan et al. **"When MCP Servers Attack: Taxonomy, Feasibility, and Mitigation."** arXiv preprint arXiv:2509.24272v1 (2025). [[pdf]](http://arxiv.org/abs/2509.24272v1)  
[9] Ping He, Changjiang Li, et al. **"Automatic Red Teaming LLM-based Agents with Model Context Protocol Tools."** arXiv preprint arXiv:2509.21011 (2025). [[pdf]](https://arxiv.org/abs/2509.21011)  
[10] Yixuan Yang, Daoyuan Wu, Yufan Chen. **"MCPSecBench: A Systematic Security Benchmark and Playground for Testing Model Context Protocols."** arXiv preprint arXiv:2508.13220 (2025). [[pdf]](https://arxiv.org/abs/2508.13220)  
[11] Zexin Wang, Jingjing Li, et al. **"A Survey on AgentOps: Categorization, Challenges, and Future Directions."** arXiv preprint arXiv:2508.02121 (2025). [[pdf]](https://arxiv.org/abs/2508.02121)  
[12] Yongjian Guo, Puzhuo Liu, et al. **"Systematic Analysis of MCP Security."** arXiv preprint arXiv:2508.12538 (2025). [[pdf]](https://arxiv.org/abs/2508.12538)  

📧 If you have used A.I.G in your research or product, or if we have inadvertently missed your publication, we would love to hear from you! [Contact us here](#-join-the-community).
<br>
<br>

## 📄 License

This project is licensed under the **MIT License**. See the [License.txt](./License.txt) file for details.

<div>

[![Star History Chart](https://api.star-history.com/svg?repos=Tencent/AI-Infra-Guard&type=Date)](https://star-history.com/#Tencent/AI-Infra-Guard&Date)
