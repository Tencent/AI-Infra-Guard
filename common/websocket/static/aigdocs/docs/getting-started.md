# 2. 快速开始

本章节将指导您如何快速部署和使用A.I.G。

## a) 一键安装

### 一键Docker部署

为了方便用户快速体验，我们提供了Docker镜像。

```bash
# 拉取最新的Docker镜像
docker pull tencent/ai-infra-guard

# 运行WebUI模式
docker run -it -p 8080:8080 tencent/ai-infra-guard webserver
```

然后，您可以通过浏览器访问 `http://localhost:8080` 来使用A.I.G的Web界面。

### 从源码编译

如果您希望自行编译，请确保您已安装Go语言环境（1.18或更高版本）。

```bash
# 克隆项目仓库
git clone `https://github.com/Tencent/AI-Infra-Guard.git`
cd AI-Infra-Guard

# 编译
go build .

# 运行
./ai-infra-guard webserver
```

## b) 集成到安全流水线

A.I.G提供了命令行接口（CLI），可以方便地集成到您的CI/CD或其他自动化安全流水线中。

```bash
# 扫描单个URL
./ai-infra-guard scan --url `http://testphp.vulnweb.com`

# 扫描多个URL
./ai-infra-guard scan -f urls.txt

# 将扫描结果保存为JSON格式
./ai-infra-guard scan --url `http://testphp.vulnweb.com`  --json result.json
```

## c) 基础配置

A.I.G的核心配置文件位于 `config.yaml`。您可以根据需要修改以下配置：

*   **代理设置**: 配置HTTP/HTTPS代理，用于网络请求。
*   **并发设置**: 调整扫描任务的并发数，以平衡扫描速度和资源消耗。
*   **超时设置**: 设置网络请求的超时时间。
*   **自定义规则路径**: 指定自定义指纹和漏洞规则的存放目录。

## d) 核心功能使用

A.I.G的核心功能是`scan`（扫描）和`mcp`（MCP分析）。

### `scan`功能

`scan`命令用于扫描Web资产，发现已知的组件漏洞。

```bash
# 扫描一个示例漏洞网站
./ai-infra-guard scan --url `http://testphp.vulnweb.com`
```

### `mcp`功能

`mcp`命令用于分析MCP服务器的安全性。

```bash
# 扫描一个远程MCP服务器
./ai-infra-guard mcp --url `https://example-mcp-server.com`
```