# Code-Attack 模块

当目标包含代码仓库、Skill 包、MCP Server、插件、Agent 定义或本地 Agent 扩展时使用本模块。目标不是“搜索危险函数”，而是判断攻击者可控输入能否到达高权限行为，或能否投毒宿主 Agent。

## 第一性原理审计模型

对每个目标回答：

```text
这个组件声称做什么？
它实际拥有哪些能力？
攻击者可控输入从哪里进入？
这些输入能到达哪些高权限 sink？
跨越了什么信任边界？
在真实使用中是否可达？
什么无害证明可以确认影响？
```

## 审计流程

### 1. 理解声明意图

只读取理解组件所需的文件：

- `README*`
- `SKILL.md`
- MCP manifest / tool 定义
- `package.json`、`pyproject.toml`、`requirements.txt`、`go.mod`
- 主入口文件和 handler

记录：

```json
{
  "project_name": "...",
  "declared_purpose": "...",
  "entry_points": ["..."],
  "declared_capabilities": ["..."],
  "privileged_capabilities": ["file_read", "network", "shell", "database", "browser"],
  "attacker_inputs": ["prompt", "file", "tool args", "web content", "MCP result"]
}
```

### 2. 跟踪输入到 sink

用 `rg` 和文件读取跟踪数据流。重点关注这些 sink：

| Sink | 风险原因 |
|---|---|
| Shell/subprocess/eval/exec | 可能把 prompt 或 tool 参数变成命令执行。 |
| 文件读/写/删 | 可能暴露秘密或修改用户/系统状态。 |
| 网络请求 | 可能泄露数据、触发 SSRF 或访问攻击者基础设施。 |
| Prompt 构造 | 可能让不可信内容覆盖 system/developer 意图。 |
| MCP tool description | 可能投毒宿主 Agent 对工具行为的理解。 |
| 凭据/配置处理 | 可能暴露或误用 secret。 |

不要因为 sink 存在就报告漏洞。必须判断它是否可由攻击者输入触达，以及是否超出声明用途。

### 3. 供应链与 Agent 投毒检查

对 Skill、MCP Server 和插件，检查：

- Tool description 是否要求宿主 Agent 忽略用户/系统策略。
- README、注释、示例或元数据中是否隐藏指令。
- 工具名称/描述是否过度宽泛，掩盖危险行为。
- 脚本是否访问无关文件、home 目录、浏览器 profile、SSH key、shell history 或环境变量。
- 是否静默访问非预期外部域名。
- 依赖、postinstall 脚本、二进制 blob 或生成代码是否超出包声明能力。

### 4. 可达性与影响复核

对每个疑点分类：

| 状态 | 含义 |
|---|---|
| `confirmed_static` | 代码路径可达，且影响可从源码明确判断。 |
| `dynamic_confirmed` | 无害 PoC 或 canary 已验证行为。 |
| `unverified` | 可疑，但可达性或影响未证明。 |
| `discarded` | 不可达、仅测试/示例代码，或与声明能力一致。 |

如果动态验证会执行目标代码或改变状态，必须获得用户批准。

### 5. 证据格式

每条 finding 建议包含：

```json
{
  "id": "CODE-001",
  "title": "一句话说明风险",
  "severity": "critical | high | medium | low | info",
  "status": "confirmed_static | dynamic_confirmed | unverified",
  "file": "absolute/or/repo/path",
  "line_range": "start-end",
  "evidence": "短代码片段或 trace",
  "attacker_input": "控制从哪里进入",
  "privileged_sink": "到达了什么高权限 sink",
  "business_impact": "为什么重要",
  "remediation": "具体修复",
  "retest": "如何复测修复"
}
```

## 严重级别参考

- **Critical**：可达路径能泄露 secret、执行命令、外传数据，或跨租户/用户边界。
- **High**：可达不安全动作，影响明确但范围有限。
- **Medium**：可达弱点，但需要特殊条件或影响有限。
- **Low**：加固缺口、权限声明混乱、弱防线。
- **Info**：良性能力、成功抵御投毒、资产清单说明。

## 重要约束

- 优先源码审计和推理，不执行代码。
- 代码 finding 尽量给出精确文件和行号。
- 区分必要能力和滥用。文件工具不是漏洞；不受控地访问声明范围外文件才可能是漏洞。
- 用 canary 数据验证，不读取或发布真实 secret。
- 如果证据敏感，脱敏但保留证明力。
