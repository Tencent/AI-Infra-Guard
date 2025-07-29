// Package options 命令行接口
package options

import (
	"errors"
	"flag"
	"net/url"

	"github.com/Tencent/AI-Infra-Guard/internal/gologger"
)

// Options 定义了程序的所有配置选项
type Options struct {
	Target          multiStringFlag   // 目标URL列表
	TargetFile      string            // 包含目标的文件路径
	Output          string            // 输出文件路径
	ProxyURL        string            // 代理服务器URL
	TimeOut         int               // 请求超时时间(秒)
	JSON            bool              // 是否输出JSON格式
	RateLimit       int               // 每秒请求限制数
	FPTemplates     string            // 指纹模板路径
	AdvTemplates    string            // 漏洞模板路径
	ListVulTemplate bool              // 是否列出漏洞模板
	CheckVulTargets bool              // 检查漏洞模板是否正确
	AIAnalysis      bool              // 是否启用AI分析
	AIHunyuanToken  string            // AI服务的认证令牌
	AIDeepSeekToken string            // deepseek的认证令牌
	LocalScan       bool              // 一键检测本地
	WebServer       bool              // 是否启用WebSocket服务器
	WebServerAddr   string            // WebSocket服务器地址
	Headers         multiStringFlag   // HTTP请求头
	Language        string            // 语言
	Callback        func(interface{}) `json:"-"` // 回调函数
}

// multiStringFlag 用于支持命令行中多个相同参数的输入
type multiStringFlag []string

// String 实现flag.Value接口
func (m *multiStringFlag) String() string {
	return ""
}

// Set 实现flag.Value接口，用于设置多个目标值
func (m *multiStringFlag) Set(value string) error {
	*m = append(*m, value)
	return nil
}

// ParseOptions 解析命令行参数并返回配置选项
func ParseOptions() *Options {
	options := &Options{}
	flag.Var(&options.Target, "target", "Target URLs, can specify multiple targets e.g.: -target xx.com -target aa.com")
	flag.StringVar(&options.TargetFile, "file", "", "File containing target URLs")
	flag.StringVar(&options.Output, "o", "", "Output file path")
	flag.BoolVar(&options.JSON, "json", false, "JSON Output")
	flag.IntVar(&options.TimeOut, "timeout", 5, "Request timeout in seconds")
	flag.StringVar(&options.ProxyURL, "proxy-url", "", "Proxy URL")
	flag.Var(&options.Headers, "header", "HTTP headers, can specify multiple headers e.g.: -header \"key:value\" -header \"key:value\"")
	flag.IntVar(&options.RateLimit, "limit", 200, "Maximum requests per second")
	flag.StringVar(&options.FPTemplates, "fps", "data/fingerprints", "Fingerprint templates file or directory")
	flag.StringVar(&options.AdvTemplates, "vul", "data/vuln", "Vulnerability database directory")
	flag.BoolVar(&options.ListVulTemplate, "list-vul", false, "List vulnerability templates")
	flag.BoolVar(&options.CheckVulTargets, "check-vul", false, "Validate vulnerability templates")
	flag.BoolVar(&options.LocalScan, "localscan", false, "One-click local scan")
	flag.BoolVar(&options.WebServer, "ws", false, "Enable WebServer")
	flag.StringVar(&options.WebServerAddr, "ws-addr", "127.0.0.1:8088", "WebSocket server address")
	flag.BoolVar(&options.AIAnalysis, "ai", false, "Enable AI analysis")
	flag.StringVar(&options.AIHunyuanToken, "hunyuan-token", "", "Hunyuan API token")
	flag.StringVar(&options.AIDeepSeekToken, "deepseek-token", "", "DeepSeek API token")
	flag.StringVar(&options.Language, "lang", "zh", "Response language zh/en")
	flag.Parse()
	options.configureOutput()
	ShowBanner()
	err := options.validateOptions()
	if err != nil {
		gologger.Fatalf("Program exiting: %s\n", err.Error())
	}
	return options
}

// validateOptions 验证配置选项的合法性
func (options *Options) validateOptions() error {
	// Validate proxy options if provided
	err := validateProxyURL(
		options.ProxyURL,
		"invalid http proxy format (It should be proto://username:password@host:port)",
	)
	if err != nil {
		return err
	}
	return nil
}

// validateProxyURL 验证代理URL的格式是否正确
func validateProxyURL(proxyURL, message string) error {
	if proxyURL != "" && !isValidURL(proxyURL) {
		return errors.New(message)
	}

	return nil
}

// isValidURL 检查URL字符串是否为有效的URL格式
func isValidURL(urlString string) bool {
	_, err := url.Parse(urlString)

	return err == nil
}

// SetCallback 设置回调函数
func (options *Options) SetCallback(callback func(interface{})) {
	options.Callback = callback
}

// configureOutput 配置程序的输出选项
func (options *Options) configureOutput() {
	// If the user desires verbose output, show verbose output

	//if options.Silent {
	//	gologger.MaxLevel = gologger.Silent
	//	options.OutputWithNoColor = true
	//}
}
