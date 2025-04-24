package mcp

import (
	"context"
	"github.com/Tencent/AI-Infra-Guard/internal/gologger"
	"github.com/Tencent/AI-Infra-Guard/internal/mcp/models"
	"github.com/Tencent/AI-Infra-Guard/internal/mcp/plugins"
	"github.com/Tencent/AI-Infra-Guard/internal/mcp/utils"
	"github.com/mark3labs/mcp-go/client"
	"os"
	"sync"
	"time"
)

type Scanner struct {
	mutex    sync.Mutex
	results  []*plugins.Issue
	plugins  []plugins.McpPlugin
	aiModel  *models.OpenAI
	client   *client.Client
	codePath string
	log      string
}

func NewScanner(aiConfig *models.OpenAI) *Scanner {
	return &Scanner{
		results: make([]*plugins.Issue, 0),
		plugins: make([]plugins.McpPlugin, 0),
		aiModel: aiConfig,
	}
}

func (s *Scanner) SetLog(log string) {
	s.log = log
}

func (s *Scanner) RegisterPlugin() {
	s.mutex.Lock()
	defer s.mutex.Unlock()
	plugin := []plugins.McpPlugin{
		plugins.NewCmdInjectionPlugin(),
		//plugins.NewAuthBypassPlugin(),
		//plugins.NewNameConfusionPlugin(),
		//plugins.NewToolPoisoningPlugin(),
		//plugins.NewRugPullPlugin(),
		//plugins.NewCredentialTheftPlugin(),
		//plugins.NewHardcodedApiKeyPlugin(),
		//plugins.NewResourcePoisoningPlugin(),
		//plugins.NewToolShadowingPlugin(),
	}
	gologger.Infof("注册插件数量: %d", len(plugin))
	s.plugins = append(s.plugins, plugin...)
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
func (s *Scanner) Scan(ctx context.Context) ([]plugins.Issue, error) {
	s.mutex.Lock()
	defer s.mutex.Unlock()
	result := make([]plugins.Issue, 0)
	// 运行所有插件
	s.aiModel.CacheText = ""
	for _, plugin := range s.plugins {
		pluginInfo := plugin.GetPlugin()
		gologger.Infof("运行插件 %s", pluginInfo.Name)
		s.aiModel.ResetToken()
		startTime := time.Now()
		config := plugins.McpPluginConfig{
			Client:   s.client,
			CodePath: s.codePath,
			AIModel:  s.aiModel,
		}
		issues, err := plugin.Check(ctx, &config)
		if err != nil {
			gologger.Warningf("插件 %s 运行失败: %v", pluginInfo.Name, err)
			continue
		}
		gologger.Infof("插件 %s 运行成功", pluginInfo.Name)
		gologger.Infof("共发现 %d 个问题", len(issues))
		gologger.Infof("插件 %s 运行时间: %v 消耗token:%d", pluginInfo.Name, time.Since(startTime).String(), s.aiModel.GetTotalToken())
		// 转换插件结果
		result = append(result, issues...)
	}
	if s.log != "" {
		os.WriteFile(s.log, []byte(s.aiModel.CacheText), 0644)
	}
	return result, nil
}
