# API Checker 集成说明

API Checker 以独立 Python sidecar 集成到 AIG，并由现有 Gin WebServer 提供同源入口：

```text
浏览器 / API 客户端
        │
        ▼
AIG WebServer :8088
  ├─ /api-checker/*       ─┐
  └─ /api/v1/relay/*      ─┴─► API Checker :8000（内部端口）
```

这种边界保留了 AIG 的 Go 核心和单二进制扫描能力，同时完整保留 checker 所需的
NumPy、SciPy、FastAPI 及 A–E 五类 CLI 算法。反向代理只在内存中解析有大小限制的
检测请求，以处理模型配置来源；不会记录或持久化 API Key，并对 SSE 响应逐次刷新。

## 功能入口

| 能力 | 入口 |
|---|---|
| 检测页面 | `http://127.0.0.1:8088/api-checker/` |
| 模型列表 | `GET /api/v1/relay/models` |
| quick/full SSE 检测（手动密钥或 AIG 配置） | `POST /api/v1/relay/check/stream` |
| AIG 已配置模型列表 | `GET /api/v1/app/models`（复用原有接口） |
| A–E 完整 CLI | `ai-infra-guard api-checker ...` |
| Checker OpenAPI | `/api-checker/docs` |

HTTP 服务覆盖随机数指纹、Claude Thinking Signature 与中转黑盒审计。PAMELA 和
Ventor QTest 保持为 CLI 能力，避免在匿名 HTTP 请求中触发高成本批量任务。

检测页面通过原有 `GET /api/v1/app/models` 接口读取 AIG 模型管理中已经保存且当前
用户可见的配置；该接口只返回掩码后的 `token: "********"`。开始检测时浏览器仅提交
`use_configured_model: true` 和 `model_id`，AIG WebServer 在服务端读取并注入真实 API Key，再把请求
转发给 Checker。真实 Key 不会返回浏览器，也不会转发 AIG 会话相关请求头。

检测请求可传 `language: "zh"` 或 `language: "en"`，省略时默认中文。该参数同时
支持手动密钥和 AIG 配置两种来源，只影响返回结果中的 `summary` 与
`detail.findings[].title`；字段名和 `pass`、`risk`、`inconclusive` 等机器枚举
保持不变。

手动密钥模式省略 `use_configured_model`（或传 `false`），并继续提交 `base_url`、
`api_key`、`model`。AIG 配置模式请求示例：

```json
{
  "use_configured_model": true,
  "model_id": "openrouter-model",
  "algorithm": "quick",
  "language": "zh",
  "iterations": 200,
  "no_think": true
}
```

## 本地运行

先安装 Python 依赖并构建 AIG：

```bash
python3 -m venv services/api_checker/.venv
services/api_checker/.venv/bin/pip install -r services/api_checker/requirements.txt
go build -o ai-infra-guard ./cmd/cli/main.go
```

终端一启动 checker：

```bash
AIG_API_CHECKER_ROOT_PATH=/api-checker \
  services/api_checker/.venv/bin/python services/api_checker/server.py
```

终端二启动统一 WebServer：

```bash
./ai-infra-guard webserver \
  --server 127.0.0.1:8088 \
  --api-checker-url http://127.0.0.1:8000
```

运行统一 CLI：

```bash
export AIG_API_CHECKER_PYTHON="$PWD/services/api_checker/.venv/bin/python"
./ai-infra-guard api-checker list
./ai-infra-guard api-checker audit
./ai-infra-guard api-checker pamela
./ai-infra-guard api-checker qtest openrouter-providers --model moonshotai/kimi-k2.5
```

`api-checker serve` 从 `HOST`、`PORT` 读取监听配置。源码仓库中的统一 CLI 会自动
发现 checker 目录；如采用自定义目录，可设置 `AIG_API_CHECKER_DIR`。统一命令启动服务时默认把
`AIG_API_CHECKER_ROOT_PATH` 设为 `/api-checker`；直接运行 `python server.py` 时
保持空值，可从 8000 端口直接访问。

