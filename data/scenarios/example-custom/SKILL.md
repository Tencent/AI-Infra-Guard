---
name: example-custom
description: 示例场景，默认不启用。
---

# 示例自定义场景

复制 `data/scenarios/example-custom` 为新目录。

1. 在 `scenario.yaml` 里写清场景名称、必填项和允许的工具。
2. 在本文件写检测步骤和结论标准。结论最后一行使用「结论: 通过」「结论: 不通过」或「结论: 证据不足」。
3. 工具名只能是 `http_fetch`、`fingerprint_scan`、`probe_model`、`list_uploads`、`read_text_file`、`read_agent_config`。
4. 确认能跑通后，把 `enabled` 改成 true，或删掉 `enabled`。未审核的场景不要打开脚本执行。
