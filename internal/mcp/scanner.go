package mcp

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"os"
	"path/filepath"
	"regexp"
	"strconv"
	"strings"
	"sync"
	"text/template"
	"time"

	utils2 "github.com/Tencent/AI-Infra-Guard/common/utils"
	"github.com/Tencent/AI-Infra-Guard/common/utils/models"
	"github.com/mark3labs/mcp-go/client/transport"
	"github.com/mark3labs/mcp-go/mcp"
	"github.com/remeh/sizedwaitgroup"

	"github.com/Tencent/AI-Infra-Guard/internal/gologger"
	"github.com/Tencent/AI-Infra-Guard/internal/mcp/utils"
	"github.com/mark3labs/mcp-go/client"
)

type Scanner struct {
	mutex         sync.Mutex
	results       []*Issue
	PluginConfigs []*PluginConfig
	aiModel       *models.OpenAI
	client        *client.Client
	csvResult     [][]string
	codePath      string
	url           string
	callback      func(data interface{})
	language      string
	logger        *gologger.Logger
}

type McpCallbackProcessing struct {
	Current int `json:"current"`
	Total   int `json:"total"`
}

type McpCallbackReadMe struct {
	Content string `json:"content"`
}

type McpModuleStart struct {
	ModuleName string
}

type McpModuleEnd struct {
	ModuleName string
	Result     string
}

func NewScanner(aiConfig *models.OpenAI, logger *gologger.Logger) *Scanner {
	if logger == nil {
		logger = gologger.NewLogger()
	}
	s := &Scanner{
		results:       make([]*Issue, 0),
		PluginConfigs: make([]*PluginConfig, 0),
		aiModel:       aiConfig,
		csvResult:     make([][]string, 0),
		language:      "zh",
		logger:        logger,
	}
	return s
}

func (s *Scanner) SetCallback(callback func(data interface{})) {
	s.callback = callback
}

func (s *Scanner) GetPluginsByCategory(category string) []*PluginConfig {
	plugins := make([]*PluginConfig, 0)
	for _, plugin := range s.PluginConfigs {
		for _, c := range plugin.Info.Category {
			if c == category {
				p := plugin
				plugins = append(plugins, p)
			}
		}
	}
	return plugins
}

func (s *Scanner) GetAllPluginNames() ([]string, error) {
	names := make([]string, 0)
	execPath, err := os.Executable()
	if err != nil {
		return nil, err
	}

	// 构建data/mcp目录路径
	dataDir := filepath.Join(filepath.Dir(execPath), "data", "mcp")

	// 如果相对路径不存在，尝试从工作目录查找
	if _, err := os.Stat(dataDir); os.IsNotExist(err) {
		wd, _ := os.Getwd()
		dataDir = filepath.Join(wd, "data", "mcp")
	}
	files, err := utils2.ScanDir(dataDir)
	if err != nil {
		return nil, err
	}

	for _, configPath := range files {
		if !strings.HasSuffix(configPath, ".yaml") {
			continue
		}
		plugin, err := NewYAMLPlugin(configPath)
		if err != nil {
			s.logger.Errorf("加载插件配置失败 %s: %v", configPath, err)
			continue
		}
		names = append(names, plugin.Info.ID)
	}
	return names, nil
}

func (s *Scanner) RegisterPlugin(plugins []string) error {
	// 获取当前执行文件的目录
	execPath, err := os.Executable()
	if err != nil {
		return err
	}

	// 构建data/mcp目录路径
	dataDir := filepath.Join(filepath.Dir(execPath), "data", "mcp")

	// 如果相对路径不存在，尝试从工作目录查找
	if _, err := os.Stat(dataDir); os.IsNotExist(err) {
		wd, _ := os.Getwd()
		dataDir = filepath.Join(wd, "data", "mcp")
	}
	files, err := utils2.ScanDir(dataDir)
	if err != nil {
		return err
	}

	for _, configPath := range files {
		if !strings.HasSuffix(configPath, ".yaml") {
			continue
		}
		plugin, err := NewYAMLPlugin(configPath)
		if err != nil {
			s.logger.Errorf("加载插件配置失败 %s: %v", configPath, err)
			continue
		}
		id := plugin.Info.ID
		if len(plugins) > 0 {
			for _, p := range plugins {
				if p == id {
					s.logger.Infof("加载插件 %s", plugin.Info.Name)
					s.PluginConfigs = append(s.PluginConfigs, plugin)
					break
				}
			}
		} else {
			s.logger.Infof("加载插件 %s", plugin.Info.Name)
			s.PluginConfigs = append(s.PluginConfigs, plugin)
		}
	}
	if len(s.PluginConfigs) == 0 {
		return fmt.Errorf("未加载任何插件")
	}
	return nil
}

