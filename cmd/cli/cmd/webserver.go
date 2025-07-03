package cmd

import (
	"github.com/Tencent/AI-Infra-Guard/common/websocket"
	"github.com/Tencent/AI-Infra-Guard/internal/options"
	"github.com/spf13/cobra"
)

// 为webserverCmd定义标志变量
var (
	webServerAddr string
)

// webserverCmd 表示webserver子命令
var webserverCmd = &cobra.Command{
	Use:   "webserver",
	Short: "启动Web服务器",
	Long:  `启动Web服务器功能，提供Web界面进行扫描。`,
	Run: func(cmd *cobra.Command, args []string) {
		// 创建Options对象
		webOptions := &options.Options{
			TimeOut:       10,
			RateLimit:     200,
			FPTemplates:   "data/fingerprints",
			AdvTemplates:  "data/vuln",
			WebServer:     true,
			WebServerAddr: webServerAddr,
		}
		// 设置日志级别
		websocket.RunWebServer(webOptions)
	},
}

func init() {
	rootCmd.AddCommand(webserverCmd)

	// 设置webserver子命令的标志
	webserverCmd.Flags().StringVar(&webServerAddr, "ws-addr", "0.0.0.0:8088", "WebSocket服务器地址")
}
