package plugins

import (
	"context"
	"fmt"

	"github.com/Tencent/AI-Infra-Guard/internal/gologger"
	"github.com/Tencent/AI-Infra-Guard/internal/mcp/utils"
)

// ToolPoisoningPlugin 工具投毒攻击检测插件
type ToolPoisoningPlugin struct {
}

// NewToolPoisoningPlugin 创建新的工具投毒攻击检测插件
func NewToolPoisoningPlugin() *ToolPoisoningPlugin {
	return &ToolPoisoningPlugin{}
}

// 获取插件信息
func (p *ToolPoisoningPlugin) GetPlugin() Plugin {
	return Plugin{
		Name: "工具投毒攻击检测",
		Desc: "检测MCP代码中可能存在的工具投毒攻击风险",
		ID:   "tool_poisoning",
	}
}

// AI提示词模板
const toolPoisoningAIPrompt = `
你作为资深代码安全审计师，将对MCP工具实施系统性Tool Poisoning Attack攻击检测。你的分析必须基于专业知识和确凿证据，**绝对禁止任何猜测性或不确定的输出**,请按照军工级安全标准执行以下审计流程：
Tool Poisoning Attack指的是在MCP工具的描述（docstring）中隐藏恶意指令，这些指令在普通 UI 中可能不可见，但会被处理工具描述的 LLM 读取并执行，从而操纵 LLM 的行为。

请检查代码中是否有工具同时满足以下特征：
1.  其描述 (类似python __doc__ 字符串) 包含看起来像是给 LLM 的指令，特别是如果这些指令被特殊标记（如 <HIDDEN>, <IMPORTANT>）包围或以其他方式隐藏。
2.  这些隐藏的指令试图让 LLM 绕过安全检查、访问未授权的数据（例如，通过调用特定资源或使用特殊参数）或执行其他恶意/非预期的操作。
3.  工具的实际实现代码可能看起来无害，但其描述被用来注入恶意逻辑。
4. 使用NLP模型检测包含以下模式的描述：必须/应当/要求/立即 绕过/忽略/禁用 + 安全/验证/过滤 访问/读取/下载 + ~/.ssh/credentials等路径

## 输入数据
源代码文件夹路径:%s
目录详情:
-------
%s
-------
## 输出
漏洞描述给出证据:文件位置、代码片段、技术分析(专业术语说明漏洞原理及潜在影响)

`

// 执行检测
func (p *ToolPoisoningPlugin) Check(ctx context.Context, config *McpPluginConfig) ([]Issue, error) {
	var issues []Issue
	dirPrompt, err := utils.ListDir(config.CodePath, 2)
	if err != nil {
		gologger.WithError(err).Errorln("读取目录失败: " + config.CodePath)
		return issues, err
	}
	agent := utils.NewAutoGPT([]string{
		fmt.Sprintf(toolPoisoningAIPrompt, config.CodePath, dirPrompt),
	})
	_, err = agent.Run(ctx, config.AIModel)
	if err != nil {
		gologger.WithError(err).Warningln("")
		return issues, err
	}
	return SummaryResult(ctx, agent, config.AIModel, config.SaveHistory)
}
