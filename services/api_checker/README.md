# aig_api_checker

AI 模型指纹识别 + 中转站检测工具

## 功能

### 1. 随机数指纹识别（统计方法）
通过让 AI 模型"随机选数字 1-355"，收集大量样本的分布指纹来区分不同模型。

### 2. 中转站加密级检测
用 Claude thinking signature（Anthropic 服务端 AEAD 加密签名，中转站不可伪造）+ 10 项辅助检测，1 分钟识别中转站是真原生透传，还是用 Kiro / Amazon Q / Bedrock 等替身伪装。

## 原理

### Thinking Signature（加密级验证）

Claude 的 extended thinking API 返回的 `signature` 是 base64 编码的 **protobuf 封装**，内部包裹着模型私有推理的 **AEAD 加密副本**，并与模型名绑定：

```
base64
 └─ protobuf envelope
     #2  inner message
         #1  header (authenticated)
             #6 = model name      ← 绑定模型名（AEAD 认证，不可篡改）
             #8 = "thinking"     ← block type
         #2 = 12 bytes            ← nonce/IV
         #3 = 12 bytes            ← second nonce
         #4 = 48 bytes            ← wrapped data-key / auth tag
         #5 = N bytes             ← CIPHERTEXT (加密的推理，熵≈7.96 bits/byte)
```

**关键点：**
- 只有 Anthropic 服务端持有加密密钥，能产生和解封 signature
- 模型名绑定在 AEAD 认证头中，不可篡改
- 中转站无法伪造（没有 Anthropic 的密钥）
- 替身模型（Kiro/Q/Bedrock 等）不会产生这种 protobuf 封装的签名

### 检测流程

1. **Harvest**：向待测 API 发送开启 extended thinking 的请求，获取 signature
2. **验证签名结构**：解析 protobuf，检查模型名绑定、密文熵值
3. **Replay**：用 signature 回放，验证能否解封隐藏推理
4. **10 项辅助检测**：响应头指纹、thinking_tokens、stop_reason 等

## 检测能力

### A. 随机数指纹（统计方法）
让 AI 模型"随机选数字 1-355"，通过分布指纹区分不同模型。

### D. PAMELA 单 token 分布指纹（集成自 pamela-publish-py）
用 PAMELA 研究的 10 个 study-A 探针任务（随机数字/字母/单词/颜色/动物/城市/抛硬币）
在 en/ru/zh/ar 多语言下采样单 token 回答分布，与已发布参考指纹库
（内置 `pamela/reference/distributions.json`，167 个模型）逐单元计算
Jensen–Shannon 散度，排名最前即指纹最接近的模型。候选分布输出到
`pamela/results/candidate-distributions.json`，格式与 pamela-publish-py 完全兼容。

### E. Ventor QTest 供应商一致性量化检验

