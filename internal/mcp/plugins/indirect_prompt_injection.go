package plugins

import (
	"context"
	"fmt"

	"github.com/Tencent/AI-Infra-Guard/internal/mcp/utils"
)

// ResourcePoisoningPlugin 资源投毒检测插件
type ResourcePoisoningPlugin struct {
}

// NewResourcePoisoningPlugin 创建新的资源投毒检测插件
func NewResourcePoisoningPlugin() *ResourcePoisoningPlugin {
	return &ResourcePoisoningPlugin{}
}

// 获取插件信息
func (p *ResourcePoisoningPlugin) GetPlugin() Plugin {
	return Plugin{
		Name:   "间接提示注入",
		Desc:   "检测MCP代码中可能存在的间接提示注入",
		ID:     "indirect_prompt_injection",
		NameEn: "Indirect Prompt Injection",
		DescEn: "Detecting indirect prompt injection in MCP code",
	}
}

// AI提示词模板
const indirectPromptInjectionAIPrompt = `
作为专业的AI安全分析专家，你需要精确检测MCP代码中的间接提示词注入漏洞。此检测要求极高精度，只有发现确凿的提示词注入攻击才能报告。

## 漏洞定义
间接提示词注入是指通过外部数据源（文件、网络、数据库等）向LLM注入恶意指令，操纵模型行为或绕过安全限制。

## 检测标准（必须同时满足）

### 1. 外部数据源识别
**必须确认：**
- 存在从外部获取数据的功能（文件读取、网络请求、数据库查询）
- 外部数据直接或间接传递给LLM处理
- 数据来源不在应用控制范围内（用户上传、第三方API、公共资源）
- 缺少对外部数据的安全验证

### 2. 恶意指令注入点
**必须识别：**
- 外部数据被用作LLM的提示词或上下文
- 存在指令分隔符或特殊标记被利用的可能
- 恶意指令能够覆盖或修改原有提示词
- 注入的指令能够改变LLM的预期行为

### 3. 安全控制绕过
**必须验证：**
- 能够通过注入指令绕过系统的安全限制
- 可以获取超出预期权限的信息或功能
- 存在信息泄露或恶意操作的风险
- 缺少有效的输入过滤和输出检查

## 技术检测模式

### 数据流分析
**关键路径：**
1. 外部数据获取 → 数据处理 → LLM输入
2. 用户输入 → 文件/网络获取 → 提示词构造
3. 第三方API → 数据解析 → 模型推理

### 高风险代码模式
**文件读取注入：**
- 读取用户指定文件作为提示词内容
- 处理包含LLM指令的文档或配置文件
- 动态加载外部模板或脚本

**网络数据注入：**
- 从不可信网站抓取内容作为LLM输入
- 处理第三方API返回的未验证数据
- 解析包含恶意指令的JSON/XML响应

**数据库注入：**
- 查询结果直接用作提示词构造
- 用户生成内容未经过滤直接使用
- 历史对话记录的安全隐患

## 攻击向量识别

### 指令分隔攻击
- 使用特殊标记分隔原有指令：三个反引号、---、###
- 通过注释符号隐藏恶意指令：HTML注释、井号、双斜杠
- 利用模型的特殊响应格式：INST标签、im_start标记

### 角色扮演攻击
- 通过"你现在是..."重新定义模型角色
- 利用"忽略之前的指令"覆盖原始提示
- 使用"以开发者模式"绕过安全限制

### 上下文污染
- 在大量正常内容中隐藏恶意指令
- 通过多轮对话逐步建立恶意上下文
- 利用模型的长文本处理能力隐藏攻击

## 排除条件（以下不报告）

### 安全的实现模式
- 对外部数据进行严格的安全过滤
- 使用白名单验证外部数据来源
- 实施了内容安全策略（CSP）
- 对LLM输出进行二次验证

### 正常功能场景
- 处理可信来源的结构化数据
- 官方API的标准数据格式
- 内部系统的配置文件读取
- 经过安全审计的模板系统

### 开发和测试代码
- 单元测试中的mock数据
- 开发环境的调试功能
- 示例代码和文档片段
- 临时的开发工具

## 验证要求
1. **攻击可行性**：必须能构造实际的注入攻击
2. **影响评估**：明确注入后可能的安全后果
3. **数据流追踪**：完整的从外部数据到LLM的路径
4. **绕过机制**：具体的安全控制绕过方式

## 输入数据
源代码路径: %s
目录结构:
-------
%s
-------

## 输出要求
仅在发现确凿的间接提示词注入漏洞时输出：
- 具体文件路径和行号
- 完整的漏洞代码片段
- 数据流分析：从外部数据源到LLM输入的路径
- 攻击向量：具体的注入方式和载荷构造
- 技术分析：漏洞原理和利用机制
- 影响评估：可能的安全后果和风险等级
- 修复建议：具体的安全加固方案

**严格要求：必须提供完整的攻击路径和影响分析，无确凿证据时保持静默。**
`

// 执行检测
func (p *ResourcePoisoningPlugin) Check(ctx context.Context, config *McpPluginConfig) ([]Issue, error) {
	var issues []Issue

	// 使用列出目录内容
	dirPrompt, err := utils.ListDir(config.CodePath, 2, "")
	if err != nil {
		config.Logger.WithError(err).Errorln("读取目录失败: " + config.CodePath)
		return issues, err
	}

	// 使用AI分析潜在的资源投毒风险
	agent := utils.NewAutoGPT([]string{
		fmt.Sprintf(indirectPromptInjectionAIPrompt, config.CodePath, dirPrompt),
	}, config.Language, config.CodePath)

	_, err = agent.Run(ctx, config.AIModel, config.Logger)
	if err != nil {
		config.Logger.WithError(err).Warningln("")
		return issues, err
	}
	return SummaryResult(ctx, agent, config)
}
