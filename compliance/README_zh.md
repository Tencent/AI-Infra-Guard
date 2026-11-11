# aig-compliance

**[English](./README.md)** | 中文

运行后打开本机页面，填写被测模型、裁判模型和攻击模型，检测结束后在页面里看到一份可打印的 HTML 报告。

## 安装

```bash
pip install aig-compliance
```

安装时会一并安装 `aig-model-scan` 和 `aig-infra-scan`。需要 Python ≥ 3.12。本工具不调用 MCP、Skill、Agent 扫描。

## 使用

```bash
aig-compliance
```

终端会打开 `http://127.0.0.1:8765`。页面上填写任务名称，以及三组模型参数：被测模型、裁判模型、攻击模型。每组都是模型名称、接口地址和 API Key，输入框里有例子，也可以先点「测试连接」。模型名称可以写成 `openai:gpt-4o-mini`。

被测模型和基础设施至少填一项。填写被测模型时要从评测集里至少勾选一个，可以多选，也可以一键勾选「AI合规类」或「AI安全类」。题目来自 `data/eval`。页面只显示题集名称和题数。被测模型回答所选题目，填写后还要填裁判模型。裁判按该评测集的检查项和豁免判断回答是否危险，落在豁免里不算命中；读不懂裁判结果时，仍按回复里有没有拒绝来计。DiagSafe 放在 `data/eval/diagsafe/`，分成 DiagBase 和 DiagAttack，多轮逐轮判定。勾选对抗测试后，攻击模型把应拒答题改写成另一种问法，再交给被测模型；绕过次数不计入应拒答率。不勾选时不用填攻击模型。基础设施地址是多行文本，一行一个，可以一次填多个。只填基础设施时不用填模型。

也可以先导出环境变量，页面会把它们填进对应输入框：`TARGET_MODEL_NAME`、`TARGET_BASE_URL`、`TARGET_API_KEY`，裁判模型用 `JUDGE_` 前缀，攻击模型用 `ATTACKER_` 前缀。

确认后开始检测。结束后页面直接显示报告，不再嵌一套网页。检测数据记在当前目录的 `aig-compliance.db`，里面没有 API Key。同时仍会写入可打印的 `aig-compliance-report.html`。点一条历史记录会在页面上再次打开那次结果。终端最后四行是任务名称、总评、报告路径和「报告已生成」。

模型请求直接发到所填接口，页面上可以选并发。基础设施地址通过 `aig-infra-scan` 的 `scan` 扫描。

## 许可证

Apache License 2.0。再分发时需注明 "Based on Tencent Zhuque Lab AI-Infra-Guard"，并链接到 https://github.com/Tencent/AI-Infra-Guard。详见 [NOTICE](./NOTICE)。
