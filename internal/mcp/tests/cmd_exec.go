package tests

import (
	"context"
	"github.com/Tencent/AI-Infra-Guard/internal/mcp/plugins"
	"github.com/mark3labs/mcp-go/client"
	"regexp"
	"strconv"
	"strings"
)

// 命令执行检测插件
type CmdExecPlugin struct {
	rules []cmdExecRule
}

// 命令执行检测规则
type cmdExecRule struct {
	Name        string
	Language    string
	Pattern     *regexp.Regexp
	Level       plugins.Level
	Description string
	Suggestion  string
}

// 创建新的命令执行检测插件
func NewCmdExecPlugin() *CmdExecPlugin {
	return &CmdExecPlugin{
		rules: []cmdExecRule{
			// Python
			{
				Name:        "Python os.system 命令执行",
				Language:    "Python",
				Pattern:     regexp.MustCompile(`(?i)os\s*\.\s*system\s*\(`),
				Level:       plugins.LevelHigh,
				Description: "使用os.system()直接执行系统命令，可能导致命令注入",
				Suggestion:  "使用参数化命令执行，避免使用shell=True选项，过滤危险字符",
			},
			{
				Name:        "Python subprocess 命令执行",
				Language:    "Python",
				Pattern:     regexp.MustCompile(`(?i)(subprocess\s*\.\s*(Popen|call|run|check_output|check_call))`),
				Level:       plugins.LevelHigh,
				Description: "使用subprocess模块执行系统命令，可能导致命令注入",
				Suggestion:  "使用参数列表而非字符串传递命令，设置shell=False，过滤用户输入",
			},
			{
				Name:        "Python eval/exec 代码执行",
				Language:    "Python",
				Pattern:     regexp.MustCompile(`(?i)(eval|exec)\s*\(`),
				Level:       plugins.LevelCritical,
				Description: "使用eval()或exec()执行动态代码，极易导致代码注入",
				Suggestion:  "避免使用eval/exec，使用更安全的替代方法如ast.literal_eval()或json.loads()",
			},

			// JavaScript
			{
				Name:        "JavaScript eval 代码执行",
				Language:    "JavaScript",
				Pattern:     regexp.MustCompile(`(?i)(eval|Function|setTimeout|setInterval)\s*\(`),
				Level:       plugins.LevelCritical,
				Description: "使用eval()或Function构造函数执行动态代码，可能导致代码注入",
				Suggestion:  "避免使用eval和Function构造函数，使用JSON.parse()处理JSON数据",
			},
			{
				Name:        "Node.js 命令执行",
				Language:    "JavaScript",
				Pattern:     regexp.MustCompile(`(?i)(child_process|require\s*\(\s*['"]child_process['"]\s*\)).*?(exec|spawn|execSync|spawnSync)`),
				Level:       plugins.LevelHigh,
				Description: "使用child_process模块执行系统命令，可能导致命令注入",
				Suggestion:  "使用execFile或spawn并传递参数数组而非字符串，过滤用户输入",
			},

			// Java
			{
				Name:        "Java Runtime.exec 命令执行",
				Language:    "Java",
				Pattern:     regexp.MustCompile(`(?i)(Runtime\s*\.\s*getRuntime\s*\(\s*\)\s*\.\s*exec|ProcessBuilder)`),
				Level:       plugins.LevelHigh,
				Description: "使用Runtime.exec()或ProcessBuilder执行系统命令，可能导致命令注入",
				Suggestion:  "使用ProcessBuilder并传递命令数组而非字符串，过滤用户输入",
			},

			// PHP
			{
				Name:        "PHP 命令执行",
				Language:    "PHP",
				Pattern:     regexp.MustCompile(`(?i)(system|exec|shell_exec|passthru|proc_open|popen)`),
				Level:       plugins.LevelCritical,
				Description: "使用PHP命令执行函数，可能导致命令注入",
				Suggestion:  "避免使用命令执行函数，使用escapeshellarg()和escapeshellcmd()过滤参数",
			},

			// Go
			{
				Name:        "Go exec.Command 命令执行",
				Language:    "Go",
				Pattern:     regexp.MustCompile(`(?i)(exec\s*\.\s*Command|os/exec)`),
				Level:       plugins.LevelMedium,
				Description: "使用exec.Command执行系统命令，可能导致命令注入",
				Suggestion:  "避免将用户输入直接传递给Command，使用固定的命令路径，分离命令和参数",
			},

			// 命令链接字符
			{
				Name:        "命令链接字符检测",
				Language:    "通用",
				Pattern:     regexp.MustCompile(`(;|\$\(|\$\{|\|\||&&|>|<|\|)`),
				Level:       plugins.LevelHigh,
				Description: "发现命令链接字符，可能被用于绕过命令执行限制",
				Suggestion:  "过滤命令链接字符，使用白名单验证输入内容",
			},

			// 沙箱和权限控制
			{
				Name:        "权限提升检测",
				Language:    "通用",
				Pattern:     regexp.MustCompile(`(?i)(sudo|su\s+|chmod\s+777|chown|setuid|setgid)`),
				Level:       plugins.LevelCritical,
				Description: "发现可能用于权限提升的命令",
				Suggestion:  "限制执行环境权限，使用最小权限原则",
			},

			// 文件系统操作
			{
				Name:        "危险文件操作",
				Language:    "通用",
				Pattern:     regexp.MustCompile(`(?i)(rm\s+-rf|unlink\s+|/etc/passwd|/etc/shadow|/etc/hosts)`),
				Level:       plugins.LevelCritical,
				Description: "发现危险的文件系统操作",
				Suggestion:  "限制文件系统访问权限，使用白名单验证文件路径",
			},
		},
	}
}

// 获取插件信息
func (p *CmdExecPlugin) GetPlugin() plugins.Plugin {
	return plugins.Plugin{
		Name: "命令执行漏洞检测",
		Desc: "检测MCP代码中可能存在的命令执行漏洞",
	}
}

// 执行检测
func (p *CmdExecPlugin) Check(ctx context.Context, config *plugins.McpPluginConfig) ([]plugins.Issue, error) {
	var issues []plugins.Issue

	// 对每个输入进行检测
	for _, input := range inputs {
		// 可以检测所有类型的输入
		issues = append(issues, p.checkInput(input)...)
	}

	return issues, nil
}

// 检测输入中的命令执行问题
func (p *CmdExecPlugin) checkInput(ctx context.Context, client *client.Client, codePath string) []plugins.Issue {
	var issues []plugins.Issue

	for _, rule := range p.rules {
		matches := rule.Pattern.FindAllStringIndex(input.Input, -1)
		for _, match := range matches {
			startPos := match[0]
			endPos := match[1]

			// 获取匹配上下文
			start := startPos - 20
			if start < 0 {
				start = 0
			}
			end := endPos + 20
			if end > len(input.Input) {
				end = len(input.Input)
			}

			location := ""
			if strings.Count(input.Input[:startPos], "\n") > 0 {
				line := strings.Count(input.Input[:startPos], "\n") + 1
				location = "第" + strconv.Itoa(line) + "行"
			} else {
				location = "字符位置: " + strconv.Itoa(startPos) + "-" + strconv.Itoa(endPos)
			}

			issue := plugins.Issue{
				Title:       "[" + rule.Language + "] " + rule.Name,
				Description: rule.Description,
				Level:       rule.Level,
				Suggestion:  rule.Suggestion,
				Input:       location,
				Type:        input.Type,
			}

			issues = append(issues, issue)
		}
	}

	return issues
}

// AI验证提示词模板
const cmdExecAIPrompt = `
分析以下MCP工具代码或描述，检测可能存在的命令执行漏洞：

%s

需要重点检查：
1. 是否直接执行系统命令或代码
2. 是否存在未经过滤的用户输入被传递给执行函数
3. 是否存在命令链接字符(如 &&, ;, |, $(), ${})被用于绕过限制
4. 执行环境是否有足够的沙箱控制和权限限制
5. 是否有文件系统访问权限控制
6. 是否存在权限提升风险

对于每个潜在的命令执行漏洞，提供：
- 漏洞类型
- 严重程度(低/中/高/严重)
- 详细描述，包括可能的利用方式
- 漏洞所在位置
- 修复建议，包括具体的代码改进方法
- 最小权限原则实施建议

特别关注危险函数和方法:
- Python: os.system, subprocess.*, eval, exec
- JavaScript: eval, Function, setTimeout接收字符串, child_process.exec
- Java: Runtime.exec, ProcessBuilder
- PHP: system, exec, shell_exec, passthru
- Go: exec.Command, os/exec
`