func (s *Scanner) InputCommand(ctx context.Context, command string, argv []string) (*mcp.InitializeResult, error) {
	mcpClient, err := client.NewStdioMCPClient(
		command,
		argv,
	)
	if err != nil {
		return nil, err
	}
	s.client = mcpClient
	return utils.InitMcpClient(ctx, s.client)
}

func (s *Scanner) InputUrl(ctx context.Context, url string) (*mcp.InitializeResult, error) {
	dirs := []string{"", "/mcp", "/sse"}
	url = strings.TrimRight(url, "/")
	scan := func(ctx context.Context, url string) (*mcp.InitializeResult, error) {
		r, err := s.InputStreamLink(ctx, url)
		if err != nil {
			r, err = s.InputSSELink(ctx, url)
			if err != nil {
				return nil, err
			}
		}
		return r, nil
	}
	var err error
	for _, u := range dirs {
		link := url + u
		r, err := scan(ctx, link)
		if err == nil {
			return r, nil
		}
	}
	return nil, err
}

func (s *Scanner) InputSSELink(ctx context.Context, link string) (*mcp.InitializeResult, error) {
	opt := client.WithHTTPClient(&http.Client{Timeout: 10 * time.Second})
	mcpClient, err := client.NewSSEMCPClient(link, opt)
	if err != nil {
		return nil, err
	}
	r, err := utils.InitMcpClient(ctx, mcpClient)
	if err != nil {
		return nil, err
	}
	s.client = mcpClient
	return r, err
}

func (s *Scanner) InputStreamLink(ctx context.Context, link string) (*mcp.InitializeResult, error) {
	mcpClient, err := client.NewStreamableHttpClient(link, transport.WithHTTPTimeout(10*time.Second))
	if err != nil {
		return nil, err
	}
	r, err := utils.InitMcpClient(ctx, mcpClient)
	if err != nil {
		return nil, err
	}
	s.client = mcpClient
	return r, nil
}

func (s *Scanner) InputCodePath(codePath string) error {
	c, err := filepath.Abs(codePath)
	if err != nil {
		return err
	}
	s.codePath = c
	return nil
}

func (s *Scanner) SetLanguage(language string) error {
	if language == "" {
		s.language = "zh"
		return nil
	}
	if language == "zh-CN" {
		s.language = "zh"
	} else {
		s.language = language
	}
	return nil
}

type McpTemplate struct {
	CodePath              string
	DirectoryStructure    string
	StaticAnalysisResults string
	OriginalReports       string
	McpStructure          string
}

type McpResult struct {
	Issues []Issue
	Report []Issue
}

func runAIAnalysis(ctx context.Context, p *PluginConfig, config *McpPluginConfig, staticResults []string) (*McpResult, error) {
	// 获取目录结构
	ret := McpResult{
		Issues: make([]Issue, 0),
		Report: make([]Issue, 0),
	}
	dirPrompt, err := utils.ListDir(config.CodePath, 2, "")
	if err != nil {
		config.Logger.WithError(err).Errorln("read directory failed: " + config.CodePath)
		return &ret, err
	}

	// 构建AI提示词
	tpl, err := template.New("template").Parse(p.PromptTemplate)
	var buf bytes.Buffer
	staticAnalysisText := strings.Join(staticResults, "\n\n")
	var originalReports string

	// 特殊处理vuln_review插件
	if p.Info.ID == "vuln_review" {
		originalReports = ctx.Value("original_reports").(string)
	}
	err = tpl.Execute(&buf, McpTemplate{
		CodePath:              config.CodePath,
		DirectoryStructure:    dirPrompt,
		StaticAnalysisResults: staticAnalysisText,
		OriginalReports:       originalReports,
		McpStructure:          "",
	})

	// 运行AI分析
	agent := utils.NewAutoGPT([]string{buf.String()}, config.Language, config.CodePath)
	_, err = agent.Run(ctx, config.AIModel, config.Logger)
	if err != nil {
		config.Logger.WithError(err).Errorln("run ai analysis failed")
		return &ret, err
	}

	if p.Info.ID == "mcp_info_collection" || p.Info.ID == "code_info_collection" {
		summaryPrompt := `
Generate a detailed project information collection report based on the context, providing an accurate technical background and risk assessment foundation for subsequent security testing. The report should include a comprehensive analysis of the technical architecture, a functional module inventory, and identification of security concerns.

# Output Format

# Project Overview
• Basic project information and positioning  
• Core functionalities and business value  
• Technical architecture and implementation methods  
• User groups and usage scenarios  
# Technical Analysis
• Programming languages and technology stack  
• Framework and dependency analysis  
• Data processing and storage solutions  
• Network communication and interface design  
# Security Assessment
• Permission requirements and access control  
• Data processing security  
• Network exposure analysis  
• Potential security concerns  
# Functional Inventory
• List of MCP tools and resources  
• Detailed description of each function  
• Dependencies between functions  
• Identification of security-sensitive operations  

Reply directly in Markdown format.
`
		infoCollections, err := SummaryChat(ctx, agent, config, summaryPrompt)
		if err != nil {
			return &ret, err
		}
		ret.Issues = []Issue{
			{
				Title:       "Information Collection Report",
				Description: infoCollections,
			},
		}
		return &ret, nil
	} else if p.Info.ID == "vuln_review" {
		issues, err := SummaryResult(ctx, agent, config)
		if err != nil {
			return &ret, err
		}
		ret.Issues = issues
		reporterResp, err := SummaryReport(ctx, agent, config)
		if err != nil {
			return &ret, err
		}
		reporter := ParseIssues(reporterResp)
		ret.Report = reporter
		return &ret, nil
	} else {
		issues, err := SummaryResult(ctx, agent, config)
		if err != nil {
			return &ret, err
		}
		ret.Issues = issues
		if len(issues) == 0 {
			reporterResp, err := SummaryReport(ctx, agent, config)
			if err != nil {
				return &ret, err
			}
			reporter := ParseIssues(reporterResp)
			ret.Report = reporter
		}
		return &ret, nil
	}
}

