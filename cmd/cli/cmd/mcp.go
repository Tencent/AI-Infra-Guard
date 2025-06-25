package cmd

import (
	"context"
	"encoding/csv"
	"encoding/json"
	"fmt"
	"github.com/Tencent/AI-Infra-Guard/internal/gologger"
	"github.com/Tencent/AI-Infra-Guard/internal/mcp"
	"github.com/Tencent/AI-Infra-Guard/internal/mcp/models"
	"github.com/spf13/cobra"
	"io"
	"log"
	"os"
	"path/filepath"
)

var (
	mcpCodePath   string
	mcpSseLink    string
	mcpStreamLink string
	mcpCmdName    string
	mcpCmdArgs    string
	mcpLogPath    string
	mcpCsvPath    string
	mcpJsonPath   string
	mcpModel      string
	mcpToken      string
	mcpBaseURL    string
	mcpPlugins    string
)

// mcpCmd 表示mcp子命令
var mcpCmd = &cobra.Command{
	Use:   "mcp",
	Short: "MCP扫描",
	Long:  `MCP Server扫描，检测MCP代码的安全性。`,
	Run: func(cmd *cobra.Command, args []string) {
		// 设置日志级别
		logger := gologger.NewLogger()

		if mcpLogPath != "" {
			writer1 := os.Stdout
			writer2, err := os.OpenFile(mcpLogPath, os.O_WRONLY|os.O_APPEND|os.O_CREATE, 0644)
			if err != nil {
				log.Fatalf("create file log.txt failed: %v", err)
			}
			defer writer2.Close()
			logger.Logrus().SetOutput(io.MultiWriter(writer1, writer2))
		}

		// 检查必要参数
		if mcpCodePath == "" {
			gologger.Fatalf("请提供源代码路径 (--code)")
		}

		// if mcpToken == "" {
		// 	gologger.Fatalf("请提供API令牌 (--token)")
		// }

		// if mcpModel == "" {
		// 	gologger.Fatalf("请提供模型名称 (--model)")
		// }

		// 创建 AI 模型
		aiModel := models.NewOpenAI(mcpToken, mcpModel, mcpBaseURL)

		// 创建扫描器
		scanner := mcp.NewScanner(aiModel, logger)

		// 设置输入
		ctx := context.Background()
		if mcpCodePath != "" {
			filename, err := filepath.Abs(mcpCodePath)
			if err != nil {
				gologger.Errorf("获取文件路径失败: %v", err)
				filename = mcpCodePath
			}
			gologger.Infof("设置代码路径: %s", filename)
			err = scanner.InputCodePath(filename)
			if err != nil {
				gologger.Fatalf("设置代码路径失败: %v", err)
			}
		}

		// if mcpSseLink != "" {
		// 	err := scanner.InputSSELink(ctx, mcpSseLink)
		// 	if err != nil {
		// 		gologger.Fatalf("设置 SSE 链接失败: %v", err)
		// 	}
		// }

		// if mcpStreamLink != "" {
		// 	err := scanner.InputStreamLink(ctx, mcpStreamLink)
		// 	if err != nil {
		// 		gologger.Fatalf("设置 Stream 链接失败: %v", err)
		// 	}
		// }

		// if mcpCmdName != "" {
		// 	cmdArgs := []string{}
		// 	if mcpCmdArgs != "" {
		// 		cmdArgs = strings.Split(mcpCmdArgs, ",")
		// 	}
		// 	err := scanner.InputCommand(ctx, mcpCmdName, cmdArgs)
		// 	if err != nil {
		// 		gologger.Fatalf("设置命令行失败: %v", err)
		// 	}
		// }

		// 执行扫描
		gologger.Infof("开始扫描...")
		results, err := scanner.ScanCode(ctx, false)
		if err != nil {
			gologger.Fatalf("扫描失败: %v", err)
		}

		// 输出结果
		gologger.Infof("发现 %d 个问题:", len(results))
		for i, issue := range results {
			fmt.Printf("问题 %d:\n", i+1)
			fmt.Printf("  - 标题: %s\n", issue.Title)
			fmt.Printf("  - 等级: %s\n", issue.Level)
			fmt.Printf("  - 描述: %s\n", issue.Description)
			fmt.Printf("  - 建议修复: %s\n\n", issue.Suggestion)
		}

		if mcpJsonPath != "" {
			dd, err := json.Marshal(results)
			if err != nil {
				gologger.Errorf("输出 JSON 失败: %v", err)
			} else {
				err = os.WriteFile(mcpJsonPath, dd, 0644)
				if err != nil {
					gologger.Errorf("保存 JSON 失败: %v", err)
				}
				gologger.Infoln("输出 JSON 文件成功")
			}
		}

		if mcpCsvPath != "" {
			File, err := os.OpenFile(mcpCsvPath, os.O_RDWR|os.O_APPEND|os.O_CREATE, 0666)
			if err != nil {
				log.Println("文件打开失败！")
			}
			defer File.Close()

			WriterCsv := csv.NewWriter(File)
			for _, item := range scanner.GetCsvResult() {
				WriterCsv.Write(item)
				WriterCsv.Flush()
			}
			WriterCsv.Write([]string{})
			lines := []string{"pluginID", "title", "desc", "level", "suggestion"}
			err1 := WriterCsv.Write(lines)
			if err1 != nil {
				gologger.WithError(err1).Error("写入csv文件失败")
			}
			WriterCsv.Flush()
			for _, issue := range results {
				lines = []string{issue.PluginId, issue.Title, issue.Description, string(issue.Level), issue.Suggestion}
				err1 = WriterCsv.Write(lines)
				if err1 != nil {
					gologger.WithError(err1).Error("写入csv文件失败")
				}
				WriterCsv.Flush()
			}
			gologger.Infoln("输出CSV文件成功")
		}
	},
}

func init() {
	rootCmd.AddCommand(mcpCmd)

	// 设置MCP子命令的标志
	mcpCmd.Flags().StringVar(&mcpCodePath, "code", "", "源代码路径")
	// mcpCmd.Flags().StringVar(&mcpSseLink, "sse", "", "SSE 链接")
	// mcpCmd.Flags().StringVar(&mcpStreamLink, "stream", "", "Stream 链接")
	// mcpCmd.Flags().StringVar(&mcpCmdName, "cmd", "", "命令行名称")
	// mcpCmd.Flags().StringVar(&mcpCmdArgs, "args", "", "命令行参数，用英文逗号分隔")
	mcpCmd.Flags().StringVar(&mcpLogPath, "log", "", "日志保存路径")
	mcpCmd.Flags().StringVar(&mcpCsvPath, "csv", "", "输出 CSV 文件路径")
	mcpCmd.Flags().StringVar(&mcpJsonPath, "json", "", "输出 JSON 文件路径")

	// 添加原来在YAML配置中的参数
	mcpCmd.Flags().StringVar(&mcpModel, "model", "", "AI模型名称")
	mcpCmd.Flags().StringVar(&mcpToken, "token", "", "API令牌")
	mcpCmd.Flags().StringVar(&mcpBaseURL, "base-url", "", "API基础URL")
	mcpCmd.Flags().StringVar(&mcpPlugins, "plugins", "auth_bypass,cmd_injection,credential_theft,hardcoded_api_key,indirect_prompt_injection,name_confusion,rug_pull,tool_poisoning,tool_shadowing", "插件列表，用英文逗号分隔")
}
