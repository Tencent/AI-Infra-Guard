# aig-compliance

**English** | [中文](./README_zh.md)

Run the command and a local page opens. Fill in the target, judge, and attacker models. When the check finishes, the page shows a printable HTML report.

## Install

```bash
pip install aig-compliance
```

This also installs `aig-model-scan` and `aig-infra-scan`. Python ≥ 3.12 is required. This tool does not call the MCP, Skill, or Agent scanners.

## Use

```bash
aig-compliance
```

The command opens `http://127.0.0.1:8765`. The page asks for a name and three model endpoints: target, judge, and attacker. Each endpoint is a model name, base URL, and API key, with an example in the field and a button to test the connection. A model name may look like `openai:gpt-4o-mini`.

Fill in the target model, the infrastructure addresses, or both. When a target model is filled in, choose one or more evaluation sets from `data/eval`, or use the shortcuts for the compliance group and the security group. The page lists each set's name and size, not the questions. The target model answers the selected sets. The judge then applies that set's checks and exemptions; a reply inside an exemption is not a hit. If the judge result cannot be read, a refusal phrase in the reply is used instead. DiagSafe lives in `data/eval/diagsafe/` as DiagBase and DiagAttack, and multi-turn prompts are judged one turn at a time. If adversarial testing is checked, the attacker model rephrases refuse-questions and those replies are scored separately; bypasses do not change the refuse rate. Leave that box unchecked to skip the attacker model. Infrastructure addresses go in a multiline field, one address per line. Leaving the target model empty scans infrastructure only.

Environment variables prefill the same fields: `TARGET_MODEL_NAME`, `TARGET_BASE_URL`, `TARGET_API_KEY`, and the same three names with `JUDGE_` or `ATTACKER_`.

After confirmation, the page draws the report itself. The run is stored in `aig-compliance.db` in the current directory, without API keys, and a printable `aig-compliance-report.html` is still written. Opening a history row shows that run again on the page. The terminal then prints the name, the verdict, the report path, and a single completion line.

Model calls go directly to the endpoint you enter, with a concurrency setting on the page. An infrastructure address is scanned through `aig-infra-scan`'s `scan`.

## License

Apache License 2.0. Redistribution must state "Based on Tencent Zhuque Lab AI-Infra-Guard" and link to https://github.com/Tencent/AI-Infra-Guard. See [NOTICE](./NOTICE).
