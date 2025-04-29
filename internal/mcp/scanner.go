package mcp

import (
	"context"
	"github.com/Tencent/AI-Infra-Guard/internal/gologger"
	"github.com/Tencent/AI-Infra-Guard/internal/mcp/models"
	"github.com/Tencent/AI-Infra-Guard/internal/mcp/plugins"
	"github.com/Tencent/AI-Infra-Guard/internal/mcp/utils"
	"github.com/mark3labs/mcp-go/client"
	"strconv"
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
}
type McpCallbackProcessing struct {
	Current int `json:"current"`
	Total   int `json:"total"`
}

type McpCallbackReadMe struct {
	Content string `json:"content"`
}

func NewScanner(aiConfig *models.OpenAI) *Scanner {
	return &Scanner{
		results:     make([]*plugins.Issue, 0),
		plugins:     make([]plugins.McpPlugin, 0),
		aiModel:     aiConfig,
		csvResult:   make([][]string, 0),
		saveHistory: false,
		language:    "zh",
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
				gologger.Infof("加载插件 %s", p.GetPlugin().Name)
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
	s.codePath = codePath
	return nil
}

func (s *Scanner) SaveHistory(b bool) error {
	s.saveHistory = b
	return nil
}

func (s *Scanner) SetLanguage(language string) error {
	if language == "zh-CN" {
		s.language = "zh"
	}
	s.language = language
	return nil
}

type ScannerIssue struct {
	PluginId string `json:"pluginId"`
	plugins.Issue
}

func (s *Scanner) Scan(ctx context.Context) ([]ScannerIssue, error) {
	s.mutex.Lock()
	defer s.mutex.Unlock()
	result := make([]ScannerIssue, 0)

	totalProcessing := len(s.plugins) + 1
	currentProcessing := 0
	// 运行所有插件
	info := plugins.NewCollectionInfoPlugin()
	gologger.Infoln("信息收集中...")
	issue, err := info.Check(ctx, &plugins.McpPluginConfig{
		Client:      s.client,
		CodePath:    s.codePath,
		AIModel:     s.aiModel,
		SaveHistory: s.saveHistory,
		Language:    s.language,
	})
	if err != nil {
		gologger.Warningf("信息收集失败: %v", err)
	}
	var infoPrompt string
	if len(issue) != 1 {
		gologger.Warningf("信息收集失败 结果为空")
	} else {
		infoPrompt = issue[0].Description
		ctx = context.WithValue(ctx, "collection_prompt", infoPrompt)
		gologger.Infoln("信息收集完成", infoPrompt)
	}
	if s.callback != nil {
		currentProcessing += 1
		s.callback(McpCallbackProcessing{Current: currentProcessing, Total: totalProcessing})
		s.callback(McpCallbackReadMe{infoPrompt})
	}

	s.csvResult = append(s.csvResult, []string{"Scan Folder", s.codePath})
	for _, plugin := range s.plugins {
		select {
		case <-ctx.Done():
			return nil, ctx.Err()
		default:
		}
		pluginInfo := plugin.GetPlugin()
		gologger.Infof("运行插件 %s", pluginInfo.Name)
		s.aiModel.ResetToken()
		startTime := time.Now()
		config := plugins.McpPluginConfig{
			Client:      s.client,
			CodePath:    s.codePath,
			AIModel:     s.aiModel,
			Language:    s.language,
			SaveHistory: s.saveHistory,
		}
		issues, err := plugin.Check(ctx, &config)
		if s.callback != nil {
			currentProcessing += 1
			s.callback(McpCallbackProcessing{Current: currentProcessing, Total: totalProcessing})
		}
		if err != nil {
			gologger.Warningf("插件 %s 运行失败: %v", pluginInfo.Name, err)
			continue
		}
		gologger.Infof("插件 %s 运行成功", pluginInfo.Name)
		gologger.Infof("共发现 %d 个问题", len(issues))
		gologger.Infof("插件 %s 运行时间: %v 消耗token:%d", pluginInfo.Name, time.Since(startTime).String(), s.aiModel.GetTotalToken())
		s.csvResult = append(s.csvResult, []string{"PluginId", pluginInfo.ID, "PluginName", pluginInfo.Name, "UseToken", strconv.Itoa(int(s.aiModel.GetTotalToken())), "time", time.Since(startTime).String()})
		// 转换插件结果
		for _, issue := range issues {
			r := ScannerIssue{
				PluginId: pluginInfo.ID,
				Issue:    issue,
			}
			if s.callback != nil {
				s.callback(r)
			}
			result = append(result, r)
		}
	}
	return result, nil
}

func (s *Scanner) GetCsvResult() [][]string {
	return s.csvResult
}
