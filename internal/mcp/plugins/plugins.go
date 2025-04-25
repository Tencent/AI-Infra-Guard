package plugins

import (
	"context"
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
	Name string
	Desc string
	ID   string
}

// Issue 安全问题
type Issue struct {
	Title       string `json:"title"`
	Description string `json:"description"`
	Level       Level  `json:"level"`
	Suggestion  string `json:"suggestion"`
}

type McpInput struct {
	Input string
	Type  MCPType // 输入类型：命令行、SSE链接、Stream链接、MCP代码
}

type McpPluginConfig struct {
	Client   *client.Client
	CodePath string
	AIModel  *models.OpenAI
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
		blockRegex  = regexp.MustCompile(`(?s)<result>(.*?)</result>`)
		titleRegex  = regexp.MustCompile(`<title>(.*?)</title>`)
		descRegex   = regexp.MustCompile(`(?s)<desc>(.*?)</desc>`)
		levelRegex  = regexp.MustCompile(`<level>(.*?)</level>`)
		suggesRegex = regexp.MustCompile(`(?s)<suggestion>(.*?)</suggestion>`)
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
		vulns = append(vulns, vuln)
	}
	return vulns
}
func SummaryResult(ctx context.Context, agent *utils.AutoGPT, model *models.OpenAI) ([]Issue, error) {
	history := agent.GetHistory()
	const summaryPrompt = `
The task is now complete, and the final vulnerability scan results must be returned. All valid results must be wrapped in <arg> tags (e.g., <arg>[RESULTS]</arg>). If no vulnerabilities are found, return <arg></arg>.  
Multiple <result> entries are supported, but only vulnerabilities with severity levels critical, high, or medium should be included.  

## EXAMPLE:  
<arg>
	<result>
	<title>Vulnerability Name</title>
	<desc>Detailed description in Markdown format, including code paths, file locations, code snippets, relevant context, and technical analysis (using professional terminology to explain the vulnerability's principle and potential impact).</desc>
	<level>Severity level (critical, high, medium)</level>
	<suggestion>Step-by-step remediation guidance</suggestion>
	</result>
	<!-- Additional <result> entries can be added -->
</arg>

If no vulnerabilities are detected, strictly return:  
<arg></arg>
`
	history = append(history, map[string]string{
		"role":    "user",
		"content": summaryPrompt,
	})
	var result string = ""
	gologger.Infoln("generate summary result")
	for word := range model.ChatStream(ctx, history) {
		result += word
		gologger.Print(word)
	}
	return ParseIssues(result), nil
}
