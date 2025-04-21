package mcp

import (
	"context"
	"fmt"
	"os"
	"strings"
	"time"

	"github.com/Tencent/AI-Infra-Guard/internal/gologger"
	"github.com/Tencent/AI-Infra-Guard/internal/mcp/plugins"
)

// Detector MCP安全检测器
type Detector struct {
	scanner *Scanner
	timeout time.Duration
}

// NewDetector 创建新的MCP安全检测器
func NewDetector(timeout time.Duration) *Detector {
	if timeout <= 0 {
		timeout = 60 * time.Second
	}
	return &Detector{
		scanner: NewScanner(),
		timeout: timeout,
	}
}

// RegisterPlugin 注册检测插件
func (d *Detector) RegisterPlugin(plugin plugins.McpPlugin) {
	d.scanner.RegisterPlugin(plugin)
}

// DetectCommandLine 检测MCP命令行
func (d *Detector) DetectCommandLine(command string) (*ScanResult, error) {
	ctx, cancel := context.WithTimeout(context.Background(), d.timeout)
	defer cancel()

	gologger.Infof("开始检测MCP命令行: %s", command)
	return d.scanner.ScanCommand(ctx, command)
}

// DetectSSELink 检测MCP SSE链接
func (d *Detector) DetectSSELink(link string) (*ScanResult, error) {
	ctx, cancel := context.WithTimeout(context.Background(), d.timeout)
	defer cancel()

	gologger.Infof("开始检测MCP SSE链接: %s", link)
	return d.scanner.ScanSSELink(ctx, link)
}

// DetectCodeFile 检测MCP代码文件
func (d *Detector) DetectCodeFile(filePath string) (*ScanResult, error) {
	ctx, cancel := context.WithTimeout(context.Background(), d.timeout)
	defer cancel()

	gologger.Infof("开始检测MCP代码文件: %s", filePath)

	// 检查文件是否存在
	if _, err := os.Stat(filePath); os.IsNotExist(err) {
		return nil, fmt.Errorf("文件不存在: %s", filePath)
	}

	// 读取文件内容
	codeBytes, err := os.ReadFile(filePath)
	if err != nil {
		return nil, fmt.Errorf("读取文件失败: %v", err)
	}

	// 调用代码检测
	code := string(codeBytes)
	return d.scanner.ScanCode(ctx, code)
}

// DetectCode 直接检测MCP代码字符串
func (d *Detector) DetectCode(code string) (*ScanResult, error) {
	ctx, cancel := context.WithTimeout(context.Background(), d.timeout)
	defer cancel()

	gologger.Infof("开始检测MCP代码，长度: %d", len(code))
	return d.scanner.ScanCode(ctx, code)
}

// DetectInput 智能识别输入类型并进行检测
func (d *Detector) DetectInput(input string) (*ScanResult, error) {
	// 检测是否为文件路径
	if _, err := os.Stat(input); err == nil {
		return d.DetectCodeFile(input)
	}

	// 检测是否为URL链接
	if strings.HasPrefix(input, "http://") || strings.HasPrefix(input, "https://") {
		return d.DetectSSELink(input)
	}

	// 检测是否为命令行
	if strings.Contains(input, "mcp ") || strings.Contains(input, "--port") ||
		strings.Contains(input, "-p") || strings.Contains(input, "--host") {
		return d.DetectCommandLine(input)
	}

	// 默认当作代码处理
	return d.DetectCode(input)
}

// PrintResults 打印所有扫描结果
func (d *Detector) PrintResults() {
	d.scanner.PrintResults()
}

// GetResults 获取所有扫描结果
func (d *Detector) GetResults() []*ScanResult {
	return d.scanner.GetResults()
}
