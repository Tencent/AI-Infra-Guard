# API Checker 集成说明

API Checker 的 Python 运行时合并在 Agent 镜像和容器中，由容器入口脚本与 Go Agent
共同运行；现有 Gin WebServer 继续提供同源入口：

```text
独立前端 / API 客户端
        │
        ▼
AIG WebServer :8088
  ├─ /api-checker/{healthz,openapi.json,docs,redoc} ─┐
  └─ /api/v1/relay/*                                 ─┴─► Agent 容器 :8000
                                                        ├─ API Checker (Python)
                                                        └─ AIG Agent (Go)
```

这种边界减少了发布和部署所需的镜像、容器数量，同时完整保留 checker 所需的
NumPy、SciPy、FastAPI 及 A–E 五类 CLI 算法。反向代理只在内存中解析有大小限制的
检测请求，以处理模型配置来源；不会记录或持久化 API Key，并对 SSE 响应逐次刷新。

## 功能入口

| 能力 | 入口 |
|---|---|
| 模型列表 | `GET /api/v1/relay/models` |
| quick/full SSE 检测（手动密钥或 AIG 配置） | `POST /api/v1/relay/check/stream` |
| AIG 已配置模型列表 | `GET /api/v1/app/models`（复用原有接口） |
| A–E 完整 CLI | `ai-infra-guard api-checker ...` |
| Checker OpenAPI | `/api-checker/docs` |
| Checker 健康检查 | `/api-checker/healthz` |

HTTP 服务覆盖随机数指纹、Claude Thinking Signature 与中转黑盒审计。PAMELA 和
Ventor QTest 保持为 CLI 能力，避免在匿名 HTTP 请求中触发高成本批量任务。

独立部署的前端可通过原有 `GET /api/v1/app/models` 接口读取 AIG 模型管理中已经保存且当前
用户可见的配置；该接口只返回掩码后的 `token: "********"`。开始检测时前端仅提交
`use_configured_model: true` 和 `model_id`，AIG WebServer 在服务端读取并注入真实 API Key，再把请求
转发给 Checker。真实 Key 不会返回前端，也不会转发 AIG 会话相关请求头。

检测请求可传 `language: "zh"` 或 `language: "en"`，省略时默认中文。该参数同时
支持手动密钥和 AIG 配置两种来源，只影响返回结果中的 `summary` 与
`detail.findings[].title`；字段名和 `overall_verdict`、`risk_level` 等机器枚举
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
保持空值，可从 8000 端口直接访问 API、健康检查和 OpenAPI 文档。

GitHub Release 的 Agent 镜像内置 API Checker Python 源码和隔离虚拟环境，不再发布
独立 Checker 镜像。源码 CLI 仅适用于源码仓库；使用前需创建虚拟环境并安装依赖，或通过
`AIG_API_CHECKER_PYTHON` 指向已有环境。

## Docker Compose

```bash
docker compose up -d --build
```

Agent 容器先启动 Checker；Checker 健康后 WebServer 才启动。Go Agent 在容器内持续
尝试连接 WebServer，因此不会形成 Compose 循环依赖。Checker 是容器关键进程，退出时
容器整体重启；Go Agent 进程退出时由入口脚本单独拉起，不影响 Checker。Compose 仅向
宿主暴露 AIG 的 `8088`，Agent 容器的 `8000` 只在内部网络开放。
`api-checker-data` 卷挂载到 Agent 容器的 `/api-checker-data`，保存标定基准和运行数据；
升级已有部署时入口脚本会修正旧卷权限，然后以非 root `agent` 用户运行两个业务进程。

## 配置

| 环境变量 | 默认值 | 说明 |
|---|---|---|
| `AIG_API_CHECKER_URL` | 本地二进制为 `http://127.0.0.1:8000`；WebServer 镜像为 `http://agent:8000` | Gin 代理的上游；空值禁用 |
| `AIG_API_CHECKER_DIR` | 自动发现 | Go CLI 查找 Python 服务目录 |
| `AIG_API_CHECKER_PYTHON` | `python3`/`python` | Go CLI 使用的解释器 |
| `AIG_API_CHECKER_ROOT_PATH` | 直接运行为空 | OpenAPI 文档经统一 CLI/Docker 反代时使用的 `/api-checker` 前缀 |
| `AIG_API_CHECKER_DATA_DIR` | `services/api_checker/runtime` | 可写运行数据目录 |
| `AIG_API_CHECKER_BASELINES` | `<data-dir>/baselines.json` | 外部基准覆盖文件 |
| `AIG_PAMELA_REFERENCE` | 内置参考库 | PAMELA 参考分布覆盖文件 |
| `AIG_API_CHECKER_MAX_JOBS` | `20` | 同时执行的 HTTP 检测任务上限 |
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
- Agent 容器中的 Checker 端口默认不映射到宿主，避免绕过 AIG 的统一访问控制。Agent
  具有扫描所需的额外容器权限，因此生产环境更应限制对 `8088` 的入口和容器出站网络。

完整 HTTP 契约见
[services/api_checker/docs/API.md](../services/api_checker/docs/API.md)。
