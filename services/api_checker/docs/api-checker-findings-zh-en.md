# API Checker Findings 中英对照表

共定义 20 项可返回的检查：7 项基础探针状态、11 项专项风险条件，以及 2 项按模式
追加的检查。

统一 findings 清单共 20 项。完整执行黑盒审计时，其中 18 项审计检查会出现在
`detail.findings` 中，另外 2 项根据模型和模式追加：

- 专项风险触发：`severity: Failed`。
- 专项风险未触发：`severity: Passed`，仍返回该检查。
- 同一检查在 Passed 和 Failed 状态下使用完全相同的中性 `title`。
- `title` 只描述检查项是什么；列表中的通过/不通过图标应由 `severity` 决定。
- full + Claude 还会追加 Claude Signature 和模型指纹，共 20 条 finding。
- full + 非 Claude 会追加模型指纹，共 19 条 finding。
- quick + Claude 会追加 Claude Signature，共 19 条 finding。
- quick + 非 Claude 仅返回 18 条黑盒审计 finding。

| Check | Probe | 类型 | 中文标题 | English Title |
|---|---|---|---|---|
| `models_base` | `models` | 基础探针 | 模型列表检查 | Model list check |
| `liveness_base` | `liveness` | 基础探针 | 中转服务连通性检查 | Relay liveness check |
| `identity_base` | `identity` | 基础探针 | 模型身份检查 | Model identity check |
| `token_delta_base` | `token_delta` | 基础探针 | 提示词 Token 差异检查 | Prompt token delta check |
| `echo_rewrite_base` | `echo_rewrite` | 基础探针 | 回显与工具命令检查 | Echo and tool command check |
| `stream_integrity_base` | `stream_integrity` | 基础探针 | 流式响应完整性检查 | Stream integrity check |
| `context_canary_base` | `context_canary` | 基础探针 | 上下文完整性检查 | Context integrity check |
| `models_endpoint` | `models` | 专项风险 | 模型列表接口调用检查 | Model list endpoint check |
| `requested_model_presence` | `models` | 专项风险 | 请求模型存在性检查 | Requested model presence check |
| `liveness_truncation` | `liveness` | 专项风险 | 连通性响应截断检查 | Liveness truncation check |
| `relay_liveness_risk` | `liveness` | 专项风险 | 中转服务连通性专项检查 | Relay liveness risk check |
| `identity_family` | `identity` | 专项风险 | 模型身份系列匹配检查 | Model identity family match check |
| `token_delta_risk` | `token_delta` | 专项风险 | 提示词 Token 数量偏差检查 | Prompt token delta risk check |
| `echo_truncation` | `echo_rewrite` | 专项风险 | 回显响应截断检查 | Echo truncation check |
| `echo_rewrite_risk` | `echo_rewrite` | 专项风险 | 回显与工具命令改写检查 | Echo and tool command rewrite check |
| `stream_anomaly` | `stream_integrity` | 专项风险 | 流式响应异常检查 | Stream anomaly check |
| `stream_model_match` | `stream_integrity` | 专项风险 | 流式响应模型字段匹配检查 | Stream model field match check |
| `context_truncation` | `context_canary` | 专项风险 | 上下文截断检查 | Context truncation check |
| `signature` | `signature` | Claude 模型追加 | Claude 签名验证 | Claude signature verification |
| `fingerprint` | `fingerprint` | full 模式追加 | 模型指纹检查 | Model fingerprint check |
