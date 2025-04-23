package mcp

import (
	"context"
	"github.com/Tencent/AI-Infra-Guard/internal/gologger"
	"github.com/Tencent/AI-Infra-Guard/internal/mcp/models"
	"github.com/Tencent/AI-Infra-Guard/internal/mcp/plugins"
	"github.com/Tencent/AI-Infra-Guard/internal/mcp/utils"
	"github.com/mark3labs/mcp-go/client"
	"sync"
)

type Scanner struct {
	mutex    sync.Mutex
	results  []*plugins.Issue
	plugins  []plugins.McpPlugin
	aiModel  models.AIModel
	client   *client.Client
	codePath string
}

func NewScanner(aiConfig models.AIModel) *Scanner {
	return &Scanner{
		results: make([]*plugins.Issue, 0),
		plugins: make([]plugins.McpPlugin, 0),
		aiModel: aiConfig,
	}
}

func (s *Scanner) RegisterPlugin() {
	s.mutex.Lock()
	defer s.mutex.Unlock()
	plugin := []plugins.McpPlugin{
		plugins.NewAuthBypassPlugin(),
		plugins.NewCmdInjectionPlugin(),
		plugins.NewNameConfusionPlugin(),
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
	for _, plugin := range s.plugins {
		pluginInfo := plugin.GetPlugin()
		gologger.Infof("运行插件 %s", pluginInfo.Name)
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
		// 转换插件结果
		result = append(result, issues...)
	}
	return result, nil
}
