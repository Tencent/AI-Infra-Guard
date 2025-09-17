package mcp

import (
	"context"
	"fmt"
	"os"
	"regexp"
	"strings"

	"github.com/Tencent/AI-Infra-Guard/common/utils/models"
	"github.com/Tencent/AI-Infra-Guard/internal/gologger"
	"github.com/Tencent/AI-Infra-Guard/internal/mcp/utils"
	"github.com/mark3labs/mcp-go/client"
	"gopkg.in/yaml.v3"
)

type PluginConfig struct {
	Info struct {
		ID          string   `yaml:"id" json:"id"`
		Name        string   `yaml:"name" json:"name"`
		Description string   `yaml:"description" json:"description"`
		Author      string   `yaml:"author" json:"author"`
		Category    []string `yaml:"categories" json:"category"`
	} `yaml:"info" json:"info"`
	Rules          []Rule `yaml:"rules,omitempty" json:"rules,omitempty"`
	PromptTemplate string `yaml:"prompt_template" json:"prompt_template"`
}

type Rule struct {
	Name        string `yaml:"name"`
	Pattern     string `yaml:"pattern"`
	Description string `yaml:"description"`
}

func NewYAMLPlugin(configPath string) (*PluginConfig, error) {
	data, err := os.ReadFile(configPath)
	if err != nil {
		return nil, err
	}

	var config PluginConfig
	err = yaml.Unmarshal(data, &config)
	if err != nil {
		return nil, err
	}

	return &config, nil
}

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
	Client       *client.Client
	CodePath     string
	McpStructure string
	AIModel      *models.OpenAI
	Language     string // zh / en
	Logger       *gologger.Logger
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
			if vuln.Description == "" {
				continue
			}
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

func SummaryResult(ctx context.Context, agent utils.Agent, config *McpPluginConfig) ([]Issue, error) {
	history := agent.GetHistory()
	const summaryPrompt = `
The task is now complete, and the discovered vulnerabilities are being returned.
**Return Format**
All valid results must be wrapped in <arg> tags (e.g., <arg>[RESULTS]</arg>). 
If no vulnerabilities are found, return <arg></arg>.  
Multiple <result> entries are supported, but only vulnerabilities with severity levels critical, high, or medium should be included.
**Rules**
1. You must ensure that the vulnerability truly exists. if no vulnerability is found, return empty.
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

**请注意,必须是漏洞输出详情，没有漏洞则只输出<arg></arg>**
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
	// 保存模型输出
	return ParseIssues(result), nil
}

func SummaryChat(ctx context.Context, agent utils.Agent, config *McpPluginConfig, prompt string) (string, error) {
	history := agent.GetHistory()
	history = append(history, map[string]string{
		"role":    "user",
		"content": fmt.Sprintf(prompt, utils.LanguagePrompt(config.Language)),
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
	// 保存模型输出
	return result, nil
}

func SummaryReport(ctx context.Context, agent utils.Agent, config *McpPluginConfig) (string, error) {
	prompt := `
You have performed a complete vulnerability scanning process on the target system but ultimately found no reportable vulnerabilities. Now, a brief technical analysis report explaining the reasons needs to be generated. Please output according to the following structure:

# Task Role  
Cybersecurity Analysis Report Writing Expert  

# Core Requirements  
1. Provide a structured explanation of the technical reasons why no vulnerabilities were found.  
2. Include an analysis of potential possibilities.  
3. Propose follow-up action recommendations.  
4. Use professional security terminology but avoid excessive jargon.  

# Report Framework (Markdown Format)  
- Rephrase the core objective of the scan.  
- Briefly describe the scanning process and the key components covered (files/interfaces/code scope).  
- Reasons why no vulnerabilities were found:  
  - Provide a detailed explanation of why no vulnerabilities were detected.  
  - Explain possible reasons.  
  - Discuss potential opportunities for vulnerability discovery.  

**Return Format**  
All valid results must be wrapped in <arg> tags (e.g., <arg>[RESULTS]</arg>).  
If no vulnerabilities are found, return <arg></arg>.  
Multiple <result> entries are supported, but only vulnerabilities with severity levels critical, high, or medium should be included.  

**EXAMPLE**  
<arg>  
	<result>  
	<title>No [Vulnerability Type] Found</title>  
	<desc>Technical analysis report content in Markdown format</desc>  
	</result>  
</arg>  

If none, return:  
<arg></arg>
`
	return SummaryChat(ctx, agent, config, prompt)
}
