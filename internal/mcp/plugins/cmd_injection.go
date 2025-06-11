package plugins

import (
	"context"
	"fmt"
	"os"
	"path/filepath"
	"regexp"
	"strings"

	"github.com/Tencent/AI-Infra-Guard/internal/mcp/utils"
)

// CmdInjectionPlugin 命令注入检测插件
type CmdInjectionPlugin struct {
	rules []cmdInjectionRule
}

// 命令注入检测规则
type cmdInjectionRule struct {
	Name        string
	Language    string
	Pattern     *regexp.Regexp
	Level       Level
	Description string
	Suggestion  string
}

// NewCmdInjectionPlugin 创建新的命令注入检测插件
func NewCmdInjectionPlugin() *CmdInjectionPlugin {
	return &CmdInjectionPlugin{
		rules: []cmdInjectionRule{
			// Python
			{
				Name:        "Python os.system 命令注入",
				Language:    "Python",
				Pattern:     regexp.MustCompile(`(?i)os\s*\.\s*system\s*\(`),
				Level:       LevelHigh,
				Description: "使用os.system()直接执行系统命令，可能导致命令注入",
				Suggestion:  "使用参数化命令执行，避免使用shell=True选项，过滤危险字符",
			},
			{
				Name:        "Python subprocess 命令注入",
				Language:    "Python",
				Pattern:     regexp.MustCompile(`(?i)(subprocess\s*\.\s*(Popen|call|run|check_output|check_call))`),
				Level:       LevelHigh,
				Description: "使用subprocess模块执行系统命令，可能导致命令注入",
				Suggestion:  "使用参数列表而非字符串传递命令，设置shell=False，过滤用户输入",
			},
			{
				Name:        "Python eval/exec 命令注入",
				Language:    "Python",
				Pattern:     regexp.MustCompile(`(?i)(eval|exec)\s*\(`),
				Level:       LevelCritical,
				Description: "使用eval()或exec()执行动态代码，可能导致代码注入",
				Suggestion:  "避免使用eval/exec，使用更安全的替代方案如ast.literal_eval()或json.loads()",
			},
			{
				Name:        "Python 模板注入",
				Language:    "Python",
				Pattern:     regexp.MustCompile(`(?i)(flask\.render_template_string|jinja2\.Template|django\.template\.Template)`),
				Level:       LevelHigh,
				Description: "使用模板字符串可能导致服务器端模板注入",
				Suggestion:  "不要将用户输入直接传递给模板引擎，对用户输入进行严格过滤",
			},

			// JavaScript
			{
				Name:        "Node.js 命令注入",
				Language:    "JavaScript",
				Pattern:     regexp.MustCompile(`(?i)(child_process|require\s*\(\s*['"]child_process['"]\s*\)).*?(exec|spawn|execSync|spawnSync)`),
				Level:       LevelHigh,
				Description: "使用child_process模块执行系统命令，可能导致命令注入",
				Suggestion:  "使用execFile或spawn并传递参数数组而非字符串，过滤用户输入",
			},
			{
				Name:        "JavaScript eval注入",
				Language:    "JavaScript",
				Pattern:     regexp.MustCompile(`(?i)(eval|new\s+Function|setTimeout|setInterval)\s*\(`),
				Level:       LevelCritical,
				Description: "使用eval()或Function构造函数执行动态代码，可能导致代码注入",
				Suggestion:  "避免使用eval和Function构造函数，使用更安全的替代方案如JSON.parse()",
			},

			// Java
			{
				Name:        "Java Runtime.exec 命令注入",
				Language:    "Java",
				Pattern:     regexp.MustCompile(`(?i)(Runtime\s*\.\s*getRuntime\s*\(\s*\)\s*\.\s*exec|ProcessBuilder)`),
				Level:       LevelHigh,
				Description: "使用Runtime.exec()或ProcessBuilder执行系统命令，可能导致命令注入",
				Suggestion:  "使用ProcessBuilder并传递命令数组而非字符串，过滤用户输入",
			},
			{
				Name:        "Java 反射代码注入",
				Language:    "Java",
				Pattern:     regexp.MustCompile(`(?i)(Class\.forName|loadClass|getMethod|invoke)`),
				Level:       LevelMedium,
				Description: "使用Java反射机制可能导致代码注入风险",
				Suggestion:  "限制可加载的类，实施严格的安全管理器策略，避免将用户输入传递给反射API",
			},
			{
				Name:        "Java 表达式注入",
				Language:    "Java",
				Pattern:     regexp.MustCompile(`(?i)(javax\.script\.ScriptEngine|Expression|SpelExpressionParser|groovy\.util\.Eval)`),
				Level:       LevelHigh,
				Description: "使用脚本引擎或表达式解析器可能导致代码注入",
				Suggestion:  "避免将用户输入传递给表达式解析器，使用参数化表达式，限制表达式执行环境",
			},

			// PHP
			{
				Name:        "PHP 命令注入",
				Language:    "PHP",
				Pattern:     regexp.MustCompile(`(?i)(system|exec|shell_exec|passthru|proc_open|popen)`),
				Level:       LevelCritical,
				Description: "使用PHP命令执行函数，可能导致命令注入",
				Suggestion:  "避免使用命令执行函数，使用escapeshellarg()和escapeshellcmd()过滤参数",
			},
			{
				Name:        "PHP 代码执行注入",
				Language:    "PHP",
				Pattern:     regexp.MustCompile(`(?i)(eval|assert|create_function|include|include_once|require|require_once|preg_replace.*\/e)`),
				Level:       LevelCritical,
				Description: "使用PHP代码执行函数可能导致代码注入",
				Suggestion:  "避免使用eval和动态代码执行函数，使用更安全的替代方案如json_decode()",
			},

			// Go
			{
				Name:        "Go exec.Command 命令注入",
				Language:    "Go",
				Pattern:     regexp.MustCompile(`(?i)(exec\s*\.\s*Command|os/exec)`),
				Level:       LevelMedium,
				Description: "使用exec.Command执行系统命令，可能导致命令注入",
				Suggestion:  "避免将用户输入直接传递给Command，使用固定的命令路径，分离命令和参数",
			},
			{
				Name:        "Go 模板注入",
				Language:    "Go",
				Pattern:     regexp.MustCompile(`(?i)(text/template|html/template).*?(\.\s*Parse|\.\s*ExecuteTemplate)`),
				Level:       LevelMedium,
				Description: "不当使用Go模板可能导致服务器端模板注入",
				Suggestion:  "使用html/template而非text/template处理HTML输出，不要将用户输入直接传递给模板引擎",
			},

			// Ruby
			{
				Name:        "Ruby 命令注入",
				Language:    "Ruby",
				Pattern:     regexp.MustCompile(`(?i)(\\` + "`" + `|\%x\{|\%x\(|system|exec|spawn|open\s*\(\s*\"|IO\.popen|Open3\.(popen|capture|pipeline))`),
				Level:       LevelHigh,
				Description: "使用Ruby命令执行函数可能导致命令注入",
				Suggestion:  "避免使用反引号执行命令，使用数组形式传递参数，过滤用户输入",
			},
			{
				Name:        "Ruby eval注入",
				Language:    "Ruby",
				Pattern:     regexp.MustCompile(`(?i)(eval|instance_eval|class_eval|module_eval|binding\.eval)`),
				Level:       LevelCritical,
				Description: "使用Ruby的eval函数执行动态代码，可能导致代码注入",
				Suggestion:  "避免使用eval函数，使用更安全的替代方案如JSON.parse",
			},

			// C/C++
			{
				Name:        "C/C++ 命令注入",
				Language:    "C/C++",
				Pattern:     regexp.MustCompile(`(?i)(system|popen|exec|execl|execlp|execle|execv|execvp|execvpe|spawn|ShellExecute)`),
				Level:       LevelHigh,
				Description: "使用C/C++命令执行函数可能导致命令注入",
				Suggestion:  "避免使用system函数，使用execv系列函数并传递参数数组，过滤用户输入",
			},

			// Perl
			{
				Name:        "Perl 命令注入",
				Language:    "Perl",
				Pattern:     regexp.MustCompile(`(?i)(\\` + "`" + `|\||\<\s*[\w\s\-\.]+\s*\>|system|exec|open\s*\(\s*[\"\'].*[\"\'].*\|)`),
				Level:       LevelHigh,
				Description: "使用Perl命令执行函数可能导致命令注入",
				Suggestion:  "避免使用反引号和system函数执行命令，使用参数化的system调用，过滤用户输入",
			},

			// C#
			{
				Name:        "C# 命令注入",
				Language:    "C#",
				Pattern:     regexp.MustCompile(`(?i)(Process\.Start|ProcessStartInfo|System\.Diagnostics\.Process)`),
				Level:       LevelHigh,
				Description: "使用C#进程启动函数可能导致命令注入",
				Suggestion:  "设置ProcessStartInfo.UseShellExecute为false，避免将用户输入直接传递给命令，过滤用户输入",
			},
			{
				Name:        "C# 动态代码执行",
				Language:    "C#",
				Pattern:     regexp.MustCompile(`(?i)(CSharpCodeProvider|CodeDomProvider|Assembly\.Load|Activator\.CreateInstance)`),
				Level:       LevelHigh,
				Description: "动态加载和执行代码可能导致代码注入",
				Suggestion:  "避免动态编译和执行用户提供的代码，使用沙箱环境限制执行权限",
			},
		},
	}
}

