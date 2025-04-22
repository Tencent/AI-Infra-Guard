package plugins

import (
	"context"
	"fmt"
	"github.com/mark3labs/mcp-go/client"
	"strings"
)

// 命名混淆检测插件
type NameConfusionPlugin struct {
	officialServices    []nameConfusionInfo
	similarityThreshold float64
}

// 命名混淆信息
type nameConfusionInfo struct {
	OfficialName   string
	OfficialVendor string
	Description    string
}

// 创建新的命名混淆检测插件
func NewNameConfusionPlugin() *NameConfusionPlugin {
	return &NameConfusionPlugin{
		officialServices: []nameConfusionInfo{
			{
				OfficialName:   "MCP.Translator",
				OfficialVendor: "AI-Infra-Guard",
				Description:    "官方翻译服务",
			},
			{
				OfficialName:   "MCP.CodeAnalyzer",
				OfficialVendor: "AI-Infra-Guard",
				Description:    "官方代码分析服务",
			},
			{
				OfficialName:   "MCP.ImageGenerator",
				OfficialVendor: "AI-Infra-Guard",
				Description:    "官方图像生成服务",
			},
			// 可根据实际官方服务添加更多
		},
		similarityThreshold: 0.8, // 相似度阈值
	}
}

// 获取插件信息
func (p *NameConfusionPlugin) GetPlugin() Plugin {
	return Plugin{
		Name: "命名混淆检测",
		Desc: "检测MCP服务名称混淆与抢注风险",
	}
}

// 执行检测
func (p *NameConfusionPlugin) Check(ctx context.Context, client *client.Client, codePath string) ([]Issue, error) {
	var issues []Issue

	// 构建服务信息
	for _, input := range inputs {
		// 解析输入中的服务信息
		serviceInfo := p.parseServiceInfo(input.Input)
		if serviceInfo.Name != "" {
			issues = append(issues, p.checkServiceName(serviceInfo)...)
		}
	}

	return issues, nil
}

// 从输入中解析服务信息（简化实现）
func (p *NameConfusionPlugin) parseServiceInfo(input string) mcpServiceInfo {
	// 此处简化实现，实际应该根据输入格式进行解析
	// 假设输入格式为：name:vendor:description
	parts := strings.Split(input, ":")

	result := mcpServiceInfo{
		Name:        "",
		Vendor:      "",
		Description: "",
	}

	if len(parts) >= 1 {
		result.Name = strings.TrimSpace(parts[0])
	}

	if len(parts) >= 2 {
		result.Vendor = strings.TrimSpace(parts[1])
	}

	if len(parts) >= 3 {
		result.Description = strings.TrimSpace(parts[2])
	}

	return result
}

// MCP服务信息结构
type mcpServiceInfo struct {
	Name        string
	Description string
	Vendor      string
}

// 检测服务名称混淆
func (p *NameConfusionPlugin) checkServiceName(serviceInfo mcpServiceInfo) []Issue {
	var issues []Issue

	// 获取所有官方供应商名单
	officialVendors := make([]string, 0)
	for _, service := range p.officialServices {
		if !sliceContains(officialVendors, service.OfficialVendor) {
			officialVendors = append(officialVendors, service.OfficialVendor)
		}
	}

	// 检查供应商是否可信
	if !p.isVendorTrusted(serviceInfo.Vendor, officialVendors) {
		issue := Issue{
			Title:       "非官方供应商",
			Description: fmt.Sprintf("服务供应商'%s'不在官方供应商列表中，可能存在安全风险", serviceInfo.Vendor),
			Level:       LevelMedium,
			Suggestion:  "建议使用官方供应商提供的MCP服务，或对第三方服务进行严格的安全审查",
			Input:       "服务元数据",
			Type:        MCPTypeCode,
		}
		issues = append(issues, issue)
	}

	// 检查名称混淆
	for _, officialService := range p.officialServices {
		if p.isPotentialNameConfusion(serviceInfo.Name, officialService, p.similarityThreshold) {
			issue := Issue{
				Title: "命名混淆风险",
				Description: fmt.Sprintf("服务名称'%s'与官方服务'%s'高度相似，可能导致AI错误调用",
					serviceInfo.Name, officialService.OfficialName),
				Level:      LevelHigh,
				Suggestion: "更改服务名称，避免与官方服务名称相似，或确认是否为官方服务的正式替代品",
				Input:      "服务名称",
				Type:       MCPTypeCode,
			}
			issues = append(issues, issue)
		}
	}

	// 检查名称与描述不匹配
	if len(serviceInfo.Description) < 10 {
		issue := Issue{
			Title:       "服务描述不充分",
			Description: "服务描述过于简短，难以判断服务真实功能",
			Level:       LevelLow,
			Suggestion:  "提供详细的服务功能描述，包括用途、权限和数据处理方式",
			Input:       "服务描述",
			Type:        MCPTypeCode,
		}
		issues = append(issues, issue)
	}

	return issues
}