func runDynamicAnalysis(ctx context.Context, p *PluginConfig, config *McpPluginConfig) (*McpResult, error) {

	tpl, err := template.New("template").Parse(p.PromptTemplate)
	if err != nil {
		return nil, err
	}
	var buf bytes.Buffer
	var originalReports string

	// 特殊处理vuln_review插件
	if p.Info.ID == "vuln_review" {
		originalReports = ctx.Value("original_reports").(string)
	}
	err = tpl.Execute(&buf, McpTemplate{
		CodePath:              config.CodePath,
		DirectoryStructure:    "",
		StaticAnalysisResults: "",
		OriginalReports:       originalReports,
		McpStructure:          config.McpStructure,
	})

	// 运行AI分析
	agent := utils.NewAutoWEBGPT(config.Language)
	_, err = agent.Run(ctx, config.AIModel, config.Logger, config.Client, buf.String())
	if err != nil {
		config.Logger.WithError(err).Errorln("run ai analysis failed")
		return nil, err
	}
	ret := McpResult{
		Issues: make([]Issue, 0),
		Report: make([]Issue, 0),
	}

	if p.Info.ID == "mcp_info_collection" {
		summaryPrompt := `
Now generate a detailed markdown-formatted project information collection report based on the context, to provide an accurate technical background and risk assessment foundation for subsequent security testing.  
# Expected Report Structure
The markdown report must include the following key information (if applicable):  
# Project Overview
• Basic Information and Project Positioning  
• Core Functionality and Business Value  
• Technical Architecture and Implementation Plan  
• User Groups and Usage Scenarios  
# Technical Analysis
• Programming Languages and Tech Stack  
• Framework and Dependency Library Analysis  
• Data Processing and Storage Solutions  
• Network Communication Interface Design  
# Security Assessment
• Permission Requirements and Access Control  
• Data Processing Security  
• Network Exposure Analysis  
• Potential Security Risks  
# Functional Inventory
• MCP Tools and Resource List  
• Detailed Description of Each Function  
• Inter-functional Dependencies  
• Sensitive Operation Identification Points  

Reply directly in markdown format.
`
		infoCollection, err := SummaryChat(ctx, agent, config, summaryPrompt)
		if err != nil {
			return nil, err
		}
		ret.Issues = []Issue{
			{
				Title:       "Information Collection Report",
				Description: infoCollection,
			},
		}
		return &ret, nil
	} else {
		issue, err := SummaryResult(ctx, agent, config)
		if err != nil {
			return nil, err
		}
		ret.Issues = issue
		return &ret, nil
	}
}

func (s *Scanner) runCheckCode(ctx context.Context, p *PluginConfig, config *McpPluginConfig) (*McpResult, error) {
	var results []string
	if len(p.Rules) > 0 {
		// 编译所有正则表达式
		var compiledRules []struct {
			rule    Rule
			pattern *regexp.Regexp
		}

		for _, rule := range p.Rules {
			compiled, err := regexp.Compile(rule.Pattern)
			if err != nil {
				s.logger.Warningf("regex compile:%s faild:%v", rule.Pattern, err.Error())
				continue
			}
			compiledRules = append(compiledRules, struct {
				rule    Rule
				pattern *regexp.Regexp
			}{rule: rule, pattern: compiled})
		}

		// 扫描文件
		err := filepath.Walk(s.codePath, func(path string, info os.FileInfo, err error) error {
			if err != nil {
				return err
			}

			if info.IsDir() {
				// 跳过常见的非源代码目录
				baseName := filepath.Base(path)
				if baseName == "node_modules" || baseName == "vendor" || baseName == ".git" ||
					baseName == "__pycache__" {
					return filepath.SkipDir
				}
				return nil
			}

			// 检查文件扩展名
			content, err := os.ReadFile(path)
			if err != nil {
				return nil
			}

			contentStr := string(content)
			relPath, _ := filepath.Rel(s.codePath, path)

			// 对每个规则进行匹配
			for _, compiledRule := range compiledRules {
				matches := compiledRule.pattern.FindAllString(contentStr, -1)
				if len(matches) > 0 {
					result := fmt.Sprintf("file: %s\nrule: %s\nmatches: %v\ndescription: %s\n", relPath, compiledRule.rule.Name, matches, compiledRule.rule.Description)
					results = append(results, result)
				}
			}
			return nil
		})

		if err != nil {
			s.logger.WithError(err).Errorln("scan file failed")
		}
	}
	return runAIAnalysis(ctx, p, config, results)
}

