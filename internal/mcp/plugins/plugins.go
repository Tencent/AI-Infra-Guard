package plugins

import (
	"context"
	"github.com/Tencent/AI-Infra-Guard/internal/mcp/models"
	"github.com/mark3labs/mcp-go/client"
)

// 威胁级别常量
type Level string

const (
	LevelLow      Level = "low"
	LevelMedium   Level = "medium"
	LevelHigh     Level = "high"
	LevelCritical Level = "critical"
)

type MCPType string

const (
	MCPTypeCommand MCPType = "command"
	MCPTypeSSE     MCPType = "sse"
	MCPTypeCode    MCPType = "code"
)

// Plugin MCP插件信息
type Plugin struct {
	Name string
	Desc string
}

// Issue 安全问题
type Issue struct {
	Title       string `json:"title"`
	Description string `json:"description"`
	Level       Level  `json:"level"`
	Suggestion  string `json:"suggestion"`
}

type McpInput struct {
	Input string
	Type  MCPType // 输入类型：命令行、SSE链接、MCP代码
}

type McpPluginConfig struct {
	Client   *client.Client
	CodePath string
	AIModel  models.AIModel
}

type McpPlugin interface {
	GetPlugin() Plugin
	Check(ctx context.Context, config *McpPluginConfig) ([]Issue, error)
}
