package plugins

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

// 安全问题
type Issue struct {
	Title       string
	Description string
	Level       Level
	Suggestion  string
	Input       string
	Type        MCPType // 输入类型：命令行、SSE链接、MCP代码
}

type McpInput struct {
	Input string
	Type  MCPType // 输入类型：命令行、SSE链接、MCP代码
}

type McpPlugin interface {
	GetPlugin() Plugin
	Check(input []McpInput) ([]Issue, error)
}
