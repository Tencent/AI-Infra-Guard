
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