# AIG API Checker HTTP API

- **版本**：v1.7.0
- **AIG 统一地址**：`http://127.0.0.1:8088`
- **Web 检测页**：`/api-checker/`
- **Swagger 文档**：AIG 统一接入为 `/api-checker/docs`；独立运行 Checker 为 `/docs`
- **API 前缀**：`/api/v1`

> 测试结果仅供参考，不能作为商业纠纷、退款索赔的绝对法律或事实依据。

## 1. 接口总览

| 方法 | 路径 | 说明 |
|---|---|---|
| `GET` | `/api/v1/relay/models` | 获取完整指纹识别使用的参考模型列表 |
| `POST` | `/api/v1/relay/check/stream` | API 中转检查 SSE 流式接口 |

### 检测算法

| `algorithm` | 检测内容 |
|---|---|
| `quick` | C：黑盒审计 7 探针；Claude 模型自动叠加 B |
| `full` | A：随机数指纹 + C：黑盒审计 7 探针；Claude 模型自动叠加 B |

模型 ID 包含 `sonnet`、`opus`、`haiku` 或 `fable` 时，不区分大小写地识别为
Claude，并自动叠加算法 B（Thinking Signature 验证）。

---

## 2. 获取可检测模型

### `GET /api/v1/relay/models`

模型列表从 `baselines.json` 动态读取。Claude 和 GPT 系列排在前面，同系列中
版本号较新的型号优先。

### 请求示例

```bash
curl http://127.0.0.1:8088/api/v1/relay/models
```

### 响应结构

```json
{
  "status": 0,
  "message": "success",
  "data": {
    "models": [
      {
        "id": "anthropic/claude-sonnet-5",
        "name": "Claude-Sonnet-5",
        "provider": "anthropic"
      },
      {
        "id": "openai/gpt-5.6-sol",
        "name": "GPT-5.6-Sol",
        "provider": "openai_compatible"
      }
    ],
    "total": 28,
    "algorithms": {
      "full": "仅支持 models 列表中的模型，可进行指纹识别和黑盒审计",
      "quick": "仅支持 models 列表中的模型，进行快速检测"
    }
  }
}
```

| 字段 | 类型 | 说明 |
|---|---|---|
| `status` | integer | `0` 表示成功 |
| `message` | string | 响应消息 |
| `data.models` | array | quick/full 支持的模型 |
| `data.models[].id` | string | 请求检测接口时使用的模型 ID |
| `data.models[].name` | string | 模型显示名称 |
| `data.models[].provider` | string | `anthropic` 或 `openai_compatible` |
| `data.total` | integer | 模型总数 |
| `data.algorithms` | object | 两种检测模式的能力说明 |

---

## 3. API 中转检查 SSE

### `POST /api/v1/relay/check/stream`

检测通常需要 30 秒到数分钟。接口返回 `text/event-stream`，客户端需要保持连接，
逐条处理 SSE 事件，直到收到 `done` 或 `error`。

### 请求体

| 字段 | 类型 | 必填 | 默认值 | 说明 |
|---|---|:---:|---|---|
| `algorithm` | string | 是 | — | `quick` 或 `full` |
| `base_url` | string | 是 | — | 待测 API 基础 URL，带不带 `/v1` 均可；默认要求公网 HTTPS |
| `api_key` | string | 是 | — | 待测 API 密钥，仅在内存使用 |
| `model` | string | 是 | — | 待测模型 ID，仅支持 models 接口返回的列表 |
| `iterations` | integer | 否 | `200` | 仅 `full` 使用，范围为 50–500 |
| `no_think` | boolean | 否 | `true` | 仅 `full` 使用，是否关闭模型思考 |

### 请求示例

快速检测：

```bash
curl -N -X POST http://127.0.0.1:8088/api/v1/relay/check/stream \
  -H "Content-Type: application/json" \
  -d '{
    "algorithm": "quick",
    "base_url": "https://relay.example.com/v1",
    "api_key": "sk-...",
    "model": "gpt-5.6-sol"
  }'
```

完整检测：

```bash
curl -N -X POST http://127.0.0.1:8088/api/v1/relay/check/stream \
  -H "Content-Type: application/json" \
  -d '{
    "algorithm": "full",
    "base_url": "https://relay.example.com/v1",
    "api_key": "sk-...",
    "model": "claude-sonnet-5",
    "iterations": 200,
    "no_think": true
  }'
```

### SSE 通用信封

每个 SSE 事件由 `event` 和 `data` 两部分组成。`data` 是 JSON：

```text
event: <事件名称>
data: {"status":0,"message":"...","data":{}}

```

| 字段 | 类型 | 说明 |
|---|---|---|
| `status` | integer | `0` 表示成功，`1` 表示失败 |
| `message` | string | 当前阶段或错误消息 |
| `data` | object | 阶段数据；没有数据的事件不包含该字段 |

服务端连接空闲超过约 15 秒时，可能发送 SSE 注释作为保活：

```text
: keepalive

```

