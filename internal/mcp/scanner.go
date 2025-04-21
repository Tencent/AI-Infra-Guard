package mcp

import (
	"context"
	"fmt"
	"regexp"
	"strings"
	"sync"
	"time"

	"github.com/Tencent/AI-Infra-Guard/internal/gologger"
	"github.com/Tencent/AI-Infra-Guard/internal/mcp/plugins"
)

// ScanResult 检测结果
type ScanResult struct {
	Timestamp time.Time
	Input     string
	Type      string // 输入类型：命令行、SSE链接、MCP代码
	Issues    []Issue
}

// Issue 安全问题
type Issue struct {
	Title       string
	Description string
	Level       string
	Location    string
	Suggestion  string
}

// 转换插件Issue到Scanner的Issue
func convertPluginIssue(pIssue plugins.Issue) Issue {
	return Issue{
		Title:       pIssue.Title,
		Description: pIssue.Description,
		Level:       string(pIssue.Level),
		Location:    pIssue.Input,
		Suggestion:  pIssue.Suggestion,
	}
}

// MCP扫描器
type Scanner struct {
	mutex   sync.Mutex
	results []*ScanResult
	plugins []plugins.McpPlugin
}

// 创建新的扫描器
func NewScanner() *Scanner {
	return &Scanner{
		results: make([]*ScanResult, 0),
		plugins: make([]plugins.McpPlugin, 0),
	}
}

// 注册插件
func (s *Scanner) RegisterPlugin(plugin plugins.McpPlugin) {
	s.mutex.Lock()
	defer s.mutex.Unlock()
	s.plugins = append(s.plugins, plugin)
}

// 获取所有扫描结果
func (s *Scanner) GetResults() []*ScanResult {
	s.mutex.Lock()
	defer s.mutex.Unlock()

	results := make([]*ScanResult, len(s.results))
	copy(results, s.results)
	return results
}

// 扫描命令
func (s *Scanner) ScanCommand(ctx context.Context, command string) (*ScanResult, error) {
	return s.scanInput(ctx, command, plugins.MCPTypeCommand)
}

// 扫描SSE链接
func (s *Scanner) ScanSSELink(ctx context.Context, link string) (*ScanResult, error) {
	return s.scanInput(ctx, link, plugins.MCPTypeSSE)
}

// 扫描代码
func (s *Scanner) ScanCode(ctx context.Context, code string) (*ScanResult, error) {
	return s.scanInput(ctx, code, plugins.MCPTypeCode)
}

// 通用扫描方法
func (s *Scanner) scanInput(ctx context.Context, input string, inputType plugins.MCPType) (*ScanResult, error) {
	s.mutex.Lock()
	defer s.mutex.Unlock()

	result := &ScanResult{
		Timestamp: time.Now(),
		Input:     input,
		Type:      string(inputType),
		Issues:    []Issue{},
	}

	// 准备输入
	mcpInput := []plugins.McpInput{
		{
			Input: input,
			Type:  inputType,
		},
	}

	// 运行所有插件
	for _, plugin := range s.plugins {
		pluginInfo := plugin.GetPlugin()
		gologger.Debugf("运行插件: %s", pluginInfo.Name)

		issues, err := plugin.Check(mcpInput)
		if err != nil {
			gologger.Warningf("插件 %s 运行失败: %v", pluginInfo.Name, err)
			continue
		}

		// 转换插件结果
		for _, issue := range issues {
			result.Issues = append(result.Issues, convertPluginIssue(issue))
		}
	}

	s.results = append(s.results, result)
	return result, nil
}

// 打印扫描结果
func (s *Scanner) PrintResults() {
	s.mutex.Lock()
	defer s.mutex.Unlock()

	if len(s.results) == 0 {
		gologger.Infoln("没有扫描结果")
		return
	}

	for i, result := range s.results {
		gologger.Infof("== 扫描结果 #%d ==", i+1)
		gologger.Infof("时间: %s", result.Timestamp.Format("2006-01-02 15:04:05"))
		gologger.Infof("输入类型: %s", result.Type)
		gologger.Infof("输入: %s", result.Input)

		if len(result.Issues) == 0 {
			gologger.Infoln("没有发现安全问题")
		} else {
			gologger.Infof("发现 %d 个安全问题:", len(result.Issues))
			for j, issue := range result.Issues {
				gologger.Infof("  %d. [%s] %s", j+1, issue.Level, issue.Title)
				gologger.Infof("     描述: %s", issue.Description)
				gologger.Infof("     位置: %s", issue.Location)
				gologger.Infof("     建议: %s\n", issue.Suggestion)
			}
		}
	}
}

