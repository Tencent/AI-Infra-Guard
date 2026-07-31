AIG API Checker HTTP API
●版本：v1.7.0
●默认地址：http://21.214.127.143:8000
●示例Web 检测页：http://21.214.127.143:8000/ui
●Swagger 文档：/docs
●API 前缀：/api/v1
测试结果仅供参考，不能作为商业纠纷、退款索赔的绝对法律或事实依据。
1. 接口总览
方法	路径	说明
GET	/api/v1/relay/models	获取当前支持完整指纹识别的模型列表
POST	/api/v1/relay/check/stream	API 中转检查 SSE 流式接口
检测算法
algorithm	检测内容
quick	C：黑盒审计 7 探针；Claude 模型自动叠加 B
full	A：随机数指纹 + C：黑盒审计 7 探针；Claude 模型自动叠加 B
模型 ID 包含 sonnet、opus、haiku 或 fable 时，不区分大小写地识别为
 Claude，并自动叠加算法 B（Thinking Signature 验证）。
2. 获取可检测模型
GET /api/v1/relay/models
模型列表从 baselines.json 动态读取。Claude 和 GPT 系列排在前面，同系列中
 版本号较新的型号优先。请求示例

curl http://21.214.127.143:8000/api/v1/relay/models

响应结构

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
      "quick": "支持 models 列表中的模型，不在列表中的模型型号只支持openai格式，进行快速检测"
    }
  }
}

字段	类型	说明
status	integer	0 表示成功
message	string	响应消息
data.models	array	可进行完整指纹识别的模型
data.models[].id	string	请求检测接口时使用的模型 ID
data.models[].name	string	模型显示名称
data.models[].provider	string	anthropic 或 openai_compatible
data.total	integer	模型总数
data.algorithms	object	两种检测模式的能力说明

3. API 中转检查 SSE
POST /api/v1/relay/check/stream
检测通常需要 30 秒到数分钟。接口返回 text/event-stream，客户端需要保持连接，
 逐条处理 SSE 事件，直到收到 done 或 error。
请求体
字段	类型	必填	默认值	说明
algorithm	string	是	—	quick 或 full
base_url	string	是	—	待测 API 基础 URL，带不带 /v1 均可
api_key	string	是	—	待测 API 密钥，仅在内存使用
model	string	是	—	待测模型 ID
language	string	否	zh	结果文本语言：zh 或 en；影响 summary、findings[].title 和 findings[].severity
iterations	integer	否	200	网页不显示，仅 full 使用，范围为 50–500
no_think	boolean	否	true	网页不显示，仅 full 使用，是否关闭模型思考
请求示例
快速检测：

curl -N -X POST http://21.214.127.143:8000/api/v1/relay/check/stream \
  -H "Content-Type: application/json" \
  -d '{
    "algorithm": "quick",
    "base_url": "https://relay.example.com/v1",
    "api_key": "sk-...",
    "model": "gpt-5.6-sol"
  }'

完整检测：

curl -N -X POST http://21.214.127.143:8000/api/v1/relay/check/stream \
  -H "Content-Type: application/json" \
  -d '{
    "algorithm": "full",
    "base_url": "https://relay.example.com/v1",
    "api_key": "sk-...",
    "model": "claude-sonnet-5",
    "language": "en",
    "iterations": 200,
    "no_think": true
  }'

SSE 通用信封
每个 SSE 事件由 event 和 data 两部分组成。data 是 JSON：

event: <事件名称>
data: {"status":0,"message":"...","data":{}}


字段	类型	说明
status	integer	0 表示成功，1 表示失败
message	string	当前阶段或错误消息
data	object	阶段数据；没有数据的事件不包含该字段
服务端连接空闲超过约 15 秒时，可能发送 SSE 注释作为保活：

: keepalive


保活行不是业务事件，客户端应忽略。

4. SSE 的 5 个阶段
SSE 定义了 start、progress、result、done、error 五种阶段事件。
正常流程：

start → progress（0 到多次）→ result → done

失败流程：

start → progress（0 到多次）→ error

error 是异常终止事件。当前实现发送 error 后不会再发送 done。
4.1 start：检测开始
每次检测固定发送一次。
结构

event: start
data: {"status":0,"message":"started","data":{"algorithm":"quick"}}



{
  "status": 0,
  "message": "started",
  "data": {
    "algorithm": "quick"
  }
}

字段	类型	说明
data.algorithm	string	本次检测模式：quick 或 full
4.2 progress：检测进度
full 模式在随机数指纹采样阶段按样本持续发送；quick 模式在 7 个黑盒探针
逐个完成时发送，因此两种模式都会以 `completed_rate: 1.0` 结束进度阶段。
结构

event: progress
data: {"status":0,"message":"progress","data":{"completed_rate":0.66}}



{
  "status": 0,
  "message": "progress",
  "data": {
    "completed_rate": 0.66
  }
}

字段	类型	说明
data.completed_rate	number	进度比例，范围 0.0–1.0
4.3 result：最终检测结果
检测至少有一个算法成功时发送一次。
完整结构

event: result
data: {"status":0,"message":"success","data":{"algorithm":"quick","score":100.0,"summary":"未发现明显风险","detail":{"findings":[],"best_model":"","fingerprint":{},"test_info":{"latency_ms":750,"tokens_per_second":20.0,"input_tokens":150,"output_tokens":30,"cache_read_tokens":65}}}}


格式化后的 JSON：

{
  "status": 0,
  "message": "success",
  "data": {
    "algorithm": "quick",
    "score": 100.0,
    "summary": "未发现明显风险 (安全分 100/100, 发现 0 项)",
    "detail": {
      "findings": [],
      "best_model": "",
      "fingerprint": {},
      "test_info": {
        "latency_ms": 750,
        "tokens_per_second": 20.0,
        "input_tokens": 150,
        "output_tokens": 30,
        "cache_read_tokens": 65
      }
    }
  }
}

result.data 字段
字段	类型	说明
algorithm	string	quick 或 full
score	number	quick 为黑盒审计安全分；full 为指纹后验百分制
summary	string	一句话检测结论
detail.findings	array	风险发现；没有风险时为空数组
detail.best_model	string	full 的最匹配模型；无结果时为空字符串
detail.fingerprint	object	full 的后验概率与造假状态；其他模式为空对象
detail.test_info	object	延迟、生成速度、输入/输出 Token 和缓存读取汇总
detail.findings[] 字段

{
  "probe": "liveness",
  "severity": "不通过",
  "title": "中转服务连通性检查失败"
}

字段	类型	说明
probe	string	探针标识
severity	string	zh 返回“不通过”；en 返回“Failed”
title	string	风险标题

`language` 省略时默认为 `zh`。传入 `en` 后，`summary` 和
`detail.findings[].title`、`detail.findings[].severity` 返回英文，例如：

```json
{
  "summary": "High risk (safety score 50/100, 1 finding)",
  "detail": {
    "findings": [{
      "probe": "liveness",
      "severity": "Failed",
      "title": "Relay liveness failed"
    }]
  }
}
```

字段名以及 `overall_verdict` 的 `pass`、`risk`、`inconclusive` 等机器枚举不随语言变化。

4.4 done：正常结束
成功发送 result 后发送一次，表示服务端不会再发送业务事件。
结构

event: done
data: {"status":0,"message":"done"}



{
  "status": 0,
  "message": "done"
}

done 没有 data 字段。
4.5 error：异常结束
当所有检测算法均失败，或检测调度发生未处理异常时发送一次。
结构

event: error
data: {"status":1,"message":"audit: HTTP 401; fingerprint: 样本不足(12/40)"}


{
  "status": 1,
  "message": "audit: HTTP 401; fingerprint: 样本不足(12/40)"
}

字段	类型	说明
status	integer	固定为 1
message	string	运行时错误摘要，最长 500 字符
error 没有 data 字段，且发送后连接结束。

6. Python SSE 客户端示例

import json
import requests

url = "http://21.214.127.143:8000/api/v1/relay/check/stream"
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

            if event_name in {"done", "error"}:
                break


7. HTTP 错误
SSE 开始前发生的请求错误使用普通 HTTP JSON 响应：
HTTP 状态码	场景	响应示例
400	base_url 不是 HTTP(S) URL	{"detail":"base_url 必须以 http:// 或 https:// 开头"}
409	基准库为空时请求 full	{"detail":"基准库为空，请先用 CLI 标定..."}
422	请求体字段校验失败	{"detail":"some error:xxxxxx"}
这些 HTTP 错误不会建立 SSE 事件流。
