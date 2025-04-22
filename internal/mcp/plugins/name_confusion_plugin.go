package plugins

import (
	"context"
	"encoding/json"
	"fmt"
	"strings"

	"github.com/Tencent/AI-Infra-Guard/internal/gologger"
	"github.com/Tencent/AI-Infra-Guard/internal/mcp/models"
	"github.com/Tencent/AI-Infra-Guard/internal/mcp/utils"
)

// NameConfusionPlugin 名称混淆检测插件
type NameConfusionPlugin struct{}

// NewNameConfusionPlugin 创建新的名称混淆检测插件
func NewNameConfusionPlugin() *NameConfusionPlugin {
	return &NameConfusionPlugin{}
}

// 获取插件信息
func (p *NameConfusionPlugin) GetPlugin() Plugin {
	return Plugin{
		Name: "名称混淆检测",
		Desc: "检测MCP服务名称混淆与抢注风险",
	}
}

// AI提示词模板
const nameConfusionAIPrompt = `
分析以下MCP工具名称列表，检测可能存在的名称混淆和抢注攻击：

%s

需要重点检查：
1. 工具名称是否与官方或知名MCP服务名称高度相似
2. 工具名称是否具有误导性，可能导致用户或AI错误调用
3. 工具名称是否存在相互混淆的情况
4. 是否存在刻意模仿官方服务的命名模式
5. 工具名称是否包含敏感词或误导性词汇

对于每个潜在问题，提供：
- 问题类型（名称混淆/抢注/误导性命名）
- 严重程度（低/中/高/严重）
- 详细描述，包括可能导致的安全风险
- 修复建议
`

const nameConfusionResultPrompt = `以json格式返回检测结果，格式如下：
[
	{
		"title": "问题名称",
		"description": "问题详细描述，可以包含分析理由和风险说明",
		"level": "规则等级（low/medium/high/critical）",
		"suggestion": "修复建议",
	},
	...
]	
`

// 工具信息结构
type toolInfo struct {
	Name        string // 工具名称
	Description string // 工具描述
	Vendor      string // 供应商
}

// 执行检测
func (p *NameConfusionPlugin) Check(ctx context.Context, config *McpPluginConfig) ([]Issue, error) {
	var issues []Issue

	// 扫描所有工具名称
	gologger.Infoln("开始扫描目录：" + config.CodePath)
	tools, err := p.scanTools(config.CodePath)
	if err != nil {
		gologger.WithError(err).Errorln("扫描工具名称失败")
		return issues, err
	}

	gologger.Infoln(fmt.Sprintf("发现 %d 个工具", len(tools)))

	// 如果找到工具且AI模型可用，直接使用AI进行分析
	if len(tools) > 0 && config.AIModel != nil {
		// 构建AI分析的输入
		var toolsInfo strings.Builder
		for i, tool := range tools {
			toolsInfo.WriteString(fmt.Sprintf("%d. 工具名称: %s\n", i+1, tool.Name))
			if tool.Description != "" {
				toolsInfo.WriteString(fmt.Sprintf("   描述: %s\n", tool.Description))
			}
			if tool.Vendor != "" {
				toolsInfo.WriteString(fmt.Sprintf("   供应商: %s\n", tool.Vendor))
			}
			toolsInfo.WriteString("\n")
		}

		// 使用大模型进行名称混淆分析
		aiResults, err := p.aiAnalysis(ctx, toolsInfo.String(), config.AIModel)
		if err != nil {
			gologger.WithError(err).Warningln("AI分析失败")
			return nil, err
		}

		issues = append(issues, aiResults...)
	} else {
		gologger.Warningln("未找到工具或AI模型不可用，无法进行名称混淆检测")
	}

	return issues, nil
}

// 使用AI进行名称混淆分析
func (p *NameConfusionPlugin) aiAnalysis(ctx context.Context, toolsInfo string, aiModel models.AIModel) ([]Issue, error) {
	agent := utils.NewAutoGPT([]string{
		fmt.Sprintf(nameConfusionAIPrompt, toolsInfo),
	}, nameConfusionResultPrompt)

	result, err := agent.Run(ctx, aiModel)
	if err != nil {
		return nil, err
	}

	if result == "" {
		return nil, nil
	}

	var issues []Issue
	err = json.Unmarshal([]byte(result), &issues)
	if err != nil {
		return nil, err
	}

	return issues, nil
}
