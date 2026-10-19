# aig-infra-scan

**[English](./USAGE.md)** | 中文

扫描域名、IP 或 URL，匹配 AI 基础设施指纹和对应漏洞。安装包里已经带了规则，普通扫描不用写 `--fps` 和 `--vul`。

```bash
pip install aig-infra-scan
```

需要 Python ≥ 3.9。请安装与本机操作系统和 CPU 匹配的 wheel。

## 示例

```bash
# 扫一个地址
aig-infra-scan -t https://example.com

# 多个目标
aig-infra-scan -t https://example.com -t 10.0.0.1

# 目标写在文件里，一行一个
aig-infra-scan -f targets.txt --json -o result.json

# 使用英文漏洞说明
aig-infra-scan -t https://example.com --lang en

# 只列出内置漏洞库
aig-infra-scan --list-vul
```

`--lang en` 会改读英文漏洞目录。指纹规则不变。

## 参数

| 参数 | 默认 | 含义 |
| --- | --- | --- |
| `-t, --target` | — | 目标 URL、域名或 IP。多个目标就重复写这个参数。 |
| `-f, --file` | — | 目标列表文件，一行一个。 |
| `-o, --output` | — | 把报告写到这个路径。 |
| `--json` | 关闭 | 以 JSON 输出扫描结果，可以和 `-o` 一起用。 |
| `--lang` | `zh` | `zh` 或 `en`。`en` 使用英文漏洞库。 |
| `--timeout` | `5` | HTTP 超时，单位秒。 |
| `--limit` | `200` | 每秒最多请求数。 |
| `--proxy-url` | — | 代理地址。 |
| `--header` | — | 额外请求头，格式 `key:value`。多个请求头就重复写。 |
| `--fps` | 包内指纹库 | 指纹规则文件或目录。 |
| `--vul` | 包内漏洞库 | 漏洞目录。加上 `--lang en` 时，实际读取的是 `<该路径>_en`。 |
| `--list-vul` | 关闭 | 打印指纹和漏洞目录后退出。 |
| `--check-vul` | 关闭 | 校验漏洞模板后退出。 |
| `--localscan` | 关闭 | 扫描本机。 |
| `--ai` | 关闭 | 打开内置 AI 分析。 |
| `--hunyuan-token` | — | `--ai` 调用混元时使用的令牌。 |
| `--deepseek-token` | — | `--ai` 调用 DeepSeek 时使用的令牌。 |

`aig-infra-scan --help` 会打印同一组参数。

## 输出

不加 `--json` 时，终端打印文本报告。加上 `--json` 后，同一份结果变成 JSON，打印在终端，或写入 `-o` 指定的文件。