// 身份验证绕过检测规则
type AuthBypassRule struct {
	Name        string
	Pattern     *regexp.Regexp
	Level       string
	Description string
	Suggestion  string
}

// 默认身份验证绕过检测规则
var defaultAuthBypassRules = []AuthBypassRule{
	{
		Name:        "弱密码检测",
		Pattern:     regexp.MustCompile(`(?i)password\s*=\s*['"]?(admin|password|123456|qwerty|default)['"]?`),
		Level:       LevelHigh,
		Description: "发现硬编码的弱密码，可能被攻击者利用",
		Suggestion:  "使用强密码政策并避免在代码中硬编码密码",
	},
	{
		Name:        "未加密令牌传输",
		Pattern:     regexp.MustCompile(`(?i)(token|auth_token|access_token|session_id)\s*=\s*['"][^'"]{5,}['"]`),
		Level:       LevelHigh,
		Description: "发现明文传输的认证令牌",
		Suggestion:  "使用HTTPS或其他加密方式传输认证信息",
	},
	{
		Name:        "不安全的OAuth实现",
		Pattern:     regexp.MustCompile(`(?i)(oauth|oauth2).*?(redirect_uri|client_secret)\s*=\s*['"][^'"]+['"]`),
		Level:       LevelMedium,
		Description: "OAuth实现可能存在缺陷",
		Suggestion:  "确保OAuth流程安全，避免硬编码client_secret",
	},
	{
		Name:        "缺少身份验证检查",
		Pattern:     regexp.MustCompile(`(?i)function\s+handle.*?\{\s*[^{]*?response\s*\(`),
		Level:       LevelCrit,
		Description: "处理函数可能缺少身份验证检查",
		Suggestion:  "在处理请求前增加身份验证检查",
	},
	{
		Name:        "硬编码JWT密钥",
		Pattern:     regexp.MustCompile(`(?i)(secret|key|jwt).*?['"][a-zA-Z0-9+/=]{16,}['"]`),
		Level:       LevelCrit,
		Description: "发现硬编码的JWT密钥",
		Suggestion:  "从环境变量或安全存储中获取JWT密钥",
	},
}

// AI提示词模板
const authBypassAIPrompt = `
分析以下MCP代码或链接，检测可能存在的身份验证绕过漏洞：

%s

需要重点检查：
1. 弱密码或硬编码凭证
2. 未加密的令牌传输
3. 不安全的OAuth实现
4. 缺失的身份验证检查
5. JWT实现缺陷
6. 会话管理问题

对于每个潜在问题，提供：
- 问题类型
- 严重程度(低/中/高/严重)
- 详细描述
- 问题位置
- 修复建议
`

// 扫描MCP代码或链接中的身份验证绕过漏洞
func (s *Scanner) ScanAuthBypass(input string, inputType string) *ScanResult {
	s.mutex.Lock()
	defer s.mutex.Unlock()

	result := &ScanResult{
		Timestamp: time.Now(),
		Input:     input,
		Type:      inputType,
		Issues:    []Issue{},
	}

	// 基于规则的检测
	for _, rule := range defaultAuthBypassRules {
		matches := rule.Pattern.FindAllStringIndex(input, -1)
		for _, match := range matches {
			startPos := match[0]
			endPos := match[1]

			// 获取匹配上下文
			start := startPos - 20
			if start < 0 {
				start = 0
			}
			end := endPos + 20
			if end > len(input) {
				end = len(input)
			}

			location := fmt.Sprintf("字符位置: %d-%d", startPos, endPos)
			if strings.Count(input[:startPos], "\n") > 0 {
				line := strings.Count(input[:startPos], "\n") + 1
				location = fmt.Sprintf("第%d行", line)
			}

			issue := Issue{
				Title:       rule.Name,
				Description: rule.Description,
				Level:       rule.Level,
				Location:    location,
				Suggestion:  rule.Suggestion,
			}

			result.Issues = append(result.Issues, issue)
		}
	}

	// 可以在这里集成AI大模型分析
	// AIAnalysis(input, authBypassAIPrompt, result)

	s.results = append(s.results, result)
	return result
}