保活行不是业务事件，客户端应忽略。

---

## 4. SSE 的 5 个阶段

SSE 定义了 `start`、`progress`、`result`、`done`、`error` 五种阶段事件。

正常流程：

```text
start → progress（0 到多次）→ result → done
```

失败流程：

```text
start → progress（0 到多次）→ error
```

`error` 是异常终止事件。当前实现发送 `error` 后不会再发送 `done`。

### 4.1 `start`：检测开始

每次检测固定发送一次。

#### 结构

```text
event: start
data: {"status":0,"message":"started","data":{"algorithm":"quick"}}

```

```json
{
  "status": 0,
  "message": "started",
  "data": {
    "algorithm": "quick"
  }
}
```

| 字段 | 类型 | 说明 |
|---|---|---|
| `data.algorithm` | string | 本次检测模式：`quick` 或 `full` |

### 4.2 `progress`：指纹采样进度

仅 `full` 模式的随机数指纹采样阶段会持续发送；`quick` 模式通常不会发送。

#### 结构

```text
event: progress
data: {"status":0,"message":"progress","data":{"completed_rate":0.66}}

```

```json
{
  "status": 0,
  "message": "progress",
  "data": {
    "completed_rate": 0.66
  }
}
```

| 字段 | 类型 | 说明 |
|---|---|---|
| `data.completed_rate` | number | 指纹采样完成率，取值范围 `0.0`～`1.0`，最多保留两位小数 |

### 4.3 `result`：最终检测结果

检测至少有一个算法成功时发送一次。某些子算法失败不一定触发 `error`，而是通过
`partial_errors` 返回部分失败信息。

#### 完整结构

```text
event: result
data: {"status":0,"message":"success","data":{"algorithm":"quick","score":100.0,"overall_verdict":"pass","summary":"未发现明显风险","detail":{"findings":[],"best_model":"","signature":{},"fingerprint":{}},"partial_errors":{}}}

```

格式化后的 JSON：

```json
{
  "status": 0,
  "message": "success",
  "data": {
    "algorithm": "quick",
    "score": 100.0,
    "overall_verdict": "pass",
    "summary": "未发现明显风险 (安全分 100/100, 发现 0 项)",
    "detail": {
      "findings": [],
      "best_model": "",
      "signature": {},
      "fingerprint": {}
    },
    "partial_errors": {}
  }
}
```

#### `result.data` 字段

| 字段 | 类型 | 说明 |
|---|---|---|
| `algorithm` | string | `quick` 或 `full` |
| `score` | number | `quick` 为黑盒审计安全分；`full` 为指纹后验百分制 |
| `overall_verdict` | string | `pass`、`risk` 或 `inconclusive`；综合所有必需子检查 |
| `summary` | string | 一句话检测结论 |
| `detail.findings` | array | 风险发现；没有风险时为空数组 |
| `detail.best_model` | string | `full` 的最匹配模型；无结果时为空字符串 |
| `detail.signature` | object | Claude Signature 聚合结果；非 Claude 或执行失败时为空对象 |
| `detail.fingerprint` | object | `full` 的后验概率与造假状态；其他模式为空对象 |
| `partial_errors` | object | 子算法部分失败信息；全部成功时为空对象 |

`overall_verdict=pass` 要求所有必需子算法完成、黑盒探针无风险、Claude Signature
（如适用）为 `native`，且 `full` 模式的已知基准声明获得足够后验支持。未知模型、
低置信度或部分失败返回 `inconclusive`，明确风险返回 `risk`。

逐探针执行状态、耗时和底层错误仅作为服务内部诊断数据，不属于公开响应契约。

#### `detail.findings[]` 字段

```json
{
  "probe": "liveness",
  "severity": "HIGH",
  "title": "Relay liveness failed"
}
```

| 字段 | 类型 | 说明 |
|---|---|---|
| `probe` | string | 产生该发现的黑盒探针名称 |
| `severity` | string | `LOW`、`MEDIUM` 或 `HIGH` |
| `title` | string | 风险标题 |

`probe` 的可能值：

| `probe` | 含义 |
|---|---|
| `models` | 模型列表一致性 |
| `liveness` | 基础聊天可用性 |
| `identity` | 模型身份弱信号 |
| `token_delta` | 隐藏 Prompt 或 token 注入 |
| `echo_rewrite` | 输出或工具命令改写 |
| `stream_integrity` | SSE 流式响应完整性 |
| `context_canary` | 长上下文截断 |

#### `detail.signature` 字段

Claude 模型示例：

```json
{
  "verdict": "suspect",
  "score": 72.7
}
```

| 字段 | 类型 | 说明 |
|---|---|---|
| `verdict` | string | `native`、`suspect` 或 `proxy` |
| `score` | number | Signature 检测百分制评分 |

### 4.4 `done`：正常结束

成功发送 `result` 后发送一次，表示服务端不会再发送业务事件。

#### 结构

```text
event: done
data: {"status":0,"message":"done"}

```

```json
{
  "status": 0,
  "message": "done"
}
```

