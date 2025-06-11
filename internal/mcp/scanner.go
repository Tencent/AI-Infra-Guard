package mcp

import (
	"context"
	"github.com/Tencent/AI-Infra-Guard/internal/gologger"
	"github.com/Tencent/AI-Infra-Guard/internal/mcp/models"
	"github.com/Tencent/AI-Infra-Guard/internal/mcp/plugins"
	"github.com/Tencent/AI-Infra-Guard/internal/mcp/utils"
	"github.com/mark3labs/mcp-go/client"
	"github.com/remeh/sizedwaitgroup"
	"path/filepath"
	"strconv"
	"strings"
	"sync"
	"time"
)

type Scanner struct {
	mutex       sync.Mutex
	results     []*plugins.Issue
	plugins     []plugins.McpPlugin
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
		plugins:     make([]plugins.McpPlugin, 0),
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

	plugin := []plugins.McpPlugin{
		plugins.NewCmdInjectionPlugin(),
		plugins.NewAuthBypassPlugin(),
		plugins.NewNameConfusionPlugin(),
		plugins.NewToolPoisoningPlugin(),
		plugins.NewRugPullPlugin(),
		plugins.NewCredentialTheftPlugin(),
		plugins.NewHardcodedApiKeyPlugin(),
		plugins.NewResourcePoisoningPlugin(),
		plugins.NewToolShadowingPlugin(),
	}
	for _, name := range names {
		for _, p := range plugin {
			if p.GetPlugin().ID == name {
				s.logger.Infof("加载插件 %s", p.GetPlugin().Name)
				s.plugins = append(s.plugins, p)
				break
			}
		}
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

	totalProcessing := len(s.plugins) + 2 // 信息收集和review插件
	currentProcessing := 0
	// 运行所有插件
	info := plugins.NewCollectionInfoPlugin()
	logger.Infoln("信息收集中...")
	issues, err := info.Check(ctx, &plugins.McpPluginConfig{
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
	if len(issues) != 1 {
		logger.Warningf("信息收集失败 结果为空")
	} else {
		infoPrompt = issues[0].Description
		ctx = context.WithValue(ctx, "collection_prompt", infoPrompt)
		logger.Infoln("信息收集完成", infoPrompt)
	}
	if s.callback != nil {
		currentProcessing += 1
		s.callback(McpCallbackProcessing{Current: currentProcessing, Total: totalProcessing})
		s.callback(McpCallbackReadMe{infoPrompt})
	}

	s.csvResult = append(s.csvResult, []string{"Scan Folder", s.codePath})
	lock := sync.Mutex{}

	runPlugin := func(ctx context.Context, plugin plugins.McpPlugin) ([]ScannerIssue, error) {
		select {
		case <-ctx.Done():
			return nil, ctx.Err()
		default:
		}
		pluginInfo := plugin.GetPlugin()
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
	for _, plugin := range s.plugins {
		if parallel {
			wg.Add()
			go func(plugin plugins.McpPlugin) {
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
	defer func() {
		// 最后的review插件
		if s.callback != nil {
			currentProcessing += 1
			s.callback(McpCallbackProcessing{Current: currentProcessing, Total: totalProcessing})
		}
	}()
	if len(results) > 0 {
		// vuln review
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
		results = make([]ScannerIssue, 0)
		reviewPlugin := plugins.VulnReviewPlugin(origin.String())
		issues, err := reviewPlugin.Check(context.Background(), &plugins.McpPluginConfig{
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
	return results, nil
}

func (s *Scanner) GetCsvResult() [][]string {
	return s.csvResult
}
