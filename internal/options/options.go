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
	ListFpsTemplate bool              // 是否列出指纹模板
	ListVulTemplate bool              // 是否列出漏洞模板
	CheckVulTargets bool              // 检查漏洞模板是否正确
	AIAnalysis      bool              // 是否启用AI分析
	AIToken         string            // AI服务的认证令牌
	LocalScan       bool              // 一键检测本地
	WebServer       bool              // 是否启用WebSocket服务器
	WebServerAddr   string            // WebSocket服务器地址
	Callback        func(interface{}) // 回调函数
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
	flag.Var(&options.Target, "target", "目标,可以指定多个目标 eg:-target xx.com -target aa.com")
	flag.StringVar(&options.TargetFile, "file", "", "指定目标文件")
	flag.StringVar(&options.Output, "o", "", "输出的文件")
	flag.IntVar(&options.TimeOut, "timeout", 5, "超时时间(s)")
	flag.StringVar(&options.ProxyURL, "proxy-url", "", "代理url")
	flag.IntVar(&options.RateLimit, "limit", 200, "限制每秒的并发数量")
	flag.StringVar(&options.FPTemplates, "fps", "data/fingerprints", "指定指纹文件或目录")
	flag.StringVar(&options.AdvTemplates, "vul", "data/vuln", "指定漏洞库目录")
	flag.BoolVar(&options.ListFpsTemplate, "list-fps", false, "输出指纹列表")
	flag.BoolVar(&options.ListVulTemplate, "list-vul", false, "输出漏洞库列表")
	flag.BoolVar(&options.CheckVulTargets, "check-vul", false, "检查漏洞模板是否正确")
	flag.BoolVar(&options.AIAnalysis, "ai", false, "AI分析")
	flag.StringVar(&options.AIToken, "token", "", "混元token")
	flag.BoolVar(&options.LocalScan, "localscan", false, "一键检测本地")
	flag.BoolVar(&options.WebServer, "ws", false, "启用WebServer服务器")
	flag.StringVar(&options.WebServerAddr, "ws-addr", "127.0.0.1:8088", "WebSocket服务器地址")
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