内置 [Ventor QTest](https://github.com/kexinoh/ventor_qtest)，通过参考模型的
`logprobs` 逐位置计算信息熵、信息方差与 Z 分数，用于比较同一模型在不同 API
供应商上的概率分布一致性。该模块使用独立配置与结果目录，不改变已有 A/B/C/D
算法、基准文件或 HTTP SSE 接口。

### B. 中转站加密级检测（11 项）

| # | 检测项 | 类型 | 说明 |
|---|--------|------|------|
| 1 | Thinking Signature | 加密级 | AEAD 加密签名，绑定模型名，中转站不可伪造 |
| 2 | 签名结构验证 | 辅助 | protobuf 格式 + 模型名绑定 + 密文熵值 ≈8 |
| 3 | 回放解封验证 | 加密级 | replay signature 能还原隐藏推理 |
| 4 | 模型名一致性 | 辅助 | 返回 model 与请求 model 一致 |
| 5 | 响应头指纹 | 辅助 | 检查 Anthropic 特有响应头 / AWS/Bedrock 头 |
| 6 | thinking_tokens | 辅助 | 扩展思考返回 thinking token 计数 |
| 7 | stop_reason | 辅助 | 合理的停止原因 |
| 8 | 随机数指纹 | 辅助 | 1-355 随机数分布指纹 |
| 9 | system prompt 探测 | 辅助 | 不同替身模型的响应差异 |
| 10 | token 计数校验 | 辅助 | input/output token 比例合理性 |
| 11 | 延迟特征 | 辅助 | 原生 API vs 中转的延迟差异模式 |

### C. 中转站黑盒审计（7 探针，源自朱雀实验室 A.I.G）

适用于 OpenAI 兼容中转站（`/v1/models`、`/v1/chat/completions`）：

| # | 探针 | 检测什么 | 关键风险信号 |
|---|------|----------|--------------|
| 1 | models | GET /v1/models 列表一致性 | 目标模型缺失；模型数异常 |
| 2 | liveness | 基础聊天可用性（精确 echo） | 返回被改写（中）；不可用（高） |
| 3 | identity | 模型身份弱信号 | 自报家族与所购模型不符 |
| 4 | token_delta | 隐藏 prompt / token 注入 | 短 prompt 的 prompt_tokens 异常偏高 |
| 5 | echo_rewrite | 输出改写 / 工具命令篡改 | pip install 被改成换源/curl/eval |
| 6 | stream_integrity | SSE 流式完整性 | 无 [DONE]、JSON 损坏、流内 model 不一致 |
| 7 | context_canary | 上下文截断 | 尾部 canary 丢失 |

- 纯 Python 标准库，无第三方依赖
- API key 全程脱敏，不回显
- 随机化探针 prompt，避免被识别规避
- 执行 7 个黑盒探针

## 安装

```bash
cd services/api_checker
pip install -r requirements.txt
```

在 AIG 仓库根目录可用以下命令创建隔离虚拟环境：

```bash
python3 -m venv services/api_checker/.venv
services/api_checker/.venv/bin/pip install -r services/api_checker/requirements.txt
```

## 使用

### 交互式菜单

```bash
python main.py
```

AIG 统一命令入口为 `ai-infra-guard api-checker ...`（别名
`relay-checker`）；它会自动查找本目录并调用配置的 Python 解释器。

### 命令行直接调用

```bash
python main.py calibrate   # 标定官方模型基准（随机数指纹）
python main.py test        # 测试第三方 API（随机数指纹匹配）
python main.py detect      # 中转站加密级检测（thinking signature）
python main.py audit       # 中转站黑盒审计（朱雀 7 探针）
python main.py pamela      # PAMELA 单token分布指纹匹配（JSD）
python main.py qtest run   # Ventor QTest（使用内置默认配置）
python main.py qtest run --config path/to/config.yaml
python main.py qtest openrouter-providers --model moonshotai/kimi-k2.5
python main.py list        # 查看已保存基准
```

### 中转站检测示例

```bash
python main.py detect
# 输入中转站的 Base URL / API Key / 模型名
# 1-2 分钟后输出 11 项检测结果
```

### HTTP SSE 接口

```bash
python server.py
# 独立运行时打开 http://127.0.0.1:8000/ui
# 通过 AIG 统一接入时打开 http://127.0.0.1:8088/api-checker/
curl http://127.0.0.1:8088/api/v1/relay/models
curl -N -X POST http://127.0.0.1:8088/api/v1/relay/check/stream \
  -H "Content-Type: application/json" \
  -d '{"algorithm":"quick","base_url":"https://relay.example.com/v1","api_key":"sk-...","model":"gpt-4o","language":"en"}'
```

可通过 `/api/v1/relay/models` 查询 quick/full 检测支持的 28 个参考指纹模型。检测入口为
`/api/v1/relay/check/stream`，详见
[`docs/API.md`](docs/API.md)。
`language` 可选 `zh` 或 `en`，省略时默认中文；该参数控制结果中的 `summary`、
`detail.findings[].title` 和 `detail.findings[].severity`。字段名以及
`overall_verdict` 的机器可读枚举保持不变。

## 隐私

- **本地执行**：检测逻辑在本地运行；被测模型 API 仍可能按调用量收费
- **API key 不留存**：HTTP 检测的 Key 仅在任务内存中使用；QTest
  `--dump-config` 只写环境变量占位符，导出文件权限为 `0600`
- **代码开源**：完整源码可审计

HTTP 服务默认只允许公网 HTTPS 目标。可信内网或本机测试可显式设置
`AIG_API_CHECKER_ALLOW_HTTP=1`、`AIG_API_CHECKER_ALLOW_PRIVATE_TARGETS=1`。

## 项目结构

```
services/api_checker/
├── main.py              # CLI 入口
├── server.py            # HTTP SSE 服务入口
├── Dockerfile           # 独立 Python sidecar
├── algorithms/
│   ├── common.py        # 公共 API 客户端、统计与基准存储
│   ├── fingerprint.py   # 随机数指纹
│   ├── bayes_score.py   # 贝叶斯评分
│   ├── signature.py     # Thinking Signature 检测
│   ├── relay_audit.py   # 中转站黑盒审计
│   └── pamela.py        # PAMELA 单 token 分布指纹
├── ventor_qtest/         # 隔离内置的 Ventor QTest
│   ├── check.py          # logprobs、信息熵与 Z 检验
│   ├── summary.py        # 结果聚合与排名
│   ├── config/           # 独立默认配置
│   └── runner/           # CLI、编排及 OpenRouter 支持
├── docs/
│   ├── API.md           # HTTP API 文档
│   └── PARAMETERS.md    # 参数与数据结构说明
├── assets/charts/       # 分析图表
├── pamela/
│   ├── config/          # PAMELA 探针配置
│   └── reference/       # 随服务提供的参考指纹库
├── tests/               # 不访问真实模型的离线测试
├── requirements.txt
└── baselines.json       # 内置只读种子基准
```

可写基准和 PAMELA 结果默认进入 `runtime/`，可通过
`AIG_API_CHECKER_DATA_DIR` 指向持久化目录。

## 免责声明

测试结果仅供参考。由于大模型本身存在随机性及网络波动，本工具的测试结果不能作为任何商业纠纷、退款索赔的绝对法律/事实依据。

## 致谢

- thinking signature 分析基于 [open-open-reasoning](https://git.woa.com/xiangfanwu/mono-repo) 项目的逆向研究
- 随机数指纹算法基于 [hlwy-ai-checker](https://github.com/hanlinwenyuan/hlwy-ai-checker)
- 中转站黑盒审计探针源自腾讯朱雀实验室 [A.I.G (AI-Infra-Guard)](https://github.com/Tencent/AI-Infra-Guard)（Apache-2.0）
