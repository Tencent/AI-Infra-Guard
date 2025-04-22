package mcp

import (
	"context"
	"github.com/Tencent/AI-Infra-Guard/internal/gologger"
	"github.com/Tencent/AI-Infra-Guard/internal/mcp/models"
	"github.com/Tencent/AI-Infra-Guard/internal/mcp/plugins"
	"github.com/mark3labs/mcp-go/client"
	"sync"
)

type Scanner struct {
	mutex   sync.Mutex
	results []*plugins.Issue
	plugins []plugins.McpPlugin
	aiModel models.AIModel
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
		//tests.NewCmdExecPlugin(),
		//tests.NewNameConfusionPlugin(),
	}
	gologger.Infof("注册插件数量: %d", len(plugin))
	s.plugins = append(s.plugins, plugin...)
}

func (s *Scanner) ScanCommand(ctx context.Context, command string, argv []string, codePath string) ([]plugins.Issue, error) {
	mcpClient, err := client.NewStdioMCPClient(
		command,
		argv,
	)
	if err != nil {
		return nil, err
	}
	defer mcpClient.Close()
	return s.scanInput(ctx, mcpClient, codePath)
}

func (s *Scanner) ScanSSELink(ctx context.Context, link, codePath string) ([]plugins.Issue, error) {
	mcpClient, err := client.NewSSEMCPClient(link)
	if err != nil {
		return nil, err
	}
	defer mcpClient.Close()
	return s.scanInput(ctx, mcpClient, codePath)
}

func (s *Scanner) scanInput(ctx context.Context, client *client.Client, codePath string) ([]plugins.Issue, error) {
	s.mutex.Lock()
	defer s.mutex.Unlock()

	result := make([]plugins.Issue, 0)

	// 运行所有插件
	for _, plugin := range s.plugins {
		config := plugins.McpPluginConfig{
			Client:   client,
			CodePath: codePath,
			AIModel:  s.aiModel,
		}
		issues, err := plugin.Check(ctx, &config)
		if err != nil {
			pluginInfo := plugin.GetPlugin()
			gologger.Warningf("插件 %s 运行失败: %v", pluginInfo.Name, err)
			continue
		}
		// 转换插件结果
		result = append(result, issues...)
	}
	return result, nil
}
