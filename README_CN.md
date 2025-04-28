# 🛡️ AI基础设施安全评估系统

AI Infra Guard(AI Infrastructure Guard) 是一个**高效**、**轻量**、**易用**的AI基础设施安全评估工具，专为发现和检测AI系统潜在安全风险而设计。支持传统安全漏洞扫描、MCP Server静态扫描和Web界面操作三种方式，全方位保障AI基础设施安全。

## 🚀 快速预览

**WEBUI**  
<img src="img/web-zh.png" height="800"><br>

**命令行**
![AI 安全扫描器演示](img/img.jpg)  
![](img/img2.png)  

## 🚀 项目亮点

* **全面的安全能力**
    * 支持传统安全漏洞扫描
    * 支持MCP Server检测
    * 提供Web界面可视化操作

* **高效扫描**
    * 支持 28 种 AI 框架指纹识别
    * 涵盖 200+ 安全漏洞数据库

* **易于使用**
    * 开箱即用，无复杂配置
    * 指纹、漏洞YAML规则定义
    * 灵活的匹配语法

* **轻量级**
    * 核心组件简洁高效
    * 二进制体积小，资源占用低
    * 跨平台支持

## 📋 功能说明

AI Infra Guard提供三大核心功能：

1. **安全漏洞扫描 (scan)** - 检测AI系统中的传统安全漏洞
2. **MCP Server静态扫描 (mcp)** - 检测MCP代码的安全性
3. **Web服务器界面 (webserver)** - 提供可视化操作界面

## 📦 安装与使用

### 安装

下载地址: [https://github.com/Tencent/AI-Infra-Guard/releases](https://github.com/Tencent/AI-Infra-Guard/releases)

### 命令行结构

AI Infra Guard采用子命令结构，提供三个主要子命令：

```
ai-infra-guard [子命令] [选项]
```

可用的子命令：
- `scan`: 执行安全漏洞扫描
- `mcp`: 执行模型污染保护检测
- `webserver`: 启动Web界面服务器

### 使用方法

#### WEBUI 可视化操作

```
./ai-infra-guard webserver [--ws-addr 127.0.0.1:8088]
```

#### 安全漏洞扫描 (scan)

**本地一键检测**
```
./ai-infra-guard scan --localscan
```

**单个目标**
```
./ai-infra-guard scan --target [IP/域名] 
```

**多个目标**
```
./ai-infra-guard scan --target [IP/域名] --target [IP/域名]
```

**从文件读取**
```
./ai-infra-guard scan --file target.txt
```

**完整参数**

```
./ai-infra-guard scan --help
```

输出：
```
执行原始的扫描功能，扫描指定目标的安全漏洞。

Usage:
  ai-infra-guard scan [flags]

Flags:
      --ai                      启用AI分析
      --check-vul               验证漏洞模板
      --deepseek-token string   DeepSeek API令牌
  -f, --file string             包含目标URL的文件路径
      --fps string              指纹模板文件或目录 (default "data/fingerprints")
      --header stringArray      HTTP请求头，可以指定多个，例如: --header "key:value" --header "key:value"
  -h, --help                    help for scan
      --hunyuan-token string    混元API令牌
      --lang string             响应语言 zh/en (default "zh")
      --limit int               每秒最大请求数 (default 200)
      --list-vul                列出漏洞模板
      --localscan               一键本地扫描
  -o, --output string           输出文件路径
      --proxy-url string        代理服务器URL
  -t, --target stringArray      目标URL，可以指定多个目标，例如: --target xx.com --target aa.com
      --timeout int             请求超时时间(秒) (default 5)
      --vul string              漏洞数据库目录 (default "data/vuln")
```

#### MCP Server扫描

MCP扫描功能用于检测MCP Server中存在的安全问题，基于AI Agent自动检测代码问题。

**基本使用**
```
./ai-infra-guard mcp --code [源代码路径] --model [模型名称] --token [API令牌]
```

**指定输出格式**
```
./ai-infra-guard mcp --code [源代码路径] --model [模型名称] --token [API令牌] --csv results.csv --json results.json
```

**完整参数**

```
./ai-infra-guard mcp --help
```

输出：
```

Usage:
  ai-infra-guard mcp [flags]

Flags:
      --base-url string   API基础URL
      --code string       源代码路径
      --csv string        输出 CSV 文件路径
  -h, --help              help for mcp
      --json string       输出 JSON 文件路径
      --log string        日志保存路径
      --model string      AI模型名称
      --plugins string    插件列表，用英文逗号分隔
      --token string      API令牌
```

## 📊 AI组件覆盖情况

| 组件名称           | 漏洞数量 |
|--------------------|------|
|         anythingllm | 8    |
|           langchain | 33   |
|          Chuanhugpt | 0    |
|          clickhouse | 22   |
|           comfy_mtb | 1    |
| ComfyUI-Prompt-Preview | 1    |
| ComfyUI-Custom-Scripts | 1    |
|             comfyui | 1    |
|                dify | 11   |
|      fastchat-webui | 0    |
|            fastchat | 1    |
|               feast | 0    |
|              gradio | 42   |
|          jupyterlab | 6    |
|    jupyter-notebook | 1    |
|      jupyter-server | 13   |
|            kubeflow | 4    |
|              kubepi | 5    |
|        llamafactory | 1    |
|           llmstudio | 0    |
|              ollama | 7    |
|          open-webui | 8    |
|           pyload-ng | 18   |
|           qanything | 2    |
|             ragflow | 2    |
|                 ray | 4    |
|         tensorboard | 0    |
|                vllm | 4    |
|          xinference | 0    |
| triton-inference-server | 7    |

## 🔍 指纹匹配规则

AI Infra Guard 基于WEB指纹识别组件，指纹规则在[data/fingerprints](./data/fingerprints)目录中，漏洞匹配规则在[data/vuln](./data/vuln)目录中。

### 示例：Gradio 指纹规则

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

### 🛠️ 指纹匹配语法

#### 匹配位置
- 标题（title）
- 正文（body）
- 请求头（header）
- 图标哈希（icon）

#### 逻辑运算符
- `=` 模糊匹配
- `==` 全等
- `!=` 不等
- `~=` 正则匹配
- `&&` 与
- `||` 或
- `()` 括号分组

## 🤝 贡献

我们非常欢迎社区贡献！欢迎提交 [PR](https://github.com/Tencent/AI-Infra-Guard/pulls) 和 [Issue](https://github.com/Tencent/AI-Infra-Guard/issues)。

## Star History

[![Star History Chart](https://api.star-history.com/svg?repos=Tencent/AI-Infra-Guard&type=Date)](https://star-history.com/#Tencent/AI-Infra-Guard&Date)

## 📄 许可证

"AI Infra Guard" is licensed under the MIT License except for the third-party components. Visited [License.txt](./License.txt)

---

💡 **提示**：持续关注更新，保护您的AI基础设施安全！