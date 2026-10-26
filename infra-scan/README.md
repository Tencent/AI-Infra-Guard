# aig-infra-scan

English | **[中文](./README_zh.md)**

Command usage: [USAGE.md](./USAGE.md) · [中文](./USAGE_zh.md)

AI infrastructure fingerprint and vulnerability scanner from [Tencent AI-Infra-Guard](https://github.com/Tencent/AI-Infra-Guard). The command is the existing Go scanner, packaged so it can be installed from PyPI together with the fingerprint and advisory rules.

## Install

```bash
pip install aig-infra-scan
```

Requires Python ≥ 3.9. The wheel matches one operating system and CPU, so install the build published for your machine.

## Quick start

```bash
aig-infra-scan -t https://example.com
aig-infra-scan -t 10.0.0.1 --json -o result.json
aig-infra-scan --list-vul
```

`--lang en` reads the English advisory set. Other flags are the same as `ai-infra-guard scan --help`.

## Publish

From the repository root, build a wheel for this machine (or every supported machine) and upload it:

```bash
python scripts/publish_pypi.py build infra
python scripts/publish_pypi.py build infra --target all
python scripts/publish_pypi.py upload infra
```

Uploading uses `twine`. Set `TWINE_USERNAME=__token__` and `TWINE_PASSWORD` to a PyPI token.

## License

Apache License 2.0. Redistribution must state "Based on Tencent Zhuque Lab AI-Infra-Guard" and link to https://github.com/Tencent/AI-Infra-Guard. See [NOTICE](./NOTICE).
