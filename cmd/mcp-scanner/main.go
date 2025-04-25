package main

import (
	"context"
	"encoding/csv"
	"encoding/json"
	"flag"
	"fmt"
	"io"
	"log"
	"os"
	"path/filepath"
	"strings"

	"github.com/Tencent/AI-Infra-Guard/internal/gologger"
	"github.com/Tencent/AI-Infra-Guard/internal/mcp"
	"github.com/Tencent/AI-Infra-Guard/internal/mcp/models"
	"gopkg.in/yaml.v3"
)

type Config struct {
	Model   string `yaml:"model"`
	Token   string `yaml:"token"`
	BaseURL string `yaml:"base_url"`
	Plugins string `yaml:"plugins"`
}

func main() {
	// 定义命令行参数
	configFile := flag.String("config", "", "配置文件路径 (YAML 格式)")
	codePath := flag.String("code", "", "源代码路径")
	sseLink := flag.String("sse", "", "SSE 链接")
	streamLink := flag.String("stream", "", "Stream 链接")
	cmdName := flag.String("cmd", "", "命令行名称")
	cmdArgs := flag.String("args", "", "命令行参数，用英文逗号分隔")
	logArg := flag.String("log", "", "日志保存路径")
	csvArg := flag.String("csv", "", "输出 CSV 文件路径")
	jsonArg := flag.String("json", "", "输出 JSON 文件路径")

	flag.Parse()

	if *logArg != "" {
		writer1 := os.Stdout
		writer2, err := os.OpenFile(*logArg, os.O_WRONLY|os.O_APPEND|os.O_CREATE, 0644)
		defer writer2.Close()
		if err != nil {
			log.Fatalf("create file log.txt failed: %v", err)
		}
		gologger.Logger.SetOutput(io.MultiWriter(writer1, writer2))
	}
	// 检查参数
	if *configFile == "" {
		gologger.Fatalf("请提供配置文件路径 (-config)")
	}

	if *codePath == "" {
		gologger.Fatalf("请至少提供以下一种输入：源代码路径 (-code)")
	}

	// 读取配置文件
	config, err := readConfig(*configFile)
	if err != nil {
		gologger.Fatalf("读取配置文件失败: %v", err)
	}

	// 创建 AI 模型
	aiModel := models.NewOpenAI(config.Token, config.Model, config.BaseURL)

	// 创建扫描器
	scanner := mcp.NewScanner(aiModel)
	scanner.RegisterPlugin(strings.Split(config.Plugins, ","))

	// 设置输入
	ctx := context.Background()
	if *codePath != "" {
		filename, err := filepath.Abs(*codePath)
		if err != nil {
			gologger.Errorln("获取文件路径失败: %v", err)
			filename = *codePath
		}
		gologger.Infof("设置代码路径: %s", filename)
		err = scanner.InputCodePath(filename)
		if err != nil {
			gologger.Fatalf("设置代码路径失败: %v", err)
		}
	}

	if *sseLink != "" {
		err = scanner.InputSSELink(ctx, *sseLink)
		if err != nil {
			gologger.Fatalf("设置 SSE 链接失败: %v", err)
		}
	}

	if *streamLink != "" {
		err = scanner.InputStreamLink(ctx, *streamLink)
		if err != nil {
			gologger.Fatalf("设置 Stream 链接失败: %v", err)
		}
	}

	if *cmdName != "" {
		args := []string{}
		if *cmdArgs != "" {
			args = strings.Split(*cmdArgs, ",")
		}
		err = scanner.InputCommand(ctx, *cmdName, args)
		if err != nil {
			gologger.Fatalf("设置命令行失败: %v", err)
		}
	}

	// 执行扫描
	gologger.Infof("开始扫描...")
	results, err := scanner.Scan(ctx)
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
	if *jsonArg != "" {
		dd, err := json.Marshal(results)
		if err != nil {
			gologger.Errorf("输出 JSON 失败: %v", err)
		} else {
			err = os.WriteFile(*jsonArg, dd, 0644)
			if err != nil {
				gologger.Errorf("保存 JSON 失败: %v", err)
			}
			gologger.Infoln("输出 JSON 文件成功")
		}
	}
	if *csvArg != "" {
		//OpenFile读取文件，不存在时则创建，使用追加模式
		File, err := os.OpenFile(*csvArg, os.O_RDWR|os.O_APPEND|os.O_CREATE, 0666)
		if err != nil {
			log.Println("文件打开失败！")
		}
		defer File.Close()

		//创建写入接口
		WriterCsv := csv.NewWriter(File)
		for _, item := range scanner.GetCsvResult() {
			WriterCsv.Write(item)
			WriterCsv.Flush()
		}
		WriterCsv.Write([]string{})
		lines := []string{"pluginID", "title", "desc", "level", "suggestion"} //需要写入csv的数据，切片类型
		err1 := WriterCsv.Write(lines)
		if err1 != nil {
			gologger.WithError(err1).Error("写入csv文件失败")
		}
		WriterCsv.Flush() //刷新，不刷新是无法写入的
		for _, issue := range results {
			lines = []string{issue.PluginId, issue.Title, issue.Description, string(issue.Level), issue.Suggestion} //需要写入csv的数据，切片类型
			err1 = WriterCsv.Write(lines)
			if err1 != nil {
				gologger.WithError(err1).Error("写入csv文件失败")
			}
			WriterCsv.Flush() //刷新，不刷新是无法写入的
		}
		gologger.Infoln("输出CSV文件成功")
	}
}

func readConfig(path string) (*Config, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, fmt.Errorf("读取文件失败: %w", err)
	}

	var config Config
	if err := yaml.Unmarshal(data, &config); err != nil {
		return nil, fmt.Errorf("解析YAML失败: %w", err)
	}

	return &config, nil
}
