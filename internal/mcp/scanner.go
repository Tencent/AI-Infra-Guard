package mcp

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	utils2 "github.com/Tencent/AI-Infra-Guard/common/utils"
	"github.com/mark3labs/mcp-go/mcp"
	"os"
	"path/filepath"
	"regexp"
	"strings"
	"sync"
	"text/template"
	"time"

	"strconv"

	"github.com/Tencent/AI-Infra-Guard/internal/gologger"
	"github.com/Tencent/AI-Infra-Guard/internal/mcp/models"
	"github.com/Tencent/AI-Infra-Guard/internal/mcp/utils"
	"github.com/mark3labs/mcp-go/client"
	"github.com/remeh/sizedwaitgroup"
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
	s.registerPlugin()
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

func (s *Scanner) registerPlugin() error {
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

		s.logger.Infof("加载插件 %s", plugin.Info.Name)
		s.PluginConfigs = append(s.PluginConfigs, plugin)
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
	dirs := []string{"/", "/mcp", "/sse"}
	url = strings.TrimRight(url, "/")
	scan := func(ctx context.Context, url string) (*mcp.InitializeResult, error) {
		r, err := s.InputStreamLink(ctx, url)
		if err != nil {
			r, err = s.InputSSELink(ctx, url)
			if err != nil {
				return nil, err
			}
		}
		return r, err
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
	mcpClient, err := client.NewSSEMCPClient(link)
	if err != nil {
		return nil, err
	}
	s.client = mcpClient
	return utils.InitMcpClient(ctx, s.client)
}

func (s *Scanner) InputStreamLink(ctx context.Context, link string) (*mcp.InitializeResult, error) {
	mcpClient, err := client.NewStreamableHttpClient(link)
	if err != nil {
		return nil, err
	}
	s.client = mcpClient
	return utils.InitMcpClient(ctx, s.client)
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
	if language == "zh-CN" {
		s.language = "zh"
	} else {
		s.language = language
	}
	return nil
}

type ScannerIssue struct {
	PluginId string `json:"pluginId,omitempty"`
	Issue
}

type McpTemplate struct {
	CodePath              string
	DirectoryStructure    string
	StaticAnalysisResults string
	OriginalReports       string
	McpStructure          string
}

func runAIAnalysis(ctx context.Context, p *PluginConfig, config *McpPluginConfig, staticResults []string) ([]Issue, error) {
	// 获取目录结构
	dirPrompt, err := utils.ListDir(config.CodePath, 2, "")
	if err != nil {
		config.Logger.WithError(err).Errorln("read directory failed: " + config.CodePath)
		return nil, err
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
		return nil, err
	}

	if p.Info.ID == "mcp_info_collection" {
		summaryPrompt := `
根据上下文生成详细的项目信息收集报告，为后续安全检测提供准确的技术背景和风险评估基础。报告应包含完整的技术架构分析、功能模块清单和安全关注点识别

## 输出格式

### 项目概览
- 项目基本信息和定位
- 核心功能和业务价值
- 技术架构和实现方式
- 用户群体和使用场景

### 技术分析
- 编程语言和技术栈
- 框架和依赖库分析
- 数据处理和存储方案
- 网络通信和接口设计

### 安全评估
- 权限需求和访问控制
- 数据处理安全性
- 网络暴露面分析
- 潜在安全关注点

### 功能清单
- MCP工具和资源列表
- 每个功能的详细描述
- 功能间的依赖关系
- 安全敏感操作识别

直接回复我markdown格式
`
		infoCollections, err := SummaryChat(ctx, agent, config, summaryPrompt)
		if err != nil {
			return nil, err
		}
		return []Issue{
			{
				Title:       "信息收集报告",
				Description: infoCollections,
			},
		}, nil
	} else {
		return SummaryResult(ctx, agent, config)
	}
}

func runDynamicAnalysis(ctx context.Context, p *PluginConfig, config *McpPluginConfig) ([]Issue, error) {

	tpl, err := template.New("template").Parse(p.PromptTemplate)
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

	if p.Info.ID == "mcp_info_collection" {
		summaryPrompt := `
现在根据上下文生成详细的markdown格式项目信息收集报告，为后续安全检测提供精确的技术背景与风险评估基础。
### 预期报告结构
markdown格式报告需要包含以下关键信息(如有)：
#### 项目概览
基础信息与项目定位
核心功能与业务价值
技术架构与实现方案
用户群体及使用场景
### 技术分析
编程语言与技术栈
框架与依赖库分析
数据处理存储方案
网络通信接口设计
#### 安全评估
权限需求与访问控制
数据处理安全性
网络暴露面分析
潜在安全隐患
#### 功能清单
MCP工具与资源列表
各功能详细描述
功能间依赖关系
敏感操作识别点

直接回复我markdown格式
`
		infoCollection, err := SummaryChat(ctx, agent, config, summaryPrompt)
		if err != nil {
			return nil, err
		}
		return []Issue{
			{
				Title:       "信息收集报告",
				Description: infoCollection,
			},
		}, nil
	} else {
		return SummaryResult(ctx, agent, config)
	}
}

func (s *Scanner) runCheckCode(ctx context.Context, p *PluginConfig, config *McpPluginConfig) ([]Issue, error) {
	var staticResults []string
	if len(p.Rules) > 0 {
		var results []string

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
	return runAIAnalysis(ctx, p, config, staticResults)
}

func (s *Scanner) ScanCode(ctx context.Context, parallel bool) ([]ScannerIssue, error) {
	results := make([]ScannerIssue, 0)
	logger := s.logger

	totalProcessing := len(s.PluginConfigs) + 2 // 信息收集和review插件
	currentProcessing := 0
	if s.callback != nil {
		s.callback(McpCallbackProcessing{Current: 5, Total: 100})
	}
	// 1. 运行信息收集插件
	infoPlugin, err := s.getPluginByID("code_info_collection")
	if err != nil {
		logger.Warningf("信息收集插件加载失败: %v", err)
	} else {
		logger.Infoln("信息收集中...")
		issues, err := s.runCheckCode(ctx, infoPlugin, &McpPluginConfig{
			Client:   s.client,
			CodePath: s.codePath,
			AIModel:  s.aiModel,
			Language: s.language,
			Logger:   logger,
		})
		if err != nil {
			logger.Warningf("信息收集失败: %v", err)
		}
		var infoPrompt string
		if len(issues) == 1 {
			infoPrompt = issues[0].Description
			ctx = context.WithValue(ctx, "collection_prompt", infoPrompt)
			logger.Infoln("信息收集完成")
		} else {
			logger.Warningf("信息收集失败 结果为空")
		}
		if s.callback != nil {
			currentProcessing += 1
			s.callback(McpCallbackProcessing{Current: currentProcessing, Total: totalProcessing})
			s.callback(McpCallbackReadMe{infoPrompt})
		}
	}

	s.csvResult = append(s.csvResult, []string{"Scan Folder", s.codePath})
	lock := sync.Mutex{}

	// 2. 运行检测插件
	runPlugin := func(ctx context.Context, plugin *PluginConfig) ([]ScannerIssue, error) {
		select {
		case <-ctx.Done():
			return nil, ctx.Err()
		default:
		}

		// 跳过特殊插件
		if plugin.Info.ID == "code_info_collection" || plugin.Info.ID == "vuln_review" {
			return nil, nil
		}

		logger.Infof("运行插件 %s", plugin.Info.Name)
		s.aiModel.ResetToken()
		startTime := time.Now()
		config := McpPluginConfig{
			Client:   s.client,
			CodePath: s.codePath,
			AIModel:  s.aiModel,
			Language: s.language,
			Logger:   logger,
		}
		issues, err := s.runCheckCode(ctx, plugin, &config)
		if s.callback != nil {
			lock.Lock()
			currentProcessing += 1
			s.callback(McpCallbackProcessing{Current: currentProcessing, Total: totalProcessing})
			lock.Unlock()
		}
		if err != nil {
			logger.Warningf("插件 %s 运行失败: %v", plugin.Info.Name, err)
		}
		logger.Infof("插件 %s 运行成功", plugin.Info.Name)
		logger.Infof("共发现 %d 个问题", len(issues))
		logger.Infof("插件 %s 运行时间: %v 消耗token:%d", plugin.Info.Name, time.Since(startTime).String(), s.aiModel.GetTotalToken())
		lock.Lock()
		s.csvResult = append(s.csvResult, []string{"PluginId", plugin.Info.ID, "PluginName", plugin.Info.Name, "UseToken", strconv.Itoa(int(s.aiModel.GetTotalToken())), "time", time.Since(startTime).String()})
		lock.Unlock()
		// 转换插件结果
		var result []ScannerIssue
		for _, res := range issues {
			res2 := res
			r := ScannerIssue{
				PluginId: plugin.Info.ID,
				Issue:    res2,
			}
			if s.callback != nil {
				lock.Lock()
				s.callback(r)
				lock.Unlock()
			}
			result = append(result, r)
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
					gologger.WithError(err).Errorln("插件运行失败")
				}
				lock.Lock()
				results = append(results, result...)
				lock.Unlock()
			}(plugin)
		} else {
			result, err := runPlugin(ctx, plugin)
			if err != nil {
				gologger.WithError(err).Errorln("插件运行失败")
			}
			lock.Lock()
			results = append(results, result...)
			lock.Unlock()
		}
	}
	wg.Wait()

	// 3. 运行漏洞评审插件
	defer func() {
		if s.callback != nil {
			currentProcessing += 1
			s.callback(McpCallbackProcessing{Current: currentProcessing, Total: totalProcessing})
		}
	}()

	if len(results) > 0 {
		logger.Infof("当前漏洞数量:%d 开始进行漏洞review...", len(results))
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
			logger.Warningf("漏洞评审插件加载失败: %v", err)
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
				logger.Warningf("插件 %s 运行失败: %v", reviewPlugin.Info.Name, err)
			} else {
				logger.Infof("插件 %s 运行成功, 共发现 %d 个问题", reviewPlugin.Info.Name, len(issues))
				results = make([]ScannerIssue, 0) // 清空之前的结果
				for _, res := range issues {
					res2 := res
					// 替换绝对路径
					res2.Description = strings.ReplaceAll(res2.Description, s.codePath, "")
					r := ScannerIssue{
						Issue: res2,
					}
					if s.callback != nil {
						s.callback(r)
					}
					results = append(results, r)
				}
			}
		}
	}
	return results, nil
}

