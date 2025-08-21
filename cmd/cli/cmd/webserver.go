package cmd

import (
	"strings"

	"github.com/Tencent/AI-Infra-Guard/common/websocket"
	"github.com/Tencent/AI-Infra-Guard/internal/gologger"
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
		if !strings.Contains(webServerAddr, "127.0.0.1") {
			gologger.Infoln("请注意，Web服务器监听地址为本地IP,外部用户可访问，可能会导致安全风险，请确保在安全的网络环境下运行。")
		}
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
	webserverCmd.Flags().StringVar(&webServerAddr, "server", "127.0.0.1:8088", "WebSocket服务器地址")
}
