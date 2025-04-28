package cmd

import (
	"github.com/Tencent/AI-Infra-Guard/common/runner"
	"github.com/Tencent/AI-Infra-Guard/internal/gologger"
	"github.com/Tencent/AI-Infra-Guard/internal/options"
	"github.com/spf13/cobra"
)

// 为scanCmd定义标志变量
var (
	scanTargets         []string
	scanTargetFile      string
	scanOutputFile      string
	scanProxyURL        string
	scanTimeOut         int
	scanRateLimit       int
	scanFpTemplates     string
	scanAdvTemplates    string
	scanListVulTemplate bool
	scanCheckVulTargets bool
	scanLocalScan       bool
	scanAIAnalysis      bool
	scanAIHunyuanToken  string
	scanAIDeepSeekToken string
	scanHeaders         []string
	scanLanguage        string
)

// scanCmd 表示scan子命令
var scanCmd = &cobra.Command{
	Use:   "scan",
	Short: "执行原始扫描功能",
	Long:  `执行原始的扫描功能，扫描指定目标的安全漏洞。`,
	Run: func(cmd *cobra.Command, args []string) {
		// 创建Options对象
		scanOptions := &options.Options{
			Target:          scanTargets,
			TargetFile:      scanTargetFile,
			Output:          scanOutputFile,
			ProxyURL:        scanProxyURL,
			TimeOut:         scanTimeOut,
			RateLimit:       scanRateLimit,
			FPTemplates:     scanFpTemplates,
			AdvTemplates:    scanAdvTemplates,
			ListVulTemplate: scanListVulTemplate,
			CheckVulTargets: scanCheckVulTargets,
			AIAnalysis:      scanAIAnalysis,
			AIHunyuanToken:  scanAIHunyuanToken,
			AIDeepSeekToken: scanAIDeepSeekToken,
			LocalScan:       scanLocalScan,
			Headers:         scanHeaders,
			Language:        scanLanguage,
		}

		// 设置日志级别
		gologger.Logger.SetLevel(gologger.InfoLevel)

		r, err := runner.New(scanOptions)
		if err != nil {
			gologger.Fatalf("Could not create runner: %s\n", err)
		}
		defer r.Close()

		if scanOptions.CheckVulTargets {
			return
		}
		if scanOptions.ListVulTemplate {
			r.ShowFpAndVulList(scanOptions.ListVulTemplate)
			return
		}

		r.RunEnumeration()
	},
}

func init() {
	rootCmd.AddCommand(scanCmd)

	// 设置scan子命令的标志
	scanCmd.Flags().StringArrayVarP(&scanTargets, "target", "t", []string{}, "目标URL，可以指定多个目标，例如: --target xx.com --target aa.com")
	scanCmd.Flags().StringVarP(&scanTargetFile, "file", "f", "", "包含目标URL的文件路径")
	scanCmd.Flags().StringVarP(&scanOutputFile, "output", "o", "", "输出文件路径")
	scanCmd.Flags().IntVar(&scanTimeOut, "timeout", 5, "请求超时时间(秒)")
	scanCmd.Flags().StringVar(&scanProxyURL, "proxy-url", "", "代理服务器URL")
	scanCmd.Flags().StringArrayVar(&scanHeaders, "header", []string{}, "HTTP请求头，可以指定多个，例如: --header \"key:value\" --header \"key:value\"")
	scanCmd.Flags().IntVar(&scanRateLimit, "limit", 200, "每秒最大请求数")
	scanCmd.Flags().StringVar(&scanFpTemplates, "fps", "data/fingerprints", "指纹模板文件或目录")
	scanCmd.Flags().StringVar(&scanAdvTemplates, "vul", "data/vuln", "漏洞数据库目录")
	scanCmd.Flags().BoolVar(&scanListVulTemplate, "list-vul", false, "列出漏洞模板")
	scanCmd.Flags().BoolVar(&scanCheckVulTargets, "check-vul", false, "验证漏洞模板")
	scanCmd.Flags().BoolVar(&scanLocalScan, "localscan", false, "一键本地扫描")
	scanCmd.Flags().BoolVar(&scanAIAnalysis, "ai", false, "启用AI分析")
	scanCmd.Flags().StringVar(&scanAIHunyuanToken, "hunyuan-token", "", "混元API令牌")
	scanCmd.Flags().StringVar(&scanAIDeepSeekToken, "deepseek-token", "", "DeepSeek API令牌")
	scanCmd.Flags().StringVar(&scanLanguage, "lang", "zh", "响应语言 zh/en")
}
