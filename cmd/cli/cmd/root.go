// Package cmd 实现命令行界面
package cmd

import (
	"github.com/Tencent/AI-Infra-Guard/internal/gologger"
	"github.com/Tencent/AI-Infra-Guard/internal/options"
	"github.com/spf13/cobra"
)

// rootCmd 表示基础命令
var rootCmd = &cobra.Command{
	Use:   "ai-infra-guard",
	Short: "AI基础设施安全检测工具",
	Long:  `AI-Infra-Guard是一个针对AI基础设施的安全检测工具，包含扫描、MCP检测功能,支持webui操作。`,
}

// Execute 添加所有子命令到根命令并设置标志
// 这由main.main()调用，仅调用一次
func Execute() {
	options.ShowBanner()
	if err := rootCmd.Execute(); err != nil {
		gologger.Fatalf("执行命令失败: %s\n", err.Error())
	}
}

func init() {
	// 在这里，您可以定义根命令的标志和配置设置
	// Cobra支持持久性标志，如果在这里定义的话，它们将对所有子命令可用
	// rootCmd.PersistentFlags().StringVar(&cfgFile, "config", "", "config file (default is $HOME/.cobra.yaml)")

	// Cobra也支持本地标志，只在直接调用此操作时运行
	// rootCmd.Flags().BoolP("toggle", "t", false, "Help message for toggle")
}