type CallbackWriteLog struct {
	Text       []byte
	ModuleName string
}

type tmpWriter struct {
	Callback   func(data interface{})
	Mux        sync.Mutex
	cache      []byte
	ModuleName string
}

func (t *tmpWriter) Write(p []byte) (n int, err error) {
	t.Mux.Lock()
	defer t.Mux.Unlock()
	for _, word := range p {
		t.cache = append(t.cache, word)
		if word == '\n' {
			if t.Callback != nil {
				t.Callback(CallbackWriteLog{t.cache, t.ModuleName})
			}
			t.cache = []byte{}
		}
	}
	return len(p), nil
}

func (t *tmpWriter) Finally() {
	if len(t.cache) > 0 {
		if t.Callback != nil {
			t.Callback(CallbackWriteLog{t.cache, t.ModuleName})
		}
		t.cache = []byte{}
	}
}

func (s *Scanner) ScanCode(ctx context.Context, parallel bool) (*McpResult, error) {
	logger := s.logger
	totalProcessing := len(s.PluginConfigs) + 2 // 信息收集和review插件
	currentProcessing := 0
	if s.language == "" {
		s.language = "zh"
	}

	// 定义语言相关的文本
	var texts struct {
		// 模块名称
		infoCollection, vulnReview string
		// 日志消息
		infoCollecting, infoCollectionComplete, infoCollectionFailed, infoCollectionEmpty                             string
		pluginRunning, pluginRunSuccess, pluginRunFailed, issuesFound, pluginRunTime                                  string
		vulnCount, vulnReviewStart, vulnReviewPluginLoadFailed, vulnReviewPluginRunFailed, vulnReviewPluginRunSuccess string
		// 错误消息
		infoCollectionPluginLoadFailed, pluginRunFailedError string
	}

	if s.language == "en" {
		// 模块名称
		texts.infoCollection = "Information Collection"
		texts.vulnReview = "Vulnerability Review"
		// 日志消息
		texts.infoCollecting = "Information collecting..."
		texts.infoCollectionComplete = "Information collection completed"
		texts.infoCollectionFailed = "Information collection failed"
		texts.infoCollectionEmpty = "Information collection failed, result is empty"
		texts.pluginRunning = "Running plugin %s"
		texts.pluginRunSuccess = "Plugin %s run successfully"
		texts.pluginRunFailed = "Plugin %s run failed: %v"
		texts.issuesFound = "Found %d issues"
		texts.pluginRunTime = "Plugin %s run time: %v consumed tokens:%d"
		texts.vulnCount = "Current vulnerability count:%d starting vulnerability review..."
		texts.vulnReviewStart = "Starting vulnerability review..."
		texts.vulnReviewPluginLoadFailed = "Vulnerability review plugin load failed: %v"
		texts.vulnReviewPluginRunFailed = "Plugin %s run failed: %v"
		texts.vulnReviewPluginRunSuccess = "Plugin %s run successfully, found %d issues"
		// 错误消息
		texts.infoCollectionPluginLoadFailed = "Information collection plugin load failed: %v"
		texts.pluginRunFailedError = "Plugin run failed"
	} else {
		// 模块名称
		texts.infoCollection = "信息收集"
		texts.vulnReview = "漏洞评审"
		// 日志消息
		texts.infoCollecting = "信息收集中..."
		texts.infoCollectionComplete = "信息收集完成"
		texts.infoCollectionFailed = "信息收集失败"
		texts.infoCollectionEmpty = "信息收集失败 结果为空"
		texts.pluginRunning = "运行插件 %s"
		texts.pluginRunSuccess = "插件 %s 运行成功"
		texts.pluginRunFailed = "插件 %s 运行失败: %v"
		texts.issuesFound = "共发现 %d 个问题"
		texts.pluginRunTime = "插件 %s 运行时间: %v 消耗token:%d"
		texts.vulnCount = "当前漏洞数量:%d 开始进行漏洞review..."
		texts.vulnReviewStart = "开始进行漏洞review..."
		texts.vulnReviewPluginLoadFailed = "漏洞评审插件加载失败: %v"
		texts.vulnReviewPluginRunFailed = "插件 %s 运行失败: %v"
		texts.vulnReviewPluginRunSuccess = "插件 %s 运行成功, 共发现 %d 个问题"
		// 错误消息
		texts.infoCollectionPluginLoadFailed = "信息收集插件加载失败: %v"
		texts.pluginRunFailedError = "插件运行失败"
	}

	if s.callback != nil {
		s.callback(McpCallbackProcessing{Current: 5, Total: 100})
	}
	ret := McpResult{
		Report: []Issue{},
		Issues: []Issue{},
	}
	// 1. 运行信息收集插件
	if s.callback != nil {
		s.callback(McpModuleStart{ModuleName: texts.infoCollection})
	}
	infoPlugin, err := s.getPluginByID("code_info_collection")
	if err != nil {
		return nil, fmt.Errorf(texts.infoCollectionPluginLoadFailed, err)
	} else {
		logger.Infoln(texts.infoCollecting)
		newLogger := gologger.NewLogger()
		tmpW := &tmpWriter{
			Callback:   s.callback,
			ModuleName: texts.infoCollection,
		}
		newLogger.Logrus().SetOutput(tmpW)

		result, err := s.runCheckCode(ctx, infoPlugin, &McpPluginConfig{
			Client:   s.client,
			CodePath: s.codePath,
			AIModel:  s.aiModel,
			Language: s.language,
			Logger:   newLogger,
		})
		tmpW.Finally()
		if err != nil {
			gologger.WithError(err).Warningf(texts.infoCollectionFailed)
		}
		var infoPrompt string
		if result != nil && len(result.Issues) == 1 {
			infoPrompt = result.Issues[0].Description
			ctx = context.WithValue(ctx, "collection_prompt", infoPrompt)
			logger.Infoln(texts.infoCollectionComplete)
		} else {
			logger.Warningf(texts.infoCollectionEmpty)
		}
		if s.callback != nil {
			currentProcessing += 1
			s.callback(McpCallbackProcessing{Current: currentProcessing, Total: totalProcessing})
			s.callback(McpCallbackReadMe{infoPrompt})
			s.callback(McpModuleEnd{ModuleName: texts.infoCollection, Result: infoPrompt})
		}
	}

	s.csvResult = append(s.csvResult, []string{"Scan Folder", s.codePath})
	lock := sync.Mutex{}

	// 2. 运行检测插件
	runPlugin := func(ctx context.Context, plugin *PluginConfig) (*McpResult, error) {
		select {
		case <-ctx.Done():
			return nil, ctx.Err()
		default:
		}

		// 跳过特殊插件
		if plugin.Info.ID == "code_info_collection" || plugin.Info.ID == "vuln_review" {
			return nil, nil
		}

		logger.Infof(texts.pluginRunning, plugin.Info.Name)
		newLogger := gologger.NewLogger()
		tmpW := &tmpWriter{
			Callback:   s.callback,
			ModuleName: plugin.Info.Name,
		}
		newLogger.Logrus().SetOutput(tmpW)

		s.aiModel.ResetToken()
		startTime := time.Now()
		config := McpPluginConfig{
			Client:   s.client,
			CodePath: s.codePath,
			AIModel:  s.aiModel,
			Language: s.language,
			Logger:   newLogger,
		}
		if s.callback != nil {
			lock.Lock()
			s.callback(McpModuleStart{ModuleName: plugin.Info.Name})
			lock.Unlock()
		}
		result, err := s.runCheckCode(ctx, plugin, &config)
		tmpW.Finally()
		if s.callback != nil {
			lock.Lock()
			currentProcessing += 1
			s.callback(McpCallbackProcessing{Current: currentProcessing, Total: totalProcessing})
			s.callback(McpModuleEnd{ModuleName: plugin.Info.Name, Result: ""})
			lock.Unlock()
		}
		if err != nil || result == nil {
			logger.Warningf(texts.pluginRunFailed, plugin.Info.Name, err)
			return nil, err
		}
		logger.Infof(texts.pluginRunSuccess, plugin.Info.Name)
		logger.Infof(texts.issuesFound, len(result.Issues))
		logger.Infof(texts.pluginRunTime, plugin.Info.Name, time.Since(startTime).String(), s.aiModel.GetTotalToken())
		lock.Lock()
		s.csvResult = append(s.csvResult, []string{"PluginId", plugin.Info.ID, "PluginName", plugin.Info.Name, "UseToken", strconv.Itoa(int(s.aiModel.GetTotalToken())), "time", time.Since(startTime).String()})
		lock.Unlock()
		// 转换插件结果
		for _, res := range result.Issues {
			if s.callback != nil {
				lock.Lock()
				s.callback(res)
				lock.Unlock()
			}
		}
		return result, nil
	}

	wg := sizedwaitgroup.New(5)
	for _, plugin := range s.GetPluginsByCategory("code") {
		if parallel {
			wg.Add()
			go func(plugin *PluginConfig) {
				defer wg.Done()
				result, err := runPlugin(ctx, plugin)
				if err != nil {
					gologger.WithError(err).Errorln(texts.pluginRunFailedError)
				}
				lock.Lock()
				if result != nil {
					if len(result.Report) > 0 {
						ret.Report = append(ret.Report, result.Report...)
					}
					if len(result.Issues) > 0 {
						ret.Issues = append(ret.Issues, result.Issues...)
					}
				}
				lock.Unlock()
			}(plugin)
		} else {
			result, err := runPlugin(ctx, plugin)
			if err != nil {
				gologger.WithError(err).Errorln(texts.pluginRunFailedError)
			}
			lock.Lock()
			if result != nil {
				if len(result.Report) > 0 {
					ret.Report = append(ret.Report, result.Report...)
				}
				if len(result.Issues) > 0 {
					ret.Issues = append(ret.Issues, result.Issues...)
				}
			}
			lock.Unlock()
		}
	}
	wg.Wait()

	// 3. 运行漏洞评审插件
	defer func() {
		if s.callback != nil {
			currentProcessing += 1
			s.callback(McpCallbackProcessing{Current: currentProcessing, Total: totalProcessing})
			s.callback(McpModuleEnd{ModuleName: texts.vulnReview, Result: ""})
		}
	}()
	if s.callback != nil {
		s.callback(McpModuleStart{ModuleName: texts.vulnReview})
	}
	if len(ret.Issues) > 0 {
		results := ret.Issues
		logger.Infof(texts.vulnCount, len(results))
		origin := strings.Builder{}
		for _, res := range results {
			origin.WriteString("<result>")
			origin.WriteString("<title>" + res.Title + "</title>")
			origin.WriteString("<desc>" + res.Description + "</desc>")
			origin.WriteString("<risk_type>" + res.RiskType + "</risk_type>")
			origin.WriteString("<level>" + string(res.Level) + "</level>")
			origin.WriteString("<suggestion>" + res.Suggestion + "</suggestion>")
			origin.WriteString("</result>")
			origin.WriteString("\n\n")
		}

		reviewPlugin, err := s.getPluginByID("vuln_review")
		if err != nil {
			logger.Warningf(texts.vulnReviewPluginLoadFailed, err)
		} else {
			ctx = context.WithValue(ctx, "original_reports", origin.String())
			issues, err := s.runCheckCode(ctx, reviewPlugin, &McpPluginConfig{
				Client:   s.client,
				CodePath: s.codePath,
				AIModel:  s.aiModel,
				Language: s.language,
				Logger:   logger,
			})
			if err != nil {
				logger.Warningf(texts.vulnReviewPluginRunFailed, reviewPlugin.Info.Name, err)
			} else {
				logger.Infof(texts.vulnReviewPluginRunSuccess, reviewPlugin.Info.Name, len(issues.Issues))
				results = make([]Issue, 0) // 清空之前的结果
				for _, res := range issues.Issues {
					res2 := res
					// 替换绝对路径
					res2.Description = strings.ReplaceAll(res2.Description, s.codePath, "")
					if s.callback != nil {
						s.callback(res2)
					}
					results = append(results, res2)
				}
				ret.Issues = results
				if len(ret.Report) > 0 {
					ret.Report = append(ret.Report, issues.Report...)
				}
			}
		}
	}
	return &ret, nil
}

