package plugins

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"github.com/Tencent/AI-Infra-Guard/internal/gologger"
	"github.com/Tencent/AI-Infra-Guard/internal/mcp/utils"
	"strings"
)

// NameConfusionPlugin 名称混淆检测插件
type NameConfusionPlugin struct{}

// NewNameConfusionPlugin 创建新的名称混淆检测插件
func NewNameConfusionPlugin() *NameConfusionPlugin {
	return &NameConfusionPlugin{}
}

// GetPlugin 获取插件信息
func (p *NameConfusionPlugin) GetPlugin() Plugin {
	return Plugin{
		Name: "名称混淆检测",
		Desc: "检测MCP服务名称混淆与抢注风险",
		ID:   "name_confusion",
	}
}

// AI提示词模板
const nameConfusionAIPrompt = `
分析以下MCP工具名称列表，检测可能存在的名称混淆和抢注攻击：

%s

文件夹路径: %s
需要重点检查：
1. 工具名称是否与官方或知名MCP服务名称高度相似,如read_file exec_cmd之类
2. 工具名称是否具有误导性，可能导致用户或AI错误调用
3. 工具名称是否存在相互混淆的情况
4. 是否存在刻意模仿官方服务的命名模式
5. 工具名称是否包含敏感词或误导性词汇

对于每个潜在问题，提供：
- 问题类型（名称混淆/抢注/误导性命名）
- 严重程度（低/中/高/严重）
- 详细描述，包括可能导致的安全风险,按风险解释、问题代码输出markdown描述
- 修复建议
`

// Check 执行检测
func (p *NameConfusionPlugin) Check(ctx context.Context, config *McpPluginConfig) ([]Issue, error) {
	var issues []Issue
	if config.Client == nil {
		return issues, errors.New("client未初始化")
	}
	// 扫描所有工具名称
	tools, err := utils.ListMcpTools(ctx, config.Client)
	if err != nil {
		gologger.WithError(err).Errorln("扫描工具名称失败")
		return issues, err
	}

	gologger.Infoln(fmt.Sprintf("发现 %d 个工具", len(tools.Tools)))

	// 如果找到工具且AI模型可用，直接使用AI进行分析
	if len(tools.Tools) > 0 && config.AIModel != nil {
		// 构建AI分析的输入
		var toolsInfo strings.Builder
		for i, tool := range tools.Tools {
			toolsInfo.WriteString(fmt.Sprintf("%d. 工具名称: %s\n", i+1, tool.Name))
			if tool.Description != "" {
				toolsInfo.WriteString(fmt.Sprintf("   描述: %s\n", tool.Description))
			}
			inputSchema, _ := json.Marshal(tool.InputSchema)
			toolsInfo.WriteString(fmt.Sprintf("   参数InputSchema: %s\n", string(inputSchema)))
			toolsInfo.WriteString("\n")
		}

		// 使用大模型进行名称混淆分析
		agent := utils.NewAutoGPT([]string{
			fmt.Sprintf(nameConfusionAIPrompt, toolsInfo, config.CodePath),
		})

		_, err := agent.Run(ctx, config.AIModel)
		if err != nil {
			return nil, err
		}
		return SummaryResult(ctx, agent, config.AIModel, config.SaveHistory)
	} else {
		gologger.Warningln("未找到工具或AI模型不可用，无法进行名称混淆检测")
	}

	return issues, nil
}
