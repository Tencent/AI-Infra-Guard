package mcp

import (
	"context"
	"fmt"
	"io/ioutil"
	"os"
	"path/filepath"
	"regexp"
	"strings"
	"sync"
	"time"

	"strconv"

	"github.com/Tencent/AI-Infra-Guard/internal/gologger"
	"github.com/Tencent/AI-Infra-Guard/internal/mcp/models"
	"github.com/Tencent/AI-Infra-Guard/internal/mcp/plugins"
	"github.com/Tencent/AI-Infra-Guard/internal/mcp/utils"
	"github.com/mark3labs/mcp-go/client"
	"github.com/remeh/sizedwaitgroup"
	"gopkg.in/yaml.v3"
)

// YAML配置结构体
type PluginConfig struct {
	Info struct {
		ID          string `yaml:"id"`
		Name        string `yaml:"name"`
		Description string `yaml:"description"`
		Author      string `yaml:"author"`
	} `yaml:"info"`
	Rules          []Rule `yaml:"rules,omitempty"`
	PromptTemplate string `yaml:"prompt_template"`
}

type Rule struct {
	Name        string `yaml:"name"`
	Pattern     string `yaml:"pattern"`
	Description string `yaml:"description"`
	Language    string `yaml:"language,omitempty"`
	Level       string `yaml:"level,omitempty"`
	Suggestion  string `yaml:"suggestion,omitempty"`
}

// YAML配置插件
type YAMLPlugin struct {
	config PluginConfig
}

func NewYAMLPlugin(configPath string) (*YAMLPlugin, error) {
	data, err := ioutil.ReadFile(configPath)
	if err != nil {
		return nil, err
	}

	var config PluginConfig
	err = yaml.Unmarshal(data, &config)
	if err != nil {
		return nil, err
	}

	return &YAMLPlugin{config: config}, nil
}

func (p *YAMLPlugin) GetPlugin() plugins.Plugin {
	return plugins.Plugin{
		ID:     p.config.Info.ID,
		Name:   p.config.Info.Name,
		Desc:   p.config.Info.Description,
		NameEn: p.config.Info.Name,
		DescEn: p.config.Info.Description,
	}
}

func (p *YAMLPlugin) Check(ctx context.Context, config *plugins.McpPluginConfig) ([]plugins.Issue, error) {
	var issues []plugins.Issue
	var staticResults []string

	// 1. 如果有规则，先进行正则搜索
	if len(p.config.Rules) > 0 {
		config.Logger.Infof("执行正则规则检测...")
		staticResults = p.runStaticAnalysis(config.CodePath, config.Logger)
	}

	// 2. 使用AI进行分析
	if p.config.PromptTemplate != "" {
		config.Logger.Infof("执行AI分析...")
		aiIssues, err := p.runAIAnalysis(ctx, config, staticResults)
		if err != nil {
			return issues, err
		}
		issues = append(issues, aiIssues...)
	}

	return issues, nil
}

func (p *YAMLPlugin) runStaticAnalysis(codePath string, logger *gologger.Logger) []string {
	var results []string

	// 编译所有正则表达式
	var compiledRules []struct {
		rule    Rule
		pattern *regexp.Regexp
	}

	for _, rule := range p.config.Rules {
		compiled, err := regexp.Compile(rule.Pattern)
		if err != nil {
			logger.Warningf("正则表达式编译失败 %s: %v", rule.Name, err)
			continue
		}
		compiledRules = append(compiledRules, struct {
			rule    Rule
			pattern *regexp.Regexp
		}{rule: rule, pattern: compiled})
	}

	// 扫描文件
	err := filepath.Walk(codePath, func(path string, info os.FileInfo, err error) error {
		if err != nil {
			return err
		}

		if info.IsDir() {
			// 跳过常见的非源代码目录
			baseName := filepath.Base(path)
			if baseName == "node_modules" || baseName == "vendor" || baseName == ".git" ||
				baseName == "build" || baseName == "dist" || baseName == "__pycache__" {
				return filepath.SkipDir
			}
			return nil
		}

		// 检查文件扩展名
		if p.shouldScanFile(path) {
			content, err := ioutil.ReadFile(path)
			if err != nil {
				return nil
			}

			contentStr := string(content)
			relPath, _ := filepath.Rel(codePath, path)

			// 对每个规则进行匹配
			for _, compiledRule := range compiledRules {
				matches := compiledRule.pattern.FindAllString(contentStr, -1)
				if len(matches) > 0 {
					result := fmt.Sprintf("文件: %s\n规则: %s\n匹配内容: %v\n描述: %s\n",
						relPath, compiledRule.rule.Name, matches, compiledRule.rule.Description)
					results = append(results, result)
				}
			}
		}
		return nil
	})

	if err != nil {
		logger.Warningf("扫描文件失败: %v", err)
	}

	return results
}