// 检测服务提供商是否可信
func (p *NameConfusionPlugin) isVendorTrusted(vendor string, officialVendors []string) bool {
	for _, officialVendor := range officialVendors {
		if strings.EqualFold(vendor, officialVendor) {
			return true
		}
	}
	return false
}

// 判断是否为潜在的命名混淆
func (p *NameConfusionPlugin) isPotentialNameConfusion(name string, officialService nameConfusionInfo, similarityThreshold float64) bool {
	similarity := p.calculateNameSimilarity(name, officialService.OfficialName)
	return similarity >= similarityThreshold && similarity < 1.0
}

// 计算名称相似度 (0-1之间，1表示完全相同)
func (p *NameConfusionPlugin) calculateNameSimilarity(name1, name2 string) float64 {
	// 如果字符串长度为0，则相似度为0
	if len(name1) == 0 || len(name2) == 0 {
		return 0.0
	}

	// 计算编辑距离
	distance := p.levenshteinDistance(name1, name2)

	// 计算相似度
	maxLength := float64(max(len(name1), len(name2)))
	similarity := 1.0 - float64(distance)/maxLength

	return similarity
}

// 计算字符串编辑距离 (Levenshtein距离)
func (p *NameConfusionPlugin) levenshteinDistance(s1, s2 string) int {
	s1 = strings.ToLower(s1)
	s2 = strings.ToLower(s2)

	// 创建矩阵
	d := make([][]int, len(s1)+1)
	for i := range d {
		d[i] = make([]int, len(s2)+1)
	}

	// 初始化
	for i := range d {
		d[i][0] = i
	}
	for j := range d[0] {
		d[0][j] = j
	}

	// 填充矩阵
	for j := 1; j <= len(s2); j++ {
		for i := 1; i <= len(s1); i++ {
			if s1[i-1] == s2[j-1] {
				d[i][j] = d[i-1][j-1] // 字符相同，无需操作
			} else {
				min := d[i-1][j-1] // 替换
				if d[i][j-1] < min {
					min = d[i][j-1] // 插入
				}
				if d[i-1][j] < min {
					min = d[i-1][j] // 删除
				}
				d[i][j] = min + 1
			}
		}
	}

	return d[len(s1)][len(s2)]
}

// 检查切片是否包含指定元素
func sliceContains(slice []string, item string) bool {
	for _, a := range slice {
		if strings.EqualFold(a, item) {
			return true
		}
	}
	return false
}

// max返回两个整数中的较大值
func max(a, b int) int {
	if a > b {
		return a
	}
	return b
}

// AI提示词模板
const nameConfusionAIPrompt = `
分析以下MCP服务或工具的名称和描述，检测可能存在的命名混淆和抢注攻击：

服务名称: %s
服务描述: %s
服务提供商: %s

需要重点检查：
1. 名称是否与官方MCP服务名称相似，可能导致AI错误调用
2. 服务提供商是否为官方厂商，而非第三方开发者
3. 服务功能描述是否与服务名称匹配
4. 是否存在刻意模仿官方服务的行为

对于每个潜在问题，提供：
- 问题类型
- 严重程度(低/中/高/严重)
- 详细描述，包括可能导致的风险
- 修复建议
- 防御措施
`
