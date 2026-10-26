# aig-infra-scan

**[English](./README.md)** | 中文

命令用法：[中文](./USAGE_zh.md) · [English](./USAGE.md)

[Tencent AI-Infra-Guard](https://github.com/Tencent/AI-Infra-Guard) 的 AI 基础设施指纹与漏洞扫描。命令仍是原来的 Go 扫描器，连同指纹和漏洞规则一起打成 PyPI 包。

## 安装

```bash
pip install aig-infra-scan
```

需要 Python ≥ 3.9。每个 wheel 只对应一种操作系统和 CPU，请安装与本机匹配的版本。

## 快速使用

```bash
aig-infra-scan -t https://example.com
aig-infra-scan -t 10.0.0.1 --json -o result.json
aig-infra-scan --list-vul
```

`--lang en` 会改用英文漏洞库。其余参数与 `ai-infra-guard scan --help` 相同。

## 发布

在仓库根目录构建当前系统（或全部支持的系统）的 wheel，再上传：

```bash
python scripts/publish_pypi.py build infra
python scripts/publish_pypi.py build infra --target all
python scripts/publish_pypi.py upload infra
```

上传走 `twine`。设置 `TWINE_USERNAME=__token__` 和 `TWINE_PASSWORD`（PyPI token）。

## 许可证

Apache License 2.0。再分发时需注明 "Based on Tencent Zhuque Lab AI-Infra-Guard"，并链接到 https://github.com/Tencent/AI-Infra-Guard。详见 [NOTICE](./NOTICE)。