func (s *Scanner) ScanLink(ctx context.Context, r *mcp.InitializeResult, parallel bool) (*McpResult, error) {
	if s.client == nil {
		return nil, fmt.Errorf("client is nil")
	}
	tools, err := utils.ListMcpTools(ctx, s.client)
	if err != nil {
		return nil, err
	}
	p, err := s.getPluginByID("mcp_info_collection")
	if err != nil {
		return nil, err
	}
	plugins := s.GetPluginsByCategory("dynamic")
	totalProcessing := len(plugins) + 2
	currentProcessing := 0
	if s.language == "" {
		s.language = "zh"
	}

	// 定义语言相关的文本
	var texts struct {
		// 模块名称
		infoCollection, vulnReview string
		// 日志消息
		infoCollecting, infoCollectionComplete, infoCollectionFailed, infoCollectionEmpty                             string
		pluginRunning, pluginRunSuccess, pluginRunFailed, issuesFound, pluginRunTime                                  string
		vulnCount, vulnReviewStart, vulnReviewPluginLoadFailed, vulnReviewPluginRunFailed, vulnReviewPluginRunSuccess string
		// 错误消息
		infoCollectionPluginLoadFailed, pluginRunFailedError string
	}

	if s.language == "en" {
		// 模块名称
		texts.infoCollection = "Information Collection"
		texts.vulnReview = "Vulnerability Review"
		// 日志消息
		texts.infoCollecting = "Information collecting..."
		texts.infoCollectionComplete = "Information collection completed"
		texts.infoCollectionFailed = "Information collection failed"
		texts.infoCollectionEmpty = "Information collection failed, result is empty"
		texts.pluginRunning = "Running plugin %s"
		texts.pluginRunSuccess = "Plugin %s run successfully"
		texts.pluginRunFailed = "Plugin %s run failed: %v"
		texts.issuesFound = "Found %d issues"
		texts.pluginRunTime = "Plugin %s run time: %v consumed tokens:%d"
		texts.vulnCount = "Current vulnerability count:%d starting vulnerability review..."
		texts.vulnReviewStart = "Starting vulnerability review..."
		texts.vulnReviewPluginLoadFailed = "Vulnerability review plugin load failed: %v"
		texts.vulnReviewPluginRunFailed = "Plugin %s run failed: %v"
		texts.vulnReviewPluginRunSuccess = "Plugin %s run successfully, found %d issues"
		// 错误消息
		texts.infoCollectionPluginLoadFailed = "Information collection plugin load failed: %v"
		texts.pluginRunFailedError = "Plugin run failed"
	} else {
		// 模块名称
		texts.infoCollection = "信息收集"
		texts.vulnReview = "漏洞评审"
		// 日志消息
		texts.infoCollecting = "信息收集中..."
		texts.infoCollectionComplete = "信息收集完成"
		texts.infoCollectionFailed = "信息收集失败"
		texts.infoCollectionEmpty = "信息收集失败 结果为空"
		texts.pluginRunning = "运行插件 %s"
		texts.pluginRunSuccess = "插件 %s 运行成功"
		texts.pluginRunFailed = "插件 %s 运行失败: %v"
		texts.issuesFound = "共发现 %d 个问题"
		texts.pluginRunTime = "插件 %s 运行时间: %v 消耗token:%d"
		texts.vulnCount = "当前漏洞数量:%d 开始进行漏洞review..."
		texts.vulnReviewStart = "开始进行漏洞review..."
		texts.vulnReviewPluginLoadFailed = "漏洞评审插件加载失败: %v"
		texts.vulnReviewPluginRunFailed = "插件 %s 运行失败: %v"
		texts.vulnReviewPluginRunSuccess = "插件 %s 运行成功, 共发现 %d 个问题"
		// 错误消息
		texts.infoCollectionPluginLoadFailed = "信息收集插件加载失败: %v"
		texts.pluginRunFailedError = "插件运行失败"
	}

	mcpStructure := fmt.Sprintf("%s\nserver info:%s(%s)\nmcp protocol version:%s\n", r.Instructions, r.ServerInfo.Name, r.ServerInfo.Version, r.ProtocolVersion)
	for _, tool := range tools.Tools {
		mcpStructure += fmt.Sprintf("Name:%s\nDesc:%s\n", tool.Name, tool.Description)
		scheme, _ := json.Marshal(tool.InputSchema)
		mcpStructure += fmt.Sprintf("inputSchema:%s\n\n", scheme)
	}
	if s.callback != nil {
		s.callback(McpCallbackProcessing{Current: 5, Total: 100})
	}
	if s.callback != nil {
		s.callback(McpModuleStart{ModuleName: texts.infoCollection})
	}
	s.logger.Infoln(texts.infoCollecting)
	newLogger := gologger.NewLogger()
	tmpW := &tmpWriter{
		Callback:   s.callback,
		ModuleName: texts.infoCollection,
	}
	newLogger.Logrus().SetOutput(tmpW)

	issues, err := runDynamicAnalysis(ctx, p, &McpPluginConfig{
		Client:       s.client,
		AIModel:      s.aiModel,
		Language:     s.language,
		Logger:       newLogger,
		McpStructure: mcpStructure,
	})
	if err != nil {
		s.logger.Warningf(texts.infoCollectionFailed, err)
	}
	var infoPrompt string
	if issues != nil && len(issues.Issues) == 1 {
		infoPrompt = issues.Issues[0].Description
		ctx = context.WithValue(ctx, "collection_prompt", infoPrompt)
		s.logger.Infoln(texts.infoCollectionComplete)
	} else {
		s.logger.Warningf(texts.infoCollectionEmpty)
	}
	if s.callback != nil {
		currentProcessing += 1
		s.callback(McpCallbackProcessing{Current: currentProcessing, Total: totalProcessing})
		s.callback(McpCallbackReadMe{infoPrompt})
		s.callback(McpModuleEnd{ModuleName: texts.infoCollection, Result: infoPrompt})

	}
	lock := sync.Mutex{}
	logger := s.logger
	runPlugin := func(ctx context.Context, plugin *PluginConfig) (*McpResult, error) {
		select {
		case <-ctx.Done():
			return nil, ctx.Err()
		default:
		}
		logger.Infof(texts.pluginRunning, plugin.Info.Name)
		newLogger := gologger.NewLogger()
		tmpW := &tmpWriter{
			Callback:   s.callback,
			ModuleName: texts.infoCollection,
		}
		newLogger.Logrus().SetOutput(tmpW)
		startTime := time.Now()
		config := McpPluginConfig{
			Client:       s.client,
			McpStructure: mcpStructure,
			AIModel:      s.aiModel,
			Language:     s.language,
			Logger:       newLogger,
		}
		if s.callback != nil {
			lock.Lock()
			s.callback(McpModuleStart{ModuleName: plugin.Info.Name})
			lock.Unlock()
		}
		issues, err := runDynamicAnalysis(ctx, plugin, &config)
		if s.callback != nil {
			lock.Lock()
			currentProcessing += 1
			s.callback(McpCallbackProcessing{Current: currentProcessing, Total: totalProcessing})
			s.callback(McpModuleEnd{ModuleName: plugin.Info.Name, Result: ""})

			lock.Unlock()
		}
		if issues == nil {
			return nil, fmt.Errorf(texts.pluginRunFailed, plugin.Info.Name, "")
		}
		if err != nil {
			logger.Warningf(texts.pluginRunFailed, plugin.Info.Name, err)
		}
		logger.Infof(texts.pluginRunSuccess, plugin.Info.Name)
		logger.Infof(texts.issuesFound, len(issues.Issues))
		logger.Infof(texts.pluginRunTime, plugin.Info.Name, time.Since(startTime).String(), s.aiModel.GetTotalToken())
		// 转换插件结果
		for _, res := range issues.Issues {
			res2 := res
			if s.callback != nil {
				lock.Lock()
				s.callback(res2)
				lock.Unlock()
			}
		}
		return issues, nil
	}

	wg := sizedwaitgroup.New(5)
	results := McpResult{
		Issues: make([]Issue, 0),
		Report: make([]Issue, 0),
	}

	for _, plugin := range s.GetPluginsByCategory("dynamic") {
		if parallel {
			wg.Add()
			go func(plugin *PluginConfig) {
				defer wg.Done()
				result, err := runPlugin(ctx, plugin)
				if err != nil {
					gologger.WithError(err).Errorln(texts.pluginRunFailedError)
				}
				lock.Lock()
				results.Issues = append(results.Issues, result.Issues...)
				results.Report = append(results.Report, result.Report...)
				lock.Unlock()
			}(plugin)
		} else {
			result, err := runPlugin(ctx, plugin)
			if err != nil {
				gologger.WithError(err).Errorln(texts.pluginRunFailedError)
			}
			lock.Lock()
			results.Issues = append(results.Issues, result.Issues...)
			results.Report = append(results.Report, result.Report...)
			lock.Unlock()
		}
	}
	wg.Wait()

	// 3. 运行漏洞评审插件
	defer func() {
		if s.callback != nil {
			currentProcessing += 1
			s.callback(McpCallbackProcessing{Current: currentProcessing, Total: totalProcessing})
			s.callback(McpModuleEnd{ModuleName: texts.vulnReview, Result: ""})
		}
	}()
	if s.callback != nil {
		s.callback(McpModuleStart{ModuleName: texts.vulnReview})
	}

	if len(results.Issues) > 0 {
		logger.Infof(texts.vulnCount, len(results.Issues))
		origin := strings.Builder{}
		for _, res := range results.Issues {
			origin.WriteString("<result>")
			origin.WriteString("<title>" + res.Title + "</title>")
			origin.WriteString("<desc>" + res.Description + "</desc>")
			origin.WriteString("<risk_type>" + res.RiskType + "</risk_type>")
			origin.WriteString("<level>" + string(res.Level) + "</level>")
			origin.WriteString("<suggestion>" + res.Suggestion + "</suggestion>")
			origin.WriteString("</result>")
			origin.WriteString("\n\n")
		}
		ctx = context.WithValue(ctx, "original_reports", origin.String())
		reviewPlugin, err := s.getPluginByID("vuln_review")
		if err != nil {
			logger.Warningf(texts.vulnReviewPluginLoadFailed, err)
		} else {
			issues, err := runDynamicAnalysis(ctx, reviewPlugin, &McpPluginConfig{
				Client:       s.client,
				AIModel:      s.aiModel,
				Language:     s.language,
				Logger:       s.logger,
				McpStructure: mcpStructure,
			})
			if err != nil {
				logger.Warningf(texts.vulnReviewPluginRunFailed, reviewPlugin.Info.Name, err)
			} else {
				logger.Infof(texts.vulnReviewPluginRunSuccess, reviewPlugin.Info.Name, len(issues.Issues))
				for _, res := range issues.Issues {
					if s.callback != nil {
						s.callback(res)
					}
				}
				results.Issues = issues.Issues
			}
		}
	}
	return &results, nil
}

func (s *Scanner) getPluginByID(id string) (*PluginConfig, error) {
	for _, plugin := range s.PluginConfigs {
		if plugin.Info.ID == id {
			return plugin, nil
		}
	}
	return nil, fmt.Errorf("插件 %s 未找到", id)
}

func (s *Scanner) GetCsvResult() [][]string {
	return s.csvResult
}