func (p *YAMLPlugin) shouldScanFile(filePath string) bool {
	// 检查文件扩展名，只关注源代码和配置文件
	ext := strings.ToLower(filepath.Ext(filePath))
	baseName := strings.ToLower(filepath.Base(filePath))

	// 源代码文件
	if ext == ".go" || ext == ".py" || ext == ".js" || ext == ".ts" ||
		ext == ".java" || ext == ".php" || ext == ".rb" || ext == ".sh" ||
		ext == ".c" || ext == ".cpp" || ext == ".h" || ext == ".cs" {
		return true
	}

	// 配置文件
	if ext == ".json" || ext == ".yml" || ext == ".yaml" || ext == ".xml" ||
		ext == ".ini" || ext == ".conf" || ext == ".config" || ext == ".toml" {
		return true
	}

	// 特殊敏感文件
	if strings.Contains(baseName, ".env") || strings.Contains(baseName, "secret") ||
		strings.Contains(baseName, "credential") || strings.Contains(baseName, ".key") ||
		strings.Contains(baseName, ".pem") || strings.Contains(baseName, ".ppk") {
		return true
	}

	return false
}

func (p *YAMLPlugin) runAIAnalysis(ctx context.Context, config *plugins.McpPluginConfig, staticResults []string) ([]plugins.Issue, error) {
	// 获取目录结构
	dirPrompt, err := utils.ListDir(config.CodePath, 2, "")
	if err != nil {
		config.Logger.WithError(err).Errorln("读取目录失败: " + config.CodePath)
		return nil, err
	}

	// 构建AI提示词
	prompt := p.config.PromptTemplate

	// 替换模板变量
	prompt = strings.ReplaceAll(prompt, "{{code_path}}", config.CodePath)
	prompt = strings.ReplaceAll(prompt, "{{directory_structure}}", dirPrompt)

	// 如果有静态分析结果，添加到提示词中
	if len(staticResults) > 0 {
		staticAnalysisText := strings.Join(staticResults, "\n\n")
		prompt = strings.ReplaceAll(prompt, "{{static_analysis_results}}", staticAnalysisText)
		prompt = strings.ReplaceAll(prompt, "{{detection_results}}", staticAnalysisText)
		prompt = strings.ReplaceAll(prompt, "{{preliminary_results}}", staticAnalysisText)
	} else {
		prompt = strings.ReplaceAll(prompt, "{{static_analysis_results}}", "未发现匹配的代码模式")
		prompt = strings.ReplaceAll(prompt, "{{detection_results}}", "未发现匹配的代码模式")
		prompt = strings.ReplaceAll(prompt, "{{preliminary_results}}", "未发现匹配的代码模式")
	}

	// 特殊处理vuln_review插件
	if p.config.Info.ID == "vuln_review" {
		if originalReports := ctx.Value("original_reports"); originalReports != nil {
			prompt = strings.ReplaceAll(prompt, "{{original_reports}}", originalReports.(string))
		}
	}

	// 运行AI分析
	agent := utils.NewAutoGPT([]string{prompt}, config.Language, config.CodePath)
	_, err = agent.Run(ctx, config.AIModel, config.Logger)
	if err != nil {
		config.Logger.WithError(err).Warningln("")
		return nil, err
	}

	return plugins.SummaryResult(ctx, agent, config)
}

type Scanner struct {
	mutex       sync.Mutex
	results     []*plugins.Issue
	yamlPlugins []*YAMLPlugin
	aiModel     *models.OpenAI
	client      *client.Client
	csvResult   [][]string
	codePath    string
	callback    func(data interface{})
	saveHistory bool
	language    string
	logger      *gologger.Logger
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
	return &Scanner{
		results:     make([]*plugins.Issue, 0),
		yamlPlugins: make([]*YAMLPlugin, 0),
		aiModel:     aiConfig,
		csvResult:   make([][]string, 0),
		saveHistory: false,
		language:    "zh",
		logger:      logger,
	}
}

func (s *Scanner) SetCallback(callback func(data interface{})) {
	s.callback = callback
}

func (s *Scanner) RegisterPlugin(names []string) {
	s.mutex.Lock()
	defer s.mutex.Unlock()

	// 获取当前执行文件的目录
	execPath, err := os.Executable()
	if err != nil {
		s.logger.Errorln("获取执行文件路径失败:", err)
		return
	}

	// 构建data/mcp目录路径
	dataDir := filepath.Join(filepath.Dir(execPath), "data", "mcp")

	// 如果相对路径不存在，尝试从工作目录查找
	if _, err := os.Stat(dataDir); os.IsNotExist(err) {
		wd, _ := os.Getwd()
		dataDir = filepath.Join(wd, "data", "mcp")
	}

	for _, name := range names {
		configPath := filepath.Join(dataDir, name+".yaml")

		// 检查文件是否存在
		if _, err := os.Stat(configPath); os.IsNotExist(err) {
			s.logger.Warningf("插件配置文件不存在: %s", configPath)
			continue
		}

		plugin, err := NewYAMLPlugin(configPath)
		if err != nil {
			s.logger.Errorf("加载插件配置失败 %s: %v", configPath, err)
			continue
		}

		s.logger.Infof("加载插件 %s", plugin.GetPlugin().Name)
		s.yamlPlugins = append(s.yamlPlugins, plugin)
	}
}