GitHub Release 包通过 Compose 使用同版本的预构建 API Checker sidecar 镜像，不携带
Python 源码。源码 CLI 仅适用于源码仓库；使用前需创建虚拟环境并安装依赖，或通过
`AIG_API_CHECKER_PYTHON` 指向已有环境。

## Docker Compose

```bash
docker compose up -d
```

Compose 仅向宿主暴露 AIG 的 `8088`，checker 的 `8000` 只在内部网络开放。
`api-checker-data` 卷保存标定基准和运行数据。WebServer 与 checker 独立启动，checker
暂时不可用时仅相关代理接口返回 `502`，不会阻塞 AIG 原有功能。

## 配置

| 环境变量 | 默认值 | 说明 |
|---|---|---|
| `AIG_API_CHECKER_URL` | `http://127.0.0.1:8000` | Gin 代理的上游；空值禁用 |
| `AIG_API_CHECKER_DIR` | 自动发现 | Go CLI 查找 Python 服务目录 |
| `AIG_API_CHECKER_PYTHON` | `python3`/`python` | Go CLI 使用的解释器 |
| `AIG_API_CHECKER_ROOT_PATH` | 直接运行为空 | 统一 CLI/Docker 反代时默认为 `/api-checker` |
| `AIG_API_CHECKER_DATA_DIR` | `services/api_checker/runtime` | 可写运行数据目录 |
| `AIG_API_CHECKER_BASELINES` | `<data-dir>/baselines.json` | 外部基准覆盖文件 |
| `AIG_PAMELA_REFERENCE` | 内置参考库 | PAMELA 参考分布覆盖文件 |
| `AIG_API_CHECKER_MAX_JOBS` | `2` | 同时执行的 HTTP 检测任务上限 |
| `AIG_API_CHECKER_ALLOW_HTTP` | `false` | 允许向可信目标用明文 HTTP 发送 Key |
| `AIG_API_CHECKER_ALLOW_PRIVATE_TARGETS` | `false` | 允许环回、私网或链路本地目标 |
| `AIG_API_CHECKER_CORS_ORIGINS` | 空 | 逗号分隔的额外跨域来源；默认仅同源 |
| `HOST` / `PORT` | `0.0.0.0` / `8000` | Python 服务监听地址 |

外部基准不存在时会读取内置的 28 个只读种子基准；首次标定时采用原子写入，在数据
目录创建可更新副本。PAMELA 候选分布和 QTest 的默认结果也写入该数据目录。

## 验证

离线单元测试不访问真实模型：

```bash
go test ./common/apichecker ./cmd/cli/cmd
services/api_checker/.venv/bin/python -m unittest discover \
  -s services/api_checker/tests -p 'test_*.py'
python3 -m compileall -q services/api_checker
```

健康与模型列表烟测：

```bash
curl http://127.0.0.1:8088/api-checker/healthz
curl http://127.0.0.1:8088/api/v1/relay/models
```

## 安全边界

- 检测会向用户提交的 `base_url` 发起服务端请求。默认拒绝明文 HTTP、私网、环回、
  链路本地和保留地址，且算法客户端不跟随重定向；可信内网目标需显式开启上述
  `ALLOW_*` 开关。
- 公网部署仍应在外层网关增加认证、频率限制和出站网络策略，以覆盖 DNS 重绑定等
  仅靠应用层校验无法彻底消除的风险。
- 使用临时、低权限 API Key；Key 只在检测进程内存和单次请求中使用，不写入基准、
  结果或代理错误响应；QTest 导出配置只保存环境变量占位符。
- `full`、PAMELA、QTest 会产生多次付费模型请求，执行前应确认预算。
- HTTP 客户端断开后会协作取消未开始的指纹请求；已经发出的单次请求仍需等待其自身
  超时，因此出站限额仍然必要。
- Checker sidecar 默认不映射宿主端口，避免绕过 AIG 的统一访问控制。

完整 HTTP 契约见
[services/api_checker/docs/API.md](../services/api_checker/docs/API.md)。