// 获取插件信息
func (p *CmdInjectionPlugin) GetPlugin() Plugin {
	return Plugin{
		Name:   "命令注入漏洞检测",
		Desc:   "检测MCP代码中可能存在的命令注入漏洞",
		ID:     "cmd_injection",
		NameEn: "Command Injection",
		DescEn: "Detect command injection vulnerabilities in MCP code",
	}
}

// AI提示词模板
const cmdInjectionAIPrompt = `
作为专业的网络安全分析专家，你需要对命令注入漏洞进行精确分析。此分析要求极高准确性，只有确认存在真实可利用的命令注入风险才能报告。

## 分析目标
基于静态代码分析的初步发现，进行深度的命令注入漏洞验证和误报过滤。

## 漏洞确认标准（必须同时满足）

### 1. 用户输入可控性
**必须确认以下条件：**
- 存在外部用户可控的输入源（HTTP参数、文件内容、环境变量等）
- 用户输入能够影响命令执行的参数或路径
- 输入验证机制缺失或可绕过
- 能够构造恶意载荷进行攻击

### 2. 危险函数调用链
**必须识别完整的调用链：**
- 从用户输入点到危险函数的完整数据流
- 确认危险函数确实会执行系统命令
- 验证命令构造方式和执行环境
- 排除安全的API调用模式

### 3. 安全防护缺失
**必须验证防护不足：**
- 输入过滤机制缺失或不完善
- 参数化查询或安全API未使用
- 命令执行环境缺少必要限制
- 错误处理可能泄露系统信息

## 技术分析要点

### 高危模式确认
**Python命令注入：**
- os.system() + 字符串拼接用户输入
- subprocess.* + shell=True + 用户输入
- eval()/exec() + 外部数据

**JavaScript命令注入：**
- child_process.exec() + 用户输入拼接
- eval() + 外部可控字符串
- Function构造器 + 动态代码

**其他语言类似模式**

### 安全实现识别
**以下情况不报告：**
- 使用参数化命令执行（execFile、spawn with array）
- 严格的输入白名单验证
- 命令路径固定且参数安全处理
- 在沙箱环境中执行

## 误报过滤规则

### 测试和开发代码
- 单元测试中的mock执行
- 开发工具和构建脚本
- 示例代码和文档片段
- 调试和日志记录功能

### 安全的代码模式
- 参数数组而非字符串拼接
- 使用官方SDK的标准API
- 实施了充分输入验证的代码
- 命令白名单和路径限制

### 特殊环境考虑
- 容器化环境的权限限制
- 只读文件系统的执行限制
- 网络隔离环境的影响
- 用户权限的实际限制

## 风险评估标准

### Critical级别
- 外部用户可直接控制命令执行
- 能够执行任意系统命令
- 可获取系统敏感信息或权限提升
- 无有效防护措施

### High级别  
- 用户输入影响命令参数
- 存在一定的利用限制
- 可能导致信息泄露或系统影响
- 防护措施不完善

### Medium级别
- 利用条件较为苛刻
- 影响范围相对有限
- 需要特定环境或权限
- 存在部分防护措施

## 分析输入数据
源代码路径: %s
静态扫描发现的潜在问题:
%s

## 输出要求
仅在确认存在真实命令注入威胁时输出：
- 具体文件路径和行号范围
- 完整的漏洞代码上下文
- 数据流分析：从输入源到命令执行的路径
- 漏洞原理：详细的技术分析和利用方式
- 影响评估：可能的攻击后果和影响范围
- POC构造：具体的攻击载荷示例（如适用）
- 修复建议：具体的代码修改方案

**关键要求：必须提供完整的攻击路径分析和实际危害评估，仅在确认存在真实威胁时输出结果。**
`

