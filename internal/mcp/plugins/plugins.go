package plugins

import (
	"context"
	"fmt"
	"github.com/Tencent/AI-Infra-Guard/internal/gologger"
	"github.com/Tencent/AI-Infra-Guard/internal/mcp/models"
	"github.com/Tencent/AI-Infra-Guard/internal/mcp/utils"
	"github.com/mark3labs/mcp-go/client"
	"regexp"
	"strings"
)

// 威胁级别常量
type Level string

const (
	LevelLow      Level = "low"
	LevelMedium   Level = "medium"
	LevelHigh     Level = "high"
	LevelCritical Level = "critical"
)

type MCPType string

const (
	MCPTypeCommand MCPType = "command"
	MCPTypeSSE     MCPType = "sse"
	MCPTypeSTREAM  MCPType = "stream"
	MCPTypeCode    MCPType = "code"
)

// Plugin MCP插件信息
type Plugin struct {
	Name   string `json:"name"`
	Desc   string `json:"desc"`
	NameEn string `json:"name_en"`
	DescEn string `json:"desc_en"`
	ID     string `json:"id"`
}

// Issue 安全问题
type Issue struct {
	Title       string `json:"title"`
	Description string `json:"description"`
	Level       Level  `json:"level"`
	Suggestion  string `json:"suggestion"`
	RiskType    string `json:"risk_type"`
}

type McpInput struct {
	Input string
	Type  MCPType // 输入类型：命令行、SSE链接、Stream链接、MCP代码
}

type McpPluginConfig struct {
	Client      *client.Client
	CodePath    string
	AIModel     *models.OpenAI
	SaveHistory bool
	Language    string // zh / en
	Logger      *gologger.Logger
}

type McpPlugin interface {
	GetPlugin() Plugin
	Check(ctx context.Context, config *McpPluginConfig) ([]Issue, error)
}

// ExtractBatchResults 从文本中提取结果
func ParseIssues(input string) []Issue {
	var vulns []Issue
	// 解析漏洞数据的正则表达式
	var (
		blockRegex    = regexp.MustCompile(`(?s)<result>(.*?)</result>`)
		titleRegex    = regexp.MustCompile(`<title>(.*?)</title>`)
		descRegex     = regexp.MustCompile(`(?s)<desc>(.*?)</desc>`)
		levelRegex    = regexp.MustCompile(`<level>(.*?)</level>`)
		riskTypeRegex = regexp.MustCompile(`<risk_type>(.*?)</risk_type>`)
		suggesRegex   = regexp.MustCompile(`(?s)<suggestion>(.*?)</suggestion>`)
	)
	blocks := blockRegex.FindAllStringSubmatch(input, -1)
	for _, block := range blocks {
		var vuln Issue
		// 提取各个字段
		if title := titleRegex.FindStringSubmatch(block[1]); len(title) > 1 {
			vuln.Title = strings.TrimSpace(title[1])
		}
		if desc := descRegex.FindStringSubmatch(block[1]); len(desc) > 1 {
			vuln.Description = strings.TrimSpace(desc[1])
		}
		if level := levelRegex.FindStringSubmatch(block[1]); len(level) > 1 {
			vuln.Level = Level(strings.TrimSpace(level[1]))
		}
		if sugges := suggesRegex.FindStringSubmatch(block[1]); len(sugges) > 1 {
			vuln.Suggestion = strings.TrimSpace(sugges[1])
		}
		if riskType := riskTypeRegex.FindStringSubmatch(block[1]); len(riskType) > 1 {
			vuln.RiskType = strings.TrimSpace(riskType[1])
		}
		vulns = append(vulns, vuln)
	}
	return vulns
}
func SummaryResult(ctx context.Context, agent *utils.AutoGPT, config *McpPluginConfig) ([]Issue, error) {
	history := agent.GetHistory()
	const summaryPrompt = `
The task is now complete, and the discovered vulnerabilities are being returned.
**Return Format**
All valid results must be wrapped in <arg> tags (e.g., <arg>[RESULTS]</arg>). 
If no vulnerabilities are found, return <arg></arg>.  
Multiple <result> entries are supported, but only vulnerabilities with severity levels critical, high, or medium should be included.
**Rules**
1. You must ensure that the vulnerability truly exists; if no vulnerability is found, return empty.
2. The desc field in the vulnerability description should include a detailed evidence chain for the vulnerability.
3. Determine the severity 'level'' of the vulnerability based on its title and description: critical, high, medium, low.
%s
**EXAMPLE**
1. if no vulnerabilities are found, return <arg></arg>.
2. if vulnerabilities are found, return:
<arg>
	<result>
	<title>Vulnerability Name</title>
	<desc>Detailed description in Markdown format, including code paths, file locations, code snippets, relevant context, and technical analysis (using professional terminology to explain the vulnerability's principle and potential impact).</desc>
	<risk_type>Vulnerability risk type</risk_type>
	<level>Severity level (critical, high, medium,low)</level>
	<suggestion>Step-by-step remediation guidance</suggestion>
	</result>
	<!-- Additional <result> entries can be added -->
</arg>
`
	history = append(history, map[string]string{
		"role":    "user",
		"content": fmt.Sprintf(summaryPrompt, utils.LanguagePrompt(config.Language)),
	})
	var result string = ""
	config.Logger.Infoln("generate summary result")
	for word := range config.AIModel.ChatStream(ctx, history) {
		result += word
		config.Logger.Print(word)
	}
	history = append(history, map[string]string{
		"role":    "assistant",
		"content": result,
	})
	if config.SaveHistory {
		err := utils.SaveHistory(history)
		if err != nil {
			config.Logger.Errorln("save history failed")
		}
	}
	// 保存模型输出
	return ParseIssues(result), nil
}
