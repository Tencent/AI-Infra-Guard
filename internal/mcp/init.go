package mcp

import (
	"github.com/Tencent/AI-Infra-Guard/internal/gologger"
	"github.com/Tencent/AI-Infra-Guard/internal/mcp/plugins"
)

// InitDetector 初始化MCP检测器并注册插件
func InitDetector(timeout int) *Detector {
	// 创建检测器
	detector := NewDetector(0) // 使用默认超时时间

	// 注册所有插件
	registerPlugins(detector)

	gologger.Infof("MCP检测器初始化完成，已注册%d个插件", len(detector.scanner.plugins))

	return detector
}

// 注册所有插件
func registerPlugins(detector *Detector) {
	// 身份验证绕过检测插件
	detector.RegisterPlugin(plugins.NewAuthBypassPlugin())

	// 命令执行漏洞检测插件
	detector.RegisterPlugin(plugins.NewCmdExecPlugin())

	// 命名混淆检测插件
	detector.RegisterPlugin(plugins.NewNameConfusionPlugin())

	// 可以在此处添加更多插件
}