// GetLocation 根据起始位置和间隔行数获取文件的行位置
func GetLocation(content string, startPos, endPos, context_lines int) (string, string) {
	lines := strings.Split(content, "\n")

	// 找到起始和结束位置对应的行号
	startLine := 0
	currentPos := 0

	for i, line := range lines {
		lineLength := len(line) + 1 // +1 for newline character
		if currentPos <= startPos && startPos < currentPos+lineLength {
			startLine = i
			break
		}
		currentPos += lineLength
	}

	// 计算上下文的起始和结束行
	contextStart := startLine - context_lines
	if contextStart < 0 {
		contextStart = 0
	}

	contextEnd := startLine + context_lines
	if contextEnd >= len(lines) {
		contextEnd = len(lines) - 1
	}

	// 构建上下文代码
	var contextCode strings.Builder
	for i := contextStart; i <= contextEnd; i++ {
		prefix := "  "
		if i == startLine {
			prefix = "> "
		}
		contextCode.WriteString(fmt.Sprintf("%s%d: %s\n", prefix, i+1, lines[i]))
	}

	return fmt.Sprintf("第%d行", startLine+1), contextCode.String()
}

// 检查单个文件中的命令注入漏洞
func (p *CmdInjectionPlugin) checkFile(filePath string, contextLines int) ([]Issue, error) {
	var issues []Issue

	// 读取文件内容
	content, err := os.ReadFile(filePath)
	if err != nil {
		return nil, err
	}

	fileContent := string(content)
	fileExt := filepath.Ext(filePath)

	// 根据文件扩展名过滤规则
	var applicableRules []cmdInjectionRule
	for _, rule := range p.rules {
		switch rule.Language {
		case "Python":
			if fileExt == ".py" {
				applicableRules = append(applicableRules, rule)
			}
		case "JavaScript":
			if fileExt == ".js" || fileExt == ".ts" || fileExt == ".jsx" || fileExt == ".tsx" {
				applicableRules = append(applicableRules, rule)
			}
		case "Java":
			if fileExt == ".java" {
				applicableRules = append(applicableRules, rule)
			}
		case "PHP":
			if fileExt == ".php" {
				applicableRules = append(applicableRules, rule)
			}
		case "Go":
			if fileExt == ".go" {
				applicableRules = append(applicableRules, rule)
			}
		}
	}

	// 对每条规则进行匹配
	for _, rule := range applicableRules {
		matches := rule.Pattern.FindAllStringIndex(fileContent, -1)
		for _, match := range matches {
			startPos := match[0]
			endPos := match[1]

			// 获取匹配位置和上下文
			location, contextCode := GetLocation(fileContent, startPos, endPos, contextLines)

			description := fmt.Sprintf("代码上下文:\n```\n%s```", contextCode)

			issue := Issue{
				Title:       fmt.Sprintf("[%s] 疑似%s 在 %s (%s)", rule.Language, rule.Name, filepath.Base(filePath), location),
				Description: description,
			}

			issues = append(issues, issue)
		}
	}

	return issues, nil
}

