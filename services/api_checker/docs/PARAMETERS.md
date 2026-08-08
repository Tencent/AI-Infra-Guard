# aig_api_checker — 输入/输出参数规格文档

本文档详细说明 `aig_api_checker` 各功能模块的**输入参数**与**输出参数**，并列出不同算法作为可选选项。

---

## 目录

1. [功能总览与算法选择](#1-功能总览与算法选择)
2. [算法 A：随机数指纹（统计方法）](#2-算法-a随机数指纹统计方法)
3. [算法 B：加密级 Signature 验证（Anthropic 专用）](#3-算法-b加密级-signature-验证anthropic-专用)
4. [算法 C：中转站黑盒审计（OpenAI 兼容通用）](#4-算法-c中转站黑盒审计openai-兼容通用)
5. [算法 D：PAMELA 单 token 分布指纹](#5-算法-dpamela-单-token-分布指纹)
6. [算法 E：Ventor QTest 供应商一致性检验](#6-算法-eventor-qtest-供应商一致性检验)
7. [公共数据结构](#7-公共数据结构)
8. [CLI 命令与参数映射](#8-cli-命令与参数映射)

---

## 1. 功能总览与算法选择

本工具提供 **五种可选算法**，按目标场景选择：

| 算法 | 适用 API | 检测维度 | 可伪造性 | 耗时 | 费用 |
|------|----------|----------|----------|------|------|
| **A. 随机数指纹** | OpenAI / Anthropic / Responses 均可 | 统计分布指纹 | 理论上可（但需海量样本对标） | 高（200+次采样） | 中 |
| **B. 加密级 Signature** | 仅 Anthropic（Claude extended thinking） | AEAD 加密签名 + 10 项辅助 | **不可伪造**（加密级） | 低（1-2 分钟） | 低 |
| **C. 黑盒审计 7 探针** | OpenAI 兼容中转站 | 篡改行为黑盒探测 | 探针可被识别规避（已做随机化） | 低（1 分钟内） | 低 |
| **D. PAMELA 分布指纹** | OpenAI 兼容 API | 多任务、多语言单 token 分布 JSD | 需要系统性复现参考分布 | 高（默认约 400 次请求） | 中 |
| **E. Ventor QTest** | 支持 `logprobs` 的 OpenAI 兼容 API | token 概率、信息熵与 Z-test | 取决于供应商的 logprobs 完整性 | 中 | 中 |

### 选择建议

```
目标 API 是 Anthropic Claude？
├─ 是 → 优先用 [B] 加密级 Signature（不可伪造，最可靠）
│        可选叠加 [A] 随机数指纹做交叉验证
└─ 否（OpenAI 兼容中转站）
         → 用 [C] 黑盒审计 7 探针
         可选叠加 [A] 或 [D] 做模型识别
         需要比较多家供应商且端点支持 logprobs 时使用 [E]
```

---

## 2. 算法 A：随机数指纹（统计方法）

### 原理

让 AI 模型"从 1 到 355 随机选一个数字"，不同模型因训练数据、架构、RLHF 差异产生不同的分布偏差。收集大量样本后形成统计学上可区分的指纹。

### 2.1 采样：`collect_samples()`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|:----:|--------|------|
| `api_type` | `str` | 是 | — | `"openai"` / `"openai-responses"` / `"anthropic"` |
| `base_url` | `str` | 是 | — | API 基础 URL，如 `https://api.example.com/v1` |
| `api_key` | `str` | 是 | — | API 密钥（内存使用，不写盘） |
| `model` | `str` | 是 | — | 模型名称，如 `gpt-4o` |
| `iterations` | `int` | 否 | `200` | 采样次数，范围 50–500 |
| `concurrency` | `int` | 否 | `5` | 并发数，范围 1–50 |
| `no_think` | `bool` | 否 | `False` | 对兼容模型关闭推理过程，失败时自动回退 |
| `on_progress` | `callable` | 否 | `None` | 进度回调 `fn(completed, total, success, error)` |
| `cancel_event` | `threading.Event` | 否 | `None` | HTTP 客户端断连时协作取消未开始的请求 |

**输出**：`tuple[list[int], int]`

| 返回字段 | 类型 | 说明 |
|----------|------|------|
| `results` | `list[int]` | 有效数字列表（每个 1–355） |
| `error_count` | `int` | 失败请求数 |

### 2.2 指纹计算：`calculate_distribution()` + `calculate_stats()`

| 参数 | 类型 | 说明 |
|------|------|------|
| `numbers` | `list[int]` | 采样结果列表 |

**`calculate_distribution()` 输出**：`list[float]`

| 字段 | 类型 | 说明 |
|------|------|------|
| `[0..354]` | `float` | 每个数字（1–355）的出现频率，和为 1.0 |

**`calculate_stats()` 输出**：`dict`

| 字段 | 类型 | 说明 |
|------|------|------|
| `mean` | `float` | 均值 |
| `median` | `int` | 中位数 |
| `stdDev` | `float` | 标准差 |
| `min` | `int` | 最小值 |
| `max` | `int` | 最大值 |
| `unique` | `int` | 唯一值数量 |
| `mode` | `int` | 众数（出现最多的数字） |
| `modeCount` | `int` | 众数出现次数 |

### 2.3 相似度计算：`calculate_similarity()`

| 参数 | 类型 | 说明 |
|------|------|------|
| `dist1` | `list[float]` | 分布 1（长度 355） |
| `dist2` | `list[float]` | 分布 2（长度 355） |
| `stats1` | `dict` | 统计特征 1（可选，用于众数匹配） |
| `stats2` | `dict` | 统计特征 2（可选） |

**输出**：`dict`

| 字段 | 类型 | 范围 | 说明 |
|------|------|------|------|
| `cosineSimilarity` | `float` | 0–1 | 余弦相似度 |
| `jsDivergence` | `float` | ≥0 | JS 散度（越小越相似） |
| `modeScore` | `float` | 0–1 | 众数匹配分（完全匹配=1，否则 `max(0, 1−Δ/50)`） |
| `distribScore` | `float` | 0–1 | 分布匹配分 = `cosine × exp(−js)` |
| `overallScore` | `float` | 0–1 | **综合匹配度** = `0.5 × modeScore + 0.5 × distribScore` |

### 2.4 基准匹配：`match_baselines()`

| 参数 | 类型 | 说明 |
|------|------|------|
| `test_results` | `list[int]` | 待测样本列表 |
| `baselines` | `list[dict]` | 已标定的基准列表（见 [基准数据结构](#基准数据结构)） |

**输出**：`list[dict]`（按 `score` 降序）

| 字段 | 类型 | 说明 |
|------|------|------|
| `name` | `str` | 基准名称 |
| `model` | `str` | 基准模型名 |
| `score` | `float` | Dirichlet-multinomial 模型识别后验概率（0–1） |
| `modeMatch` | `bool` | 众数是否匹配 |
| `similarity` | `dict` | 详细相似度（见 2.3） |
| `testStats` | `dict` | 测试样本统计特征 |

### 2.5 基准存储：`build_baseline()` / `save_baselines()` / `load_baselines()`

**`build_baseline()` 输入**：

| 参数 | 类型 | 说明 |
|------|------|------|
| `name` | `str` | 基准名称 |
| `model` | `str` | 模型名 |
| `api_type` | `str` | API 类型 |
| `results` | `list[int]` | 采样数据 |

**输出（基准数据结构）**：

| 字段 | 类型 | 说明 |
|------|------|------|
| `name` | `str` | 基准名称 |
| `model` | `str` | 模型名 |
| `apiType` | `str` | API 类型 |
| `timestamp` | `str` | UTC ISO 时间戳 |
| `iterations` | `int` | 样本数 |
| `noThink` | `bool` | 标定时是否关闭模型推理 |
| `distribution` | `list[float]` | 概率分布（长度 355） |
| `stats` | `dict` | 统计特征（见 2.2） |
| `counts` | `list[int]` | 1–355 的计数向量（长度 355） |
| `rawData` | `list[int]` | 原始采样数据 |

---

## 3. 算法 B：加密级 Signature 验证（Anthropic 专用）

### 原理

Claude 的 extended thinking API 返回的 `signature` 是 base64 protobuf 封装，内部包裹 AEAD 加密的推理内容，模型名绑定在认证头中。只有 Anthropic 服务端能产生和解封，中转站无法伪造。

### 3.1 Harvest 采集：`harvest_signature()`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|:----:|--------|------|
| `base_url` | `str` | 是 | — | Anthropic API base URL |
| `api_key` | `str` | 是 | — | Anthropic API Key |
| `model` | `str` | 是 | — | 模型名，如 `claude-sonnet-4-5-20250514` |
| `user_message` | `str` | 否 | `"What is 17 * 23? Think carefully."` | 发给模型的 prompt |
| `max_tokens` | `int` | 否 | `8000` | 最大输出 token |

**输出**：`dict`

| 字段 | 类型 | 说明 |
|------|------|------|
| `thinking_text` | `str` | 可见的 thinking 文本（display:omitted 时通常为空） |
| `signature` | `str \| None` | base64 编码的 signature（核心验证对象） |
| `answer` | `str` | 模型可见回复 |
| `thinking_tokens` | `int` | 隐藏思考 token 数 |
| `stop_reason` | `str \| None` | 停止原因 |
| `model` | `str` | 返回的模型名 |
| `usage` | `dict` | token 使用统计 |
| `raw` | `dict` | 原始 API 响应 |
| `error` | `str` | 仅失败时存在 |

### 3.2 Signature 解码：`parse_signature()`

| 参数 | 类型 | 说明 |
|------|------|------|
| `signature_b64` | `str` | base64 编码的 signature 字符串 |

**输出**：`SignatureInfo`

| 字段 | 类型 | 说明 |
|------|------|------|
| `total_bytes` | `int` | 解码后总字节数 |
| `envelope_version` | `int \| None` | protobuf envelope 版本 |
| `model` | `str \| None` | 绑定的模型名（header #6，AEAD 认证不可篡改） |
| `block_type` | `str \| None` | 块类型（应为 `"thinking"`） |
| `key_id` | `bytes \| None` | 密钥 ID（header #5，20 bytes） |
| `nonce_lengths` | `list[int]` | nonce 长度列表（#2, #3, #4） |
| `ciphertext_len` | `int` | 密文字节数（#5） |
| `ciphertext_entropy` | `float` | 密文 Shannon 熵（应 ≈7.96 bits/byte） |
| `parse_error` | `str \| None` | 解析错误信息 |

### 3.3 Replay 回放：`replay_signature()`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|:----:|--------|------|
| `base_url` | `str` | 是 | — | API base URL |
| `api_key` | `str` | 是 | — | API Key |
| `model` | `str` | 是 | — | 模型名 |
| `signature` | `str` | 是 | — | harvest 获取的 signature |
| `preceding_user` | `str` | 否 | `"What is 17 * 23?"` | 回放请求的前置 user 消息 |
| `max_tokens` | `int` | 否 | `4096` | 最大输出 token |

**输出**：`dict`

| 字段 | 类型 | 说明 |
|------|------|------|
| `recovered` | `str` | 解封的隐藏推理内容 |
| `model` | `str` | 返回的模型名 |
| `usage` | `dict` | token 使用统计 |
| `stop_reason` | `str \| None` | 停止原因 |
| `status` | `int` | HTTP 状态码 |
| `error` | `str` | 仅失败时存在 |

### 3.4 综合检测：`run_all_checks()`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|:----:|--------|------|
| `base_url` | `str` | 是 | — | Anthropic API base URL |
| `api_key` | `str` | 是 | — | API Key |
| `model` | `str` | 是 | — | 模型名 |
| `skip_fingerprint` | `bool` | 否 | `False` | 跳过随机数指纹检测（省时） |
| `skip_latency` | `bool` | 否 | `False` | 跳过延迟检测 |
| `on_progress` | `callable` | 否 | `None` | 每个上游请求完成后的回调 `fn(completed, total, success, error)` |

**输出**：`dict`

| 字段 | 类型 | 说明 |
|------|------|------|
| `verdict` | `str` | 判定结果：`"native"` / `"suspect"` / `"proxy"` |
| `score` | `float` | 对外签名评分 80–100，最多扣 20 分 |
| `checks` | `list[CheckResult]` | 11 项检测详细结果 |
| `summary` | `str` | 一句话摘要 |

**判定逻辑**（阈值使用限幅前的原始加权分，避免扣分上限改变风险结论）：

| 条件 | verdict | 含义 |
|------|---------|------|
| 加密级检测全通过且原始分 ≥ 85 | `native` | 原生透传 |
| 加密级检测全通过且原始分 ≥ 60 | `suspect` | 存在可疑 |
| 加密级检测失败且原始分 < 50 | `proxy` | 疑似替身 |
| 其他 | `suspect` | 存在可疑 |

### 3.5 11 项检测项明细

| # | 检测函数 | 输入 | weight | critical | 输出 `CheckResult` |
|---|----------|------|--------|:--------:|------|
| 1 | `check_thinking_signature` | base_url, api_key, model | 2.0 | ✅ | signature 是否有效获取 |
| 2 | `check_signature_structure` | harvest_data | 1.5 | | protobuf 结构 + 模型名 + 熵值 |
| 3 | `check_replay_unseal` | base_url, api_key, model, harvest_data | 2.0 | | signature 能否解封隐藏推理 |
| 4 | `check_model_consistency` | model, harvest_data | 1.0 | | 返回 model 与请求一致 |
| 5 | `check_response_headers` | base_url, api_key, model | 1.0 | | Anthropic/AWS/Bedrock 响应头 |
| 6 | `check_thinking_tokens` | harvest_data | 1.0 | | thinking_tokens > 0 |
| 7 | `check_stop_reason` | harvest_data | 1.0 | | stop_reason 合理 |
| 8 | `check_random_fingerprint` | base_url, api_key, model | 0.5 | | 1-355 随机数分布 |
| 9 | `check_system_prompt` | base_url, api_key, model | 1.0 | | 替身关键词探测 |
| 10 | `check_token_counts` | harvest_data | 1.0 | | token 计数合理性 |
| 11 | `check_latency` | base_url, api_key, model | 1.0 | | 延迟特征 |

### 3.6 CheckResult 数据结构

| 字段 | 类型 | 说明 |
|------|------|------|
| `name` | `str` | 检测项名称 |
| `passed` | `bool` | 是否通过（True=像原生） |
| `detail` | `str` | 详细说明 |
| `weight` | `float` | 权重（影响评分） |
| `critical` | `bool` | 是否为加密级关键检测 |

---

## 4. 算法 C：中转站黑盒审计（OpenAI 兼容通用）

### 原理

通过 7 个黑盒探针检测 OpenAI 兼容中转站的隐蔽篡改行为。纯标准库实现，API key 全程脱敏。

### 4.1 主审计函数：`run_relay_audit()`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|:----:|--------|------|
| `base_url` | `str` | 是 | — | 中转 base URL，如 `https://relay.example.com/v1` |
| `api_key` | `str` | 是 | — | 中转 API Key |
| `model` | `str` | 是 | — | 购买/声明使用的模型名 |
| `profile` | `str` | 否 | `"full"` | 探针集合：`quick` / `standard` / `full` |
| `cancel_event` | `threading.Event` | 否 | `None` | 客户端断连时取消未开始的探针 |
| `on_progress` | `callable` | 否 | `None` | 每个探针完成后的回调 `fn(completed, total)` |
| `on_request_progress` | `callable` | 否 | `None` | 每个实际 HTTP 请求完成后的回调 `fn(completed, total, success, error)` |

默认执行完整 7 探针。

**输出**：`dict`

| 字段 | 类型 | 说明 |
|------|------|------|
| `score` | `int` | 风险评分 0–100（越高越危险） |
| `verdict` | `str` | `"LOW"` / `"MEDIUM"` / `"HIGH"` |
| `findings` | `list[Finding]` | 风险发现列表 |
| `probe_results` | `list[ProbeResult]` | 探针原始结果 |
| `summary` | `str` | 一句话摘要 |

**Verdict 判定**：

| score 区间 | verdict | 含义 |
|-----------|---------|------|
| 0–29 | `LOW` | 未发现明显风险 |
| 30–69 | `MEDIUM` | 存在可疑 |
| 70–100 | `HIGH` | 高风险 |

### 4.2 7 个探针明细

| # | 探针函数 | 检测什么 | 触发条件 | 加分 | 严重度 |
|---|----------|----------|----------|------|--------|
| 1 | `probe_models` | GET /v1/models 列表一致性 | 端点失败/目标模型缺失 | +20 | MEDIUM |
| 2 | `probe_liveness` | 精确 echo 可用性 | 不可用/echo 被改写 | +50/+5 | HIGH/LOW |
| 3 | `probe_identity` | 模型身份弱信号 | 自报家族不匹配/model 字段不一致 | +15 | LOW |
| 4 | `probe_token_delta` | 隐藏 prompt 注入 | prompt_tokens delta > 200 | +25 | MEDIUM |
| 5 | `probe_echo_rewrite` | 输出/命令改写 | pip 命令被篡改 | +35 | HIGH |
| 6 | `probe_stream_integrity` | SSE 流式完整性 | 无 [DONE]/JSON 损坏/流内 model 不一致 | +20/+30 | MEDIUM |
| 7 | `probe_context_canary` | 上下文截断 | 尾部 canary 丢失 | +20 | MEDIUM |

### 4.3 Finding 数据结构

| 字段 | 类型 | 说明 |
|------|------|------|
| `probe` | `str` | 探针名 |
| `severity` | `str` | `"LOW"` / `"MEDIUM"` / `"HIGH"` |
| `score` | `int` | 风险分增量 |
| `title` | `str` | 发现标题 |
| `evidence` | `str` | 证据详情（JSON） |
| `recommendation` | `str` | 修复建议 |

### 4.4 ProbeResult 数据结构

| 字段 | 类型 | 说明 |
|------|------|------|
| `name` | `str` | 探针名 |
| `ok` | `bool` | 是否通过 |
| `latency_ms` | `int \| None` | 响应延迟（毫秒） |
| `data` | `dict` | 探针采集的详细数据 |
| `error` | `str \| None` | 错误信息 |

### 4.5 模型家族别名表

身份探针使用以下家族归一化表，避免同源误判（如 `openai` ↔ `gpt` 不误判）：

| 家族 | 别名关键词 |
|------|-----------|
| `openai` | openai, gpt, o1, o3, o4, chatgpt |
| `anthropic` | anthropic, claude, sonnet, opus, haiku |
| `google` | google, gemini, palm, bard |
| `qwen` | qwen, tongyi |
| `deepseek` | deepseek |
| `zhipu` | glm, zhipu, chatglm |
| `moonshot` | kimi, moonshot |
| `bytedance` | doubao |
| `baidu` | ernie, wenxin |
| `meta` | llama |
| `mistral` | mistral, mixtral |

---

## 5. 算法 D：PAMELA 单 token 分布指纹

PAMELA 使用 10 个 study-A 任务和多语言单 token 回答构建候选分布，并与随服务打包的参考指纹库逐单元计算 Jensen–Shannon 散度。平均 JSD 越小，指纹越接近。

### 5.1 主匹配函数：`match_model()`

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|:----:|--------|------|
| `base_url` | `str` | 是 | — | OpenAI 兼容 API base URL |
| `api_key` | `str` | 是 | — | API Key |
| `model` | `str` | 是 | — | 待测模型 ID |
| `reps` | `int` | 否 | `10` | 每个任务/语言单元的采样次数 |
| `langs` | `list[str]` | 否 | 全部 | 语言子集：`en` / `ru` / `zh` / `ar` |
| `tasks` | `list[str]` | 否 | 全部 | study-A 任务子集 |
| `concurrency` | `int` | 否 | `8` | 请求并发数 |
| `reference_path` | `str` | 否 | 内置参考库 | PAMELA 参考分布 JSON 路径 |
| `on_progress` | `callable` | 否 | `None` | 进度回调 |

主要输出为 `ranked`，元素格式是 `(模型名, mean_jsd, 有效单元数)` 并按 `mean_jsd` 升序排列；候选分布会写入运行时数据目录下的 `pamela/results/candidate-distributions.json`。

---

## 6. 算法 E：Ventor QTest 供应商一致性检验

Ventor QTest 使用端点返回的 `logprobs` 计算 token 概率和信息熵，通过 Z-test 量化待测供应商与参考分布的一致性。该算法通过独立配置执行，结果写入配置指定的结果和汇总目录。

| 子命令 | 说明 |
|--------|------|
| `qtest run [--config PATH]` | 按 JSON/YAML 配置运行测试并生成报告 |
| `qtest openrouter-providers [--model ID]` | 查询 OpenRouter 上指定模型的 provider |
| `qtest openrouter-run [参数...]` | 自动发现 provider、运行测试并生成汇总 |

完整配置字段见 `ventor_qtest/config/default.yaml`；CLI 的 `--help` 是参数的权威来源。

---

## 7. 公共数据结构

### 7.1 基准数据结构（`baselines.json`）

```json
[
  {
    "name": "GPT-4o-官方",
    "model": "gpt-4o",
    "apiType": "openai",
    "timestamp": "2026-07-21T10:00:00+00:00",
    "iterations": 200,
    "distribution": [0.005, 0.010, ...],
    "stats": {
      "mean": 178.5,
      "median": 180,
      "stdDev": 102.3,
      "min": 1,
      "max": 355,
      "unique": 150,
      "mode": 42,
      "modeCount": 8
    },
    "rawData": [42, 178, 5, ...]
  }
]
```

### 7.2 替身检测关键词

算法 B 中用于检测伪装替身的关键词：

```python
SUSPECT_KEYWORDS = [
    "kiro", "amazon q", "bedrock", "nova", "titan",
    "guardrails", "aws", "firewall",
]
```

---

## 8. CLI 命令与参数映射

### 8.1 交互式菜单

```bash
python main.py
```

| 选项 | 对应算法 | 调用函数 |
|------|----------|----------|
| `[1]` 标定官方模型基准 | A | `calibrate_flow()` |
| `[2]` 测试第三方 API | A | `test_flow()` |
| `[3]` 中转站加密级检测 | B | `detect_flow()` |
| `[4]` 中转站黑盒审计 | C | `audit_flow()` |
| `[5]` 查看已保存基准 | — | `list_flow()` |
| `[6]` PAMELA 分布指纹匹配 | D | `pamela_flow()` |
| `[7]` Ventor 供应商一致性检验 | E | `qtest_flow()` |

### 8.2 命令行直接调用

| 命令 | 算法 | 所需输入 |
|------|------|----------|
| `python main.py calibrate` | A | api_type, base_url, api_key, model, name, iterations, concurrency |
| `python main.py test` | A | api_type, base_url, api_key, model, iterations, concurrency |
| `python main.py detect` | B | base_url, api_key, model, skip_fingerprint?, skip_latency? |
| `python main.py audit` | C | base_url, api_key, model |
| `python main.py pamela` | D | base_url, api_key, model, reps, langs, concurrency, reference_path? |
| `python main.py qtest ...` | E | 子命令及其配置/参数 |
| `python main.py list` | — | 无 |

在 AIG 根目录中，上述命令也可写成 `ai-infra-guard api-checker <子命令>`（本地
Makefile 构建的二进制名为 `server`）。

### 8.3 通用输入参数汇总

以下参数在所有算法中通用：

| 参数 | 说明 | 示例 |
|------|------|------|
| `base_url` | API 基础 URL | `https://api.example.com/v1` |
| `api_key` | API 密钥（内存使用，不写盘） | `<api-key>` |
| `model` | 模型名称 | `claude-sonnet-4-5-20250514` |

### 8.4 通用输出汇总

| 算法 | 主输出字段 | 评分范围 | 判定字段 |
|------|-----------|----------|----------|
| A | `bayes.best_posterior` / `matches[].score` | 0.0–1.0 | 贝叶斯后验概率，按概率排序 |
| B | `score` (0–100) | 0–100 | `verdict`: native/suspect/proxy |
| C | `score` (0–100) | 0–100 | `verdict`: LOW/MEDIUM/HIGH |
| D | `ranked[].mean_jsd` | ≥0 | 数值越小越接近 |
| E | 报告中的 Z 值和汇总指标 | 实验相关 | 供应商一致性排序 |

> **注意**：算法 B 的 score 越高越**安全**（通过率），算法 C 的 score 越高越**危险**（风险分）。两者方向相反。

HTTP SSE 接口 `POST /api/v1/relay/check/stream` 对外返回一个顶层 `score`：
统一为 0–100 且越高越可信。黑盒审计使用 `100 - risk_score`；Signature 使用算法
B 的通过分且最多扣 20 分；full 模式的指纹在支持声明时使用后验百分制，在已知替身或未知异常时
使用 `min((1 - posterior) × 100, 50)`。多个已完成组件取最低分，任一组件执行失败时综合分
为 0。这样综合分与 `overall_verdict`、摘要保持一致，不会在高置信识别出替身时仍
显示 100 分。最高后验候选与声明模型一致且后验不低于 85% 时，G² 绝对分布漂移
作为同模型采样漂移处理，不单独判定模型被替换。
full 模式还在 `detail.fingerprint` 中分别返回身份后验概率、第二候选、曲线重合度和
最大局部偏差。身份后验概率表示在一定置信度下，系统认为的模型识别概率；曲线重合度
由前端展示用的 48 桶聚合分布计算。
Signature 的风险判定仍按未截断的原始证据分计算，不因 80 分下限而改判；证据完整
时签名组件分范围为 80–100，判定风险时为 80。除 Signature 外，任一已确认风险组件
的分数最高为 50，缺失或格式不完整的组件按 0 分处理；已确认风险优先于其他组件未完成。模型生成的总结必须与最终 verdict 语义一致，
否则回退为服务端确定性总结。
同时在 `detail.test_info` 返回黑盒生成探针的平均延迟 `latency_ms`、生成速度
`tokens_per_second`、累计输入 `input_tokens`、累计输出 `output_tokens` 和缓存读取
`cache_read_tokens`。缓存读取兼容 DeepSeek 的 `prompt_cache_hit_tokens`、
Anthropic 的 `cache_read_input_tokens`、Chat Completions 的
`prompt_tokens_details.cached_tokens` 以及 Responses 的
`input_tokens_details.cached_tokens`；上游未提供的指标为 `null`。
`detail.findings[]` 只返回适用且证据充分的探针及专项风险条件；`severity` 使用英文
二值状态 `Passed`/`Failed`。证据不足、未执行或不适用的检查直接省略，不引入第三
种状态。无论状态如何，`title` 都只返回中性的检查项名称，不包含“通过”“失败”
“异常”等结论，列表图标可直接由 `severity` 决定。统一候选清单共定义 20 项；
7 个黑盒探针对应最多 18 项审计检查（7 项基础状态 + 11 项专项条件），Claude
Signature 和 full 模式模型指纹分别作为 `probe: "signature"`、
`probe: "fingerprint"` 追加。因此四种组合的最大返回数量依次为：quick 非 Claude
18 项、quick + Claude 19 项、full 非 Claude 19 项、full + Claude 20 项；实际数量
取决于本轮获得的有效证据。
黑盒审计对单个上游 HTTP 请求设置 60 秒总时限，并对整轮 quick 审计设置
180 秒总时限，避免上游持续发送少量数据时绕过普通 socket 读超时。