func (s *Scanner) InputCommand(ctx context.Context, command string, argv []string) error {
	mcpClient, err := client.NewStdioMCPClient(
		command,
		argv,
	)
	if err != nil {
		return err
	}
	s.client = mcpClient
	err = utils.InitMcpClient(ctx, s.client)
	if err != nil {
		return err
	}
	return nil
}

func (s *Scanner) InputSSELink(ctx context.Context, link string) error {
	mcpClient, err := client.NewSSEMCPClient(link)
	if err != nil {
		return err
	}
	s.client = mcpClient
	err = utils.InitMcpClient(ctx, s.client)
	if err != nil {
		return err
	}
	return nil
}

func (s *Scanner) InputStreamLink(ctx context.Context, link string) error {
	mcpClient, err := client.NewStreamableHttpClient(link)
	if err != nil {
		return err
	}
	s.client = mcpClient
	err = utils.InitMcpClient(ctx, s.client)
	if err != nil {
		return err
	}
	return nil
}

func (s *Scanner) InputCodePath(codePath string) error {
	c, err := filepath.Abs(codePath)
	if err != nil {
		return err
	}
	s.codePath = c
	return nil
}

func (s *Scanner) SaveHistory(b bool) error {
	s.saveHistory = b
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
	plugins.Issue
}

func (s *Scanner) Scan(ctx context.Context, parallel bool) ([]ScannerIssue, error) {
	s.mutex.Lock()
	defer s.mutex.Unlock()
	results := make([]ScannerIssue, 0)
	logger := s.logger

	totalProcessing := len(s.yamlPlugins) + 2 // 信息收集和review插件
	currentProcessing := 0

	// 1. 运行信息收集插件
	infoPlugin, err := s.getPluginByID("info_collection")
	if err != nil {
		logger.Warningf("信息收集插件加载失败: %v", err)
	} else {
		logger.Infoln("信息收集中...")
		issues, err := infoPlugin.Check(ctx, &plugins.McpPluginConfig{
			Client:      s.client,
			CodePath:    s.codePath,
			AIModel:     s.aiModel,
			SaveHistory: s.saveHistory,
			Language:    s.language,
			Logger:      logger,
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
	runPlugin := func(ctx context.Context, plugin *YAMLPlugin) ([]ScannerIssue, error) {
		select {
		case <-ctx.Done():
			return nil, ctx.Err()
		default:
		}

		pluginInfo := plugin.GetPlugin()

		// 跳过特殊插件
		if pluginInfo.ID == "info_collection" || pluginInfo.ID == "vuln_review" {
			return nil, nil
		}

		logger.Infof("运行插件 %s", pluginInfo.Name)
		s.aiModel.ResetToken()
		startTime := time.Now()
		config := plugins.McpPluginConfig{
			Client:      s.client,
			CodePath:    s.codePath,
			AIModel:     s.aiModel,
			Language:    s.language,
			SaveHistory: s.saveHistory,
			Logger:      logger,
		}
		issues, err := plugin.Check(ctx, &config)
		if s.callback != nil {
			lock.Lock()
			currentProcessing += 1
			s.callback(McpCallbackProcessing{Current: currentProcessing, Total: totalProcessing})
			lock.Unlock()
		}
		if err != nil {
			logger.Warningf("插件 %s 运行失败: %v", pluginInfo.Name, err)
		}
		logger.Infof("插件 %s 运行成功", pluginInfo.Name)
		logger.Infof("共发现 %d 个问题", len(issues))
		logger.Infof("插件 %s 运行时间: %v 消耗token:%d", pluginInfo.Name, time.Since(startTime).String(), s.aiModel.GetTotalToken())
		lock.Lock()
		s.csvResult = append(s.csvResult, []string{"PluginId", pluginInfo.ID, "PluginName", pluginInfo.Name, "UseToken", strconv.Itoa(int(s.aiModel.GetTotalToken())), "time", time.Since(startTime).String()})
		lock.Unlock()
		// 转换插件结果
		var result []ScannerIssue
		for _, res := range issues {
			res2 := res
			r := ScannerIssue{
				PluginId: pluginInfo.ID,
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
	for _, plugin := range s.yamlPlugins {
		if parallel {
			wg.Add()
			go func(plugin *YAMLPlugin) {
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
			issues, err := reviewPlugin.Check(ctx, &plugins.McpPluginConfig{
				Client:      s.client,
				CodePath:    s.codePath,
				AIModel:     s.aiModel,
				SaveHistory: s.saveHistory,
				Language:    s.language,
				Logger:      logger,
			})
			if err != nil {
				logger.Warningf("插件 %s 运行失败: %v", reviewPlugin.GetPlugin().Name, err)
			} else {
				logger.Infof("插件 %s 运行成功, 共发现 %d 个问题", reviewPlugin.GetPlugin().Name, len(issues))
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

func (s *Scanner) getPluginByID(id string) (*YAMLPlugin, error) {
	for _, plugin := range s.yamlPlugins {
		if plugin.GetPlugin().ID == id {
			return plugin, nil
		}
	}
	return nil, fmt.Errorf("插件 %s 未找到", id)
}

func (s *Scanner) GetCsvResult() [][]string {
	return s.csvResult
}
