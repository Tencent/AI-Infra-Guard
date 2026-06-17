# Infra-Attack 模块

当目标包含 HTTP 服务、AI 网关、模型服务、Agent endpoint、本地 Web UI 或暴露的 AI 基础设施时使用本模块。基础设施审查是蓝军演习中的确定性辅助：它识别什么可达、看起来是什么组件，然后由 Agent 判断真实暴露面和影响。

## 第一性原理问题

对每个可达服务回答：

```text
谁可以访问它？
它是什么产品或组件？
可见版本是什么？
是否需要认证？
端点暴露了什么数据或动作？
这种暴露在当前环境中是否符合预期？
什么安全请求可以证明风险？
```

## 何时使用辅助脚本

对已知 URL 或 host:port 使用脚本：

```bash
python3 modules/infra-attack/scripts/run.py \
  --target http://host:port \
  --aig-root /path/to/AI-Infra-Guard \
  --out reports/<run_id>/infra-attack_findings.json
```

如果本地没有 AIG 数据，且用户允许联网下载，可使用：

```bash
python3 modules/infra-attack/scripts/run.py \
  --target http://host:port \
  --download-aig-data \
  --out reports/<run_id>/infra-attack_findings.json
```

该辅助脚本可以：

- 规范化并探测 URL。
- 优先匹配 [tencent/AI-Infra-Guard](https://github.com/tencent/AI-Infra-Guard) `data/fingerprints/`，找不到时回退内置指纹。
- 在指纹支持时提取版本。
- 如果存在 [tencent/AI-Infra-Guard](https://github.com/tencent/AI-Infra-Guard) `data/vuln/` 或 `data/vuln_en/`，匹配 CVE/漏洞规则。
- 当服务看起来暴露 LLM endpoint 时，建议模型级后续测试。

不要把脚本输出当作最终风险。指纹是暴露证据；可利用性取决于可达性、认证、版本置信度和可访问功能。

## 人工复核清单

探测后检查：

| 区域 | 需要验证什么 |
|---|---|
| 可达性 | 仅 localhost、私网、公网，还是认证网关后。 |
| 认证 | 未认证请求是否暴露模型、文件、任务、配置或管理功能。 |
| 产品/版本 | 指纹和版本提取的置信度。 |
| 敏感端点 | 模型清单、上传/下载、任务执行、插件/管理 API、日志、trace。 |
| CORS/origin | 是否可能被浏览器侧滥用。 |
| 默认部署 | 默认凭据、debug 模式、未认证本地面板。 |
| 业务上下文 | 该服务是个人开发、测试环境还是生产环境。 |

## 安全验证模式

- 先使用只读 `GET` 或文档化元数据端点。
- 不爆破目录或凭据。
- 除非明确授权，不运行 exploit PoC。
- 对未认证访问，用无害元数据证明，例如 status、title、模型数量或 canary endpoint。
- 对 localhost/个人开发服务，准确描述本地风险；除非证据证明公网可达，不要称为公网暴露。

## Finding 格式

```json
{
  "id": "INFRA-001",
  "title": "未授权访问暴露模型清单",
  "severity": "high",
  "status": "confirmed",
  "target": "http://host:port",
  "product": "ollama",
  "version": "0.x",
  "evidence": {
    "request": "GET /api/tags",
    "response_summary": "200 OK, returned model inventory",
    "sensitive_values_redacted": true
  },
  "business_impact": "攻击者可枚举可用模型并推断内部 AI 能力。",
  "remediation": "限制监听地址、启用认证或放到受控网关后。",
  "retest": "无认证访问同一端点应返回 401/403 或不可达。"
}
```

## 严重级别参考

- **Critical**：未认证端点允许命令/任务执行、数据读写、管理动作或凭据暴露。
- **High**：未认证端点暴露有意义的模型、文件、租户、trace 或配置数据。
- **Medium**：存在版本化漏洞组件且暴露合理，但未确认敏感动作。
- **Low**：受限环境中的 debug 元数据或加固缺口。
- **Info**：指纹、本地-only 暴露或服务资产清单。

## 数据资产

- [tencent/AI-Infra-Guard](https://github.com/tencent/AI-Infra-Guard) `data/fingerprints/`：首选 AI 基础设施指纹数据源。
- [tencent/AI-Infra-Guard](https://github.com/tencent/AI-Infra-Guard) `data/vuln/`：首选中文漏洞规则数据源。
- [tencent/AI-Infra-Guard](https://github.com/tencent/AI-Infra-Guard) `data/vuln_en/`：英文漏洞规则数据源，可通过 `--vuln-lang en` 使用。
- 本 skill 内置 `modules/infra-attack/data/`：AIG data 不可用时的最小回退数据。

数据源解析顺序：命令行参数 → `AIG_DATA_DIR`/`AIG_ROOT` → 常见本地路径 → `--download-aig-data` 临时下载 → 内置数据。

## 限制

- 辅助脚本是轻量 HTTP 指纹工具，不是完整漏洞扫描器。
- 它不能证明 CVE 可利用性。
- 未经明确授权，不应用于大范围网络扫描。