`done` 没有 `data` 字段。

### 4.5 `error`：异常结束

当所有检测算法均失败，或检测调度发生未处理异常时发送一次。

#### 结构

```text
event: error
data: {"status":1,"message":"audit: HTTP 401; fingerprint: 样本不足(12/40)"}

```

```json
{
  "status": 1,
  "message": "audit: HTTP 401; fingerprint: 样本不足(12/40)"
}
```

| 字段 | 类型 | 说明 |
|---|---|---|
| `status` | integer | 固定为 `1` |
| `message` | string | 运行时错误摘要，最长 500 字符 |

`error` 没有 `data` 字段，且发送后连接结束。

---

## 5. `partial_errors` 结构

`partial_errors` 位于 `result.data.partial_errors`。它表示检测仍然产生了可用结果，
但一个或多个子算法执行失败。

### 可能的键

| 键 | 出现条件 |
|---|---|
| `audit` | 黑盒审计 7 探针整体执行失败 |
| `fingerprint` | `full` 模式的随机数指纹检测失败 |
| `signature` | Claude Thinking Signature 检测失败 |

每个值均为字符串错误摘要，最长 300 字符。该对象没有错误时固定返回 `{}`。

### 示例 1：全部成功

```json
{
  "partial_errors": {}
}
```

### 示例 2：Signature 失败，黑盒审计成功

此时仍发送 `result`，而不是 `error`：

```json
{
  "algorithm": "quick",
  "score": 100.0,
  "overall_verdict": "inconclusive",
  "summary": "未发现明显风险 (安全分 100/100, 发现 0 项)",
  "detail": {
    "findings": [],
    "best_model": "",
    "signature": {},
    "fingerprint": {}
  },
  "partial_errors": {
    "signature": "HTTP 400: extended thinking is not supported"
  }
}
```

### 示例 3：完整检测中多个子算法失败

只要至少一个子算法成功，仍然返回部分结果：

```json
{
  "algorithm": "full",
  "score": 0.0,
  "overall_verdict": "inconclusive",
  "summary": "[审计] 未发现明显风险 (安全分 100/100, 发现 0 项)",
  "detail": {
    "findings": [],
    "best_model": "",
    "signature": {},
    "fingerprint": {}
  },
  "partial_errors": {
    "fingerprint": "样本不足(12/40)",
    "signature": "未获取到有效 thinking signature"
  }
}
```

### `partial_errors` 与 `error` 的区别

| 情况 | SSE 事件 | 含义 |
|---|---|---|
| 至少一个子算法成功 | `result` → `done` | 可使用成功部分；失败项在 `partial_errors` |
| 所有子算法均失败 | `error` | 没有可用检测结果；连接直接结束 |

---

## 6. Python SSE 客户端示例

```python
import json
import requests

url = "http://127.0.0.1:8088/api/v1/relay/check/stream"
payload = {
    "algorithm": "quick",
    "base_url": "https://relay.example.com/v1",
    "api_key": "sk-...",
    "model": "gpt-5.6-sol",
}

with requests.post(url, json=payload, stream=True, timeout=900) as response:
    response.raise_for_status()
    event_name = None

    for raw_line in response.iter_lines(decode_unicode=True):
        if not raw_line or raw_line.startswith(":"):
            continue

        if raw_line.startswith("event:"):
            event_name = raw_line.removeprefix("event:").strip()
            continue

        if raw_line.startswith("data:"):
            envelope = json.loads(raw_line.removeprefix("data:").strip())
            print(event_name, envelope)

            if event_name == "result":
                result = envelope["data"]
                if result["partial_errors"]:
                    print("部分失败：", result["partial_errors"])

            if event_name in {"done", "error"}:
                break
```

---

## 7. HTTP 错误

SSE 开始前发生的请求错误使用普通 HTTP JSON 响应：

| HTTP 状态码 | 场景 | 响应示例 |
|---:|---|---|
| `400` | URL 无效、默认策略拒绝 HTTP/私网目标或 DNS 解析失败 | `{"detail":"base_url 默认要求 https；..."}` |
| `409` | 基准库为空时请求 `full` | `{"detail":"基准库为空，请先用 CLI 标定..."}` |
| `429` | 已达到 `AIG_API_CHECKER_MAX_JOBS` 并发上限 | `{"detail":"检测任务已满，请稍后重试"}` |
| `422` | 请求体字段校验失败 | `{"detail":"body.algorithm: Input should be 'full' or 'quick'"}` |

这些 HTTP 错误不会建立 SSE 事件流。

默认拒绝明文 HTTP 以及环回、私网、链路本地和保留地址。受控内网部署如确需检测
此类目标，可分别设置 `AIG_API_CHECKER_ALLOW_HTTP=1` 和
`AIG_API_CHECKER_ALLOW_PRIVATE_TARGETS=1`；同时应在外层网关启用身份认证和出站
网络策略。算法 HTTP 客户端不会跟随重定向，避免目标借重定向绕过初始地址策略。