// 递归扫描目录中的文件
func (p *CmdInjectionPlugin) scanDirectory(dirPath string, contextLines int) ([]Issue, error) {
	var allIssues []Issue

	err := filepath.Walk(dirPath, func(path string, info os.FileInfo, err error) error {
		if err != nil {
			return err
		}

		// 跳过目录和隐藏文件
		if info.IsDir() || strings.HasPrefix(filepath.Base(path), ".") {
			return nil
		}

		// 根据文件扩展名过滤
		ext := filepath.Ext(path)
		if ext == ".py" || ext == ".js" || ext == ".java" || ext == ".php" || ext == ".go" ||
			ext == ".ts" || ext == ".jsx" || ext == ".tsx" {
			issues, err := p.checkFile(path, contextLines)
			if err != nil {
				return err
			}
			allIssues = append(allIssues, issues...)
		}

		return nil
	})

	return allIssues, err
}

// 使用AI进行深度分析
func (p *CmdInjectionPlugin) aiAnalysis(ctx context.Context, issues []Issue, config *McpPluginConfig) ([]Issue, error) {
	if len(issues) == 0 {
		return nil, nil
	}

	// 构建AI分析的输入
	var sb strings.Builder
	for _, issue := range issues {
		sb.WriteString(fmt.Sprintf("%s\n", issue.Title))
		sb.WriteString(fmt.Sprintf("描述: %s\n\n", issue.Description))
	}

	agent := utils.NewAutoGPT([]string{
		fmt.Sprintf(cmdInjectionAIPrompt, config.CodePath, sb.String()),
	}, config.Language, config.CodePath)

	_, err := agent.Run(ctx, config.AIModel, config.Logger)
	if err != nil {
		config.Logger.WithError(err).Warningln("AI分析失败")
		return nil, err
	}

	return SummaryResult(ctx, agent, config)
}

// 执行检测
func (p *CmdInjectionPlugin) Check(ctx context.Context, config *McpPluginConfig) ([]Issue, error) {
	// 初始规则检测
	config.Logger.Infoln("开始检测命令注入漏洞...")
	issues, err := p.scanDirectory(config.CodePath, 3) // 默认上下文为3行
	if err != nil {
		config.Logger.WithError(err).Errorln("扫描目录失败: " + config.CodePath)
		return issues, err
	}

	config.Logger.Infoln(fmt.Sprintf("初步检测完成，发现 %d 个潜在问题", len(issues)))
	// 使用AI进行深度分析
	if len(issues) > 0 && config.AIModel != nil {
		config.Logger.Infoln("正在使用AI进行深度分析...")
		return p.aiAnalysis(ctx, issues, config)
	}

	return issues, nil
}
