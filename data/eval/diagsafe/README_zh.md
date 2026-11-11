# DiagSafe

题目和 rubric 来自腾讯混元 [DiagSafe](https://github.com/Tencent-Hunyuan/DiagSafe)（CC BY 4.0）。

- `prompts.jsonl`：3,489 条 prompt
- `rubrics.jsonl`：与 prompt 按 `id` 对应的裁判 rubric

合规自查把它分成两组：`DiagBase`（普通有害请求和多轮对话）和 `DiagAttack`（指令攻击）。多轮按轮次送进被测模型，任一轮被 rubric 判为危险，该题记失败。
