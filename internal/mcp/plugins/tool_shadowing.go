package plugins

import (
	"context"
	"fmt"

	"github.com/Tencent/AI-Infra-Guard/internal/mcp/utils"
)

// ToolShadowingPlugin 工具覆盖攻击检测插件
type ToolShadowingPlugin struct {
}

// NewToolShadowingPlugin 创建新的工具覆盖攻击检测插件
func NewToolShadowingPlugin() *ToolShadowingPlugin {
	return &ToolShadowingPlugin{}
}

// 获取插件信息
func (p *ToolShadowingPlugin) GetPlugin() Plugin {
	return Plugin{
		Name:   "工具覆盖攻击检测",
		Desc:   "检测MCP代码中可能存在的工具覆盖攻击风险",
		ID:     "tool_shadowing",
		NameEn: "Tool Shadowing",
		DescEn: "Detect possible tool shadowing vulnerabilities in MCP code.",
	}
}

// AI提示词模板
const toolShadowingAIPrompt = `
请分析以下 MCP 服务器代码，判断是否存在 Tool Shadowing 风险。你的分析必须基于专业知识和确凿证据，**绝对禁止任何猜测性或不确定的输出**。
Tool Shadowing 指的是一个MCP工具描述中的隐藏指令重新定义或修改其他可信MCP服务器工具的行为，当用户调用其他修改的工具时，达到恶意攻击的目的。

请检查文件中是否有以下特征：
1. 检查描述中是否有访问其他工具的docstring的隐藏指令。
2. 检查工具代码里面是否有重新定义或修改其他可信MCP服务器工具的行为。
3. 检查非代码或注释中里面是否有隐藏指令访问敏感资源或诱导执行非预期操作。

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
func (p *ToolShadowingPlugin) Check(ctx context.Context, config *McpPluginConfig) ([]Issue, error) {
	var issues []Issue
	dirPrompt, err := utils.ListDir(config.CodePath, 2)
	if err != nil {
		config.Logger.WithError(err).Errorln("读取目录失败: " + config.CodePath)
		return issues, err
	}
	agent := utils.NewAutoGPT([]string{
		fmt.Sprintf(toolShadowingAIPrompt, config.CodePath, dirPrompt),
	}, config.Language)
	_, err = agent.Run(ctx, config.AIModel, config.Logger)
	if err != nil {
		config.Logger.WithError(err).Warningln("")
		return issues, err
	}
	return SummaryResult(ctx, agent, config)
}