// 与AI大模型集成的分析函数 (占位实现)
func AIAnalysis(input string, promptTemplate string, result *ScanResult) {
	// 这里需要实现对接AI大模型的逻辑
	// 1. 构建提示词
	_ = fmt.Sprintf(promptTemplate, input) // 使用_忽略未使用的prompt变量

	// 2. 调用AI接口并解析结果
	// aiResponse := callAIModel(prompt)

	// 3. 解析AI返回结果并添加到Issues中
	// issues := parseAIResponse(aiResponse)
	// result.Issues = append(result.Issues, issues...)
}

// 命令执行特征规则
type CmdExecRule struct {
	Name        string
	Language    string
	Pattern     *regexp.Regexp
	Level       string
	Description string
	Suggestion  string
}

// 默认命令执行检测规则
var defaultCmdExecRules = []CmdExecRule{
	// Python
	{
		Name:        "Python os.system 命令执行",
		Language:    "Python",
		Pattern:     regexp.MustCompile(`(?i)os\s*\.\s*system\s*\(`),
		Level:       LevelHigh,
		Description: "使用os.system()直接执行系统命令，可能导致命令注入",
		Suggestion:  "使用参数化命令执行，避免使用shell=True选项，过滤危险字符",
	},
	{
		Name:        "Python subprocess 命令执行",
		Language:    "Python",
		Pattern:     regexp.MustCompile(`(?i)(subprocess\s*\.\s*(Popen|call|run|check_output|check_call))`),
		Level:       LevelHigh,
		Description: "使用subprocess模块执行系统命令，可能导致命令注入",
		Suggestion:  "使用参数列表而非字符串传递命令，设置shell=False，过滤用户输入",
	},
	{
		Name:        "Python eval/exec 代码执行",
		Language:    "Python",
		Pattern:     regexp.MustCompile(`(?i)(eval|exec)\s*\(`),
		Level:       LevelCrit,
		Description: "使用eval()或exec()执行动态代码，极易导致代码注入",
		Suggestion:  "避免使用eval/exec，使用更安全的替代方法如ast.literal_eval()或json.loads()",
	},

	// JavaScript
	{
		Name:        "JavaScript eval 代码执行",
		Language:    "JavaScript",
		Pattern:     regexp.MustCompile(`(?i)(eval|Function|setTimeout|setInterval)\s*\(`),
		Level:       LevelCrit,
		Description: "使用eval()或Function构造函数执行动态代码，可能导致代码注入",
		Suggestion:  "避免使用eval和Function构造函数，使用JSON.parse()处理JSON数据",
	},
	{
		Name:        "Node.js 命令执行",
		Language:    "JavaScript",
		Pattern:     regexp.MustCompile(`(?i)(child_process|require\s*\(\s*['"]child_process['"]\s*\)).*?(exec|spawn|execSync|spawnSync)`),
		Level:       LevelHigh,
		Description: "使用child_process模块执行系统命令，可能导致命令注入",
		Suggestion:  "使用execFile或spawn并传递参数数组而非字符串，过滤用户输入",
	},

	// Java
	{
		Name:        "Java Runtime.exec 命令执行",
		Language:    "Java",
		Pattern:     regexp.MustCompile(`(?i)(Runtime\s*\.\s*getRuntime\s*\(\s*\)\s*\.\s*exec|ProcessBuilder)`),
		Level:       LevelHigh,
		Description: "使用Runtime.exec()或ProcessBuilder执行系统命令，可能导致命令注入",
		Suggestion:  "使用ProcessBuilder并传递命令数组而非字符串，过滤用户输入",
	},

	// PHP
	{
		Name:        "PHP 命令执行",
		Language:    "PHP",
		Pattern:     regexp.MustCompile(`(?i)(system|exec|shell_exec|passthru|proc_open|popen)`),
		Level:       LevelCrit,
		Description: "使用PHP命令执行函数，可能导致命令注入",
		Suggestion:  "避免使用命令执行函数，使用escapeshellarg()和escapeshellcmd()过滤参数",
	},

	// Go
	{
		Name:        "Go exec.Command 命令执行",
		Language:    "Go",
		Pattern:     regexp.MustCompile(`(?i)(exec\s*\.\s*Command|os/exec)`),
		Level:       LevelMedium,
		Description: "使用exec.Command执行系统命令，可能导致命令注入",
		Suggestion:  "避免将用户输入直接传递给Command，使用固定的命令路径，分离命令和参数",
	},

	// 命令链接字符
	{
		Name:        "命令链接字符检测",
		Language:    "通用",
		Pattern:     regexp.MustCompile(`(;|\$\(|\$\{|\|\||&&|>|<|\|)`),
		Level:       LevelHigh,
		Description: "发现命令链接字符，可能被用于绕过命令执行限制",
		Suggestion:  "过滤命令链接字符，使用白名单验证输入内容",
	},

	// 沙箱和权限控制
	{
		Name:        "权限提升检测",
		Language:    "通用",
		Pattern:     regexp.MustCompile(`(?i)(sudo|su\s+|chmod\s+777|chown|setuid|setgid)`),
		Level:       LevelCrit,
		Description: "发现可能用于权限提升的命令",
		Suggestion:  "限制执行环境权限，使用最小权限原则",
	},

	// 文件系统操作
	{
		Name:        "危险文件操作",
		Language:    "通用",
		Pattern:     regexp.MustCompile(`(?i)(rm\s+-rf|unlink\s+|/etc/passwd|/etc/shadow|/etc/hosts)`),
		Level:       LevelCrit,
		Description: "发现危险的文件系统操作",
		Suggestion:  "限制文件系统访问权限，使用白名单验证文件路径",
	},
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

// 扫描MCP代码或链接中的命令执行漏洞
func (s *Scanner) ScanCommandExecution(input string, inputType string) *ScanResult {
	s.mutex.Lock()
	defer s.mutex.Unlock()

	result := &ScanResult{
		Timestamp: time.Now(),
		Input:     input,
		Type:      inputType,
		Issues:    []Issue{},
	}

	// 基于规则的检测
	for _, rule := range defaultCmdExecRules {
		matches := rule.Pattern.FindAllStringIndex(input, -1)
		for _, match := range matches {
			startPos := match[0]
			endPos := match[1]

			// 获取匹配上下文
			start := startPos - 20
			if start < 0 {
				start = 0
			}
			end := endPos + 20
			if end > len(input) {
				end = len(input)
			}

			location := fmt.Sprintf("字符位置: %d-%d", startPos, endPos)
			if strings.Count(input[:startPos], "\n") > 0 {
				line := strings.Count(input[:startPos], "\n") + 1
				location = fmt.Sprintf("第%d行", line)
			}

			issue := Issue{
				Title:       fmt.Sprintf("[%s] %s", rule.Language, rule.Name),
				Description: rule.Description,
				Level:       rule.Level,
				Location:    location,
				Suggestion:  rule.Suggestion,
			}

			result.Issues = append(result.Issues, issue)
		}
	}

	// 可以在这里集成AI大模型分析
	// AIAnalysisForCommandExec(input, cmdExecAIPrompt, result)

	s.results = append(s.results, result)
	return result
}

// 命令执行漏洞的AI模型分析函数
func AIAnalysisForCommandExec(input string, promptTemplate string, result *ScanResult) {
	// 这里需要实现对接AI大模型的逻辑
	// 1. 构建提示词
	_ = fmt.Sprintf(promptTemplate, input) // 使用_忽略未使用的prompt变量

	// 2. 调用AI接口并解析结果
	// aiResponse := callAIModel(prompt)

	// 3. 解析AI返回结果并添加到Issues中
	// issues := parseAIResponse(aiResponse)
	// result.Issues = append(result.Issues, issues...)
}

// 命名混淆信息
type NameConfusionInfo struct {
	OfficialName   string
	OfficialVendor string
	Description    string
}

// 官方MCP服务信息示例
var officialMCPServices = []NameConfusionInfo{
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
}

// 计算字符串编辑距离 (Levenshtein距离)
func levenshteinDistance(s1, s2 string) int {
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

// 计算名称相似度 (0-1之间，1表示完全相同)
func calculateNameSimilarity(name1, name2 string) float64 {
	// 如果字符串长度为0，则相似度为0
	if len(name1) == 0 || len(name2) == 0 {
		return 0.0
	}

	// 计算编辑距离
	distance := levenshteinDistance(name1, name2)

	// 计算相似度
	maxLength := float64(max(len(name1), len(name2)))
	similarity := 1.0 - float64(distance)/maxLength

	return similarity
}

// 判断是否为潜在的命名混淆
func isPotentialNameConfusion(name string, officialService NameConfusionInfo, similarityThreshold float64) bool {
	similarity := calculateNameSimilarity(name, officialService.OfficialName)
	return similarity >= similarityThreshold && similarity < 1.0
}

// 检测服务提供商是否可信
func isVendorTrusted(vendor string, officialVendors []string) bool {
	for _, officialVendor := range officialVendors {
		if strings.EqualFold(vendor, officialVendor) {
			return true
		}
	}
	return false
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

// MCP服务信息结构
type MCPServiceInfo struct {
	Name        string
	Description string
	Vendor      string
}

// 扫描MCP服务命名混淆与抢注攻击
func (s *Scanner) ScanNameConfusion(serviceInfo MCPServiceInfo) *ScanResult {
	s.mutex.Lock()
	defer s.mutex.Unlock()

	result := &ScanResult{
		Timestamp: time.Now(),
		Input:     serviceInfo.Name,
		Type:      "MCP服务名称",
		Issues:    []Issue{},
	}

	// 获取所有官方供应商名单
	officialVendors := make([]string, 0)
	for _, service := range officialMCPServices {
		if !sliceContains(officialVendors, service.OfficialVendor) {
			officialVendors = append(officialVendors, service.OfficialVendor)
		}
	}

	// 检查供应商是否可信
	if !isVendorTrusted(serviceInfo.Vendor, officialVendors) {
		issue := Issue{
			Title:       "非官方供应商",
			Description: fmt.Sprintf("服务供应商'%s'不在官方供应商列表中，可能存在安全风险", serviceInfo.Vendor),
			Level:       LevelMedium,
			Location:    "服务元数据",
			Suggestion:  "建议使用官方供应商提供的MCP服务，或对第三方服务进行严格的安全审查",
		}
		result.Issues = append(result.Issues, issue)
	}

	// 检查名称混淆
	similarityThreshold := 0.8 // 相似度阈值
	for _, officialService := range officialMCPServices {
		if isPotentialNameConfusion(serviceInfo.Name, officialService, similarityThreshold) {
			issue := Issue{
				Title: "命名混淆风险",
				Description: fmt.Sprintf("服务名称'%s'与官方服务'%s'高度相似，可能导致AI错误调用",
					serviceInfo.Name, officialService.OfficialName),
				Level:      LevelHigh,
				Location:   "服务名称",
				Suggestion: "更改服务名称，避免与官方服务名称相似，或确认是否为官方服务的正式替代品",
			}
			result.Issues = append(result.Issues, issue)
		}
	}

	// 检查名称与描述不匹配
	// 此处可添加更复杂的NLP分析逻辑，当前仅为示例
	if len(serviceInfo.Description) < 10 {
		issue := Issue{
			Title:       "服务描述不充分",
			Description: "服务描述过于简短，难以判断服务真实功能",
			Level:       LevelLow,
			Location:    "服务描述",
			Suggestion:  "提供详细的服务功能描述，包括用途、权限和数据处理方式",
		}
		result.Issues = append(result.Issues, issue)
	}

	// 可以在这里集成AI大模型分析
	// AIAnalysisForNameConfusion(serviceInfo, nameConfusionAIPrompt, result)

	s.results = append(s.results, result)
	return result
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

// 命名混淆检测的AI模型分析函数
func AIAnalysisForNameConfusion(serviceInfo MCPServiceInfo, promptTemplate string, result *ScanResult) {
	// 这里需要实现对接AI大模型的逻辑
	// 1. 构建提示词
	_ = fmt.Sprintf(promptTemplate, serviceInfo.Name, serviceInfo.Description, serviceInfo.Vendor)

	// 2. 调用AI接口并解析结果
	// aiResponse := callAIModel(prompt)

	// 3. 解析AI返回结果并添加到Issues中
	// issues := parseAIResponse(aiResponse)
	// result.Issues = append(result.Issues, issues...)
}