func (s *Scanner) ScanLink(ctx context.Context, r *mcp.InitializeResult, parallel bool) ([]ScannerIssue, error) {
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

	mcpStructure := fmt.Sprintf("%s\nserver info:%s(%s)\nmcp protocol version:%s\n", r.Instructions, r.ServerInfo.Name, r.ServerInfo.Version, r.ProtocolVersion)
	for _, tool := range tools.Tools {
		mcpStructure += fmt.Sprintf("Name:%s\nDesc:%s\n", tool.Name, tool.Description)
		scheme, _ := json.Marshal(tool.InputSchema)
		mcpStructure += fmt.Sprintf("inputSchema:%s\n\n", scheme)
	}
	if s.callback != nil {
		s.callback(McpCallbackProcessing{Current: 5, Total: 100})
	}

	if err != nil {
		s.logger.Warningf("信息收集插件加载失败: %v", err)
	} else {
		s.logger.Infoln("信息收集中...")
		issues, err := runDynamicAnalysis(ctx, p, &McpPluginConfig{
			Client:       s.client,
			AIModel:      s.aiModel,
			Language:     s.language,
			Logger:       s.logger,
			McpStructure: mcpStructure,
		})
		if err != nil {
			s.logger.Warningf("信息收集失败: %v", err)
		}
		var infoPrompt string
		if len(issues) == 1 {
			infoPrompt = issues[0].Description
			ctx = context.WithValue(ctx, "collection_prompt", infoPrompt)
			s.logger.Infoln("信息收集完成")
		} else {
			s.logger.Warningf("信息收集失败 结果为空")
		}
		if s.callback != nil {
			currentProcessing += 1
			s.callback(McpCallbackProcessing{Current: currentProcessing, Total: totalProcessing})
			s.callback(McpCallbackReadMe{infoPrompt})
		}
	}
	lock := sync.Mutex{}
	logger := s.logger
	runPlugin := func(ctx context.Context, plugin *PluginConfig) ([]ScannerIssue, error) {
		select {
		case <-ctx.Done():
			return nil, ctx.Err()
		default:
		}
		logger.Infof("运行插件 %s", plugin.Info.Name)
		startTime := time.Now()
		config := McpPluginConfig{
			Client:       s.client,
			McpStructure: mcpStructure,
			AIModel:      s.aiModel,
			Language:     s.language,
			Logger:       logger,
		}
		issues, err := runDynamicAnalysis(ctx, plugin, &config)
		if s.callback != nil {
			lock.Lock()
			currentProcessing += 1
			s.callback(McpCallbackProcessing{Current: currentProcessing, Total: totalProcessing})
			lock.Unlock()
		}
		if err != nil {
			logger.Warningf("插件 %s 运行失败: %v", plugin.Info.Name, err)
		}
		logger.Infof("插件 %s 运行成功", plugin.Info.Name)
		logger.Infof("共发现 %d 个问题", len(issues))
		logger.Infof("插件 %s 运行时间: %v 消耗token:%d", plugin.Info.Name, time.Since(startTime).String(), s.aiModel.GetTotalToken())
		// 转换插件结果
		var result []ScannerIssue
		for _, res := range issues {
			res2 := res
			r := ScannerIssue{
				PluginId: plugin.Info.ID,
				Issue:    res2,
			}
			if s.callback != nil {
				lock.Lock()
				s.callback(r)
				lock.Unlock()
			}
			result = append(result, r)
		}
		return result, nil
	}

	wg := sizedwaitgroup.New(5)
	results := make([]ScannerIssue, 0)

	for _, plugin := range s.GetPluginsByCategory("dynamic") {
		if parallel {
			wg.Add()
			go func(plugin *PluginConfig) {
				defer wg.Done()
				result, err := runPlugin(ctx, plugin)
				if err != nil {
					gologger.WithError(err).Errorln("插件运行失败")
				}
				lock.Lock()
				results = append(results, result...)
				lock.Unlock()
			}(plugin)
		} else {
			result, err := runPlugin(ctx, plugin)
			if err != nil {
				gologger.WithError(err).Errorln("插件运行失败")
			}
			lock.Lock()
			results = append(results, result...)
			lock.Unlock()
		}
	}
	wg.Wait()

	// 3. 运行漏洞评审插件
	defer func() {
		if s.callback != nil {
			currentProcessing += 1
			s.callback(McpCallbackProcessing{Current: currentProcessing, Total: totalProcessing})
		}
	}()
	if len(results) > 0 {
		logger.Infof("当前漏洞数量:%d 开始进行漏洞review...", len(results))
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
		ctx = context.WithValue(ctx, "original_reports", origin.String())
		reviewPlugin, err := s.getPluginByID("vuln_review")
		if err != nil {
			logger.Warningf("漏洞评审插件加载失败: %v", err)
		} else {
			issues, err := runDynamicAnalysis(ctx, reviewPlugin, &McpPluginConfig{
				Client:       s.client,
				AIModel:      s.aiModel,
				Language:     s.language,
				Logger:       s.logger,
				McpStructure: mcpStructure,
			})
			if err != nil {
				logger.Warningf("插件 %s 运行失败: %v", reviewPlugin.Info.Name, err)
			} else {
				logger.Infof("插件 %s 运行成功, 共发现 %d 个问题", reviewPlugin.Info.Name, len(issues))
				results = make([]ScannerIssue, 0) // 清空之前的结果
				for _, res := range issues {
					r := ScannerIssue{
						Issue: res,
					}
					if s.callback != nil {
						s.callback(r)
					}
					results = append(results, r)
				}
			}
		}
	}
	return results, nil
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
