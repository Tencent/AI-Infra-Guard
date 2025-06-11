package plugins

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"strings"

	"github.com/Tencent/AI-Infra-Guard/internal/mcp/utils"
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
		Name:   "名称混淆检测",
		Desc:   "检测MCP服务名称混淆与抢注风险",
		ID:     "name_confusion",
		NameEn: "Name Confusion Detection",
		DescEn: "Detect name confusion and registration risks for MCP services",
	}
}

// AI提示词模板
const nameConfusionAIPrompt = `
作为专业的网络安全分析专家，你需要精确检测MCP代码中的名称混淆攻击漏洞。此检测要求极高精度，只有发现确凿的恶意名称混淆才能报告。

## 漏洞定义
名称混淆攻击是指恶意MCP工具使用与知名或可信工具相似的名称，误导用户或系统，以获得不当的信任和权限。

## 检测标准（必须同时满足）

### 1. 相似名称识别
**必须确认：**
- 工具名称与知名MCP工具高度相似
- 使用视觉相似字符进行欺骗（如0/O、1/l、rn/m）
- 域名或包名的拼写劫持（typosquatting）
- 大小写变化或字符替换的恶意使用

### 2. 恶意意图确认
**必须验证：**
- 工具功能与名称暗示的功能不符
- 存在明确的欺骗或误导行为
- 试图冒充合法工具获取权限
- 包含恶意功能而非声称的合法功能

### 3. 实际危害评估
**必须证明：**
- 能够成功欺骗用户或系统
- 获得超出预期的权限或信任
- 可能导致数据泄露或系统入侵
- 存在明确的安全风险

## 技术检测模式

### 名称相似性分析
**高风险模式：**
- 知名工具名称的变体：file-manager → file_manager、filemanager
- 字符替换攻击：google → g00gle、microsoft → microsft
- 添加前缀后缀：npm → npm-secure、git → git-plus
- 域名拼写劫持：github → githubcom、docker → dockerhub

### 功能不匹配检测
**欺骗模式：**
- 名称暗示安全工具但实际为恶意软件
- 声称为官方工具但实现不同功能
- 使用权威机构名称但非官方发布
- 模仿系统工具进行权限提升

### 品牌冒充识别
**冒充模式：**
- 使用知名公司或组织的名称
- 模仿官方工具的图标和描述
- 声称与知名项目有关联
- 使用误导性的版权或许可声明

## 排除条件（以下不报告）

### 合法的相似命名
- 合理的功能性命名惯例
- 同一开发者的工具系列
- 官方认可的衍生工具
- 行业标准的命名模式

### 正当的功能实现
- 提供真实声称的功能
- 开源透明的代码实现
- 清楚标注的非官方工具
- 合理的功能扩展或改进

### 开发和测试场景
- 开发环境的测试工具
- 学习项目的练习实现
- 概念验证的demo工具
- 明确标注的实验性项目

## 验证要求
1. **相似度评估**：量化名称相似度和混淆可能性
2. **功能对比**：分析声称功能与实际实现的差异
3. **欺骗效果**：评估对用户或系统的误导程度
4. **危害分析**：明确潜在的安全风险和影响

## 知名工具参考列表
**需要特别关注的知名工具：**
- 系统工具：ls、cat、grep、find、git、npm、pip
- 安全工具：nmap、wireshark、metasploit、burp
- 开发工具：docker、kubernetes、jenkins、travis
- 云服务：aws、azure、gcloud、terraform

## 输入数据
源代码路径: %s
目录结构:
-------
%s
-------

## 输出要求
仅在发现确凿的名称混淆攻击时输出：
- 混淆的工具名称和目标工具
- 具体的相似性分析和混淆技术
- 功能对比：声称功能 vs 实际功能
- 欺骗机制：如何误导用户或系统
- 潜在危害：可能的攻击后果
- 证据分析：完整的恶意意图证据

**严格要求：必须提供明确的恶意意图证据和实际危害评估，无确凿证据时保持静默。**
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
		config.Logger.WithError(err).Errorln("扫描工具名称失败")
		return issues, err
	}

	config.Logger.Infoln(fmt.Sprintf("发现 %d 个工具", len(tools.Tools)))

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
			fmt.Sprintf(nameConfusionAIPrompt, config.CodePath, toolsInfo.String()),
		}, config.Language, config.CodePath)

		_, err := agent.Run(ctx, config.AIModel, config.Logger)
		if err != nil {
			return nil, err
		}
		return SummaryResult(ctx, agent, config)
	} else {
		config.Logger.Warningln("未找到工具或AI模型不可用，无法进行名称混淆检测")
	}

	return issues, nil
}
