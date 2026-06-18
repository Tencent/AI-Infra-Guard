# A.I.G Agent 护网 — 一句话给 Agent 做安全演习

[English](./README.md)

面向 AI Agent 的全方位红队安全演习技能。装进你的 Agent 客户端，让它以攻击者视角攻击自己——测试提示词注入、间接注入、工具滥用、数据泄露、权限提升、SSRF、供应链风险、基础设施暴露等全攻击面。

基于腾讯朱雀实验室 [A.I.G](https://github.com/Tencent/AI-Infra-Guard) 的第一性原理蓝军方法论。

### 安装

```bash
npx skills add https://github.com/Tencent/AI-Infra-Guard.git --skill aig-agent-redteam
```

备选方案，从源码安装：

```text
https://github.com/Tencent/AI-Infra-Guard/tree/main/skills/aig-agent-redteam
```

需要 `node` 和 `git`。支持 Claude Code、CodeBuddy、Cursor 等主流 Agent 客户端。

如果 `npx skills` 不可用，手动安装：

```bash
git clone https://github.com/Tencent/AI-Infra-Guard.git /tmp/aig
cp -r /tmp/aig/skills/aig-agent-redteam ~/.claude/skills/
```

### 使用

安装后直接对话：

**个人开发者（IDE Agent）** — 审计已安装的 Skill、MCP Server 和供应链安全：

```
帮我进行安全演习
```

**生产级业务 Agent** — 全攻击面覆盖：基础设施扫描、代码审计、动态安全测试、越狱评估、工作流攻击：

```
帮我进行安全演习
```

此 Skill 会自动识别 Agent 类型并适配测试范围。对于生产级 Agent，覆盖以下维度：

- **基础设施扫描**：AI 服务指纹识别 + CVE 匹配（Ollama、vLLM、Dify 等）
- **代码审计**：Skill 源码、MCP Server 代码、依赖供应链静态分析
- **动态安全测试**：30+ 条 prompt injection payload，支持自适应变异（角色扮演、编码绕过、多轮渐进突破）
- **越狱评估**：Parseltongue 编码递进引擎，测试模型边界
- **工作流攻击**：模拟多步任务链滥用，通过文档/RAG 进行间接注入
- **完整报告**：按严重级别分组的 findings，附证据链、正面防御验证和修复建议——所有数据不出本机

### 注意事项

- 所有测试数据留在本机，不上报任何服务器。
- Skill 使用第一性原理推理，非盲跑 payload 库。
- 执行前会确认目标范围，破坏性操作需明确授权。
- 支持 Claude Code、CodeBuddy、Cursor 及任何支持 Skills 的 Agent 客户端。

---

扫描能力由腾讯朱雀实验室 [A.I.G](https://github.com/Tencent/AI-Infra-Guard) 提供
