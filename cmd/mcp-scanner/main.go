package main

import (
	"context"
	"flag"
	"fmt"
	"os"
	"strings"

	"github.com/Tencent/AI-Infra-Guard/internal/gologger"
	"github.com/Tencent/AI-Infra-Guard/internal/mcp"
	"github.com/Tencent/AI-Infra-Guard/internal/mcp/models"
	"gopkg.in/yaml.v3"
)

type Config struct {
	Model   string `yaml:"model"`
	Type    string `yaml:"type"`
	Token   string `yaml:"token"`
	BaseURL string `yaml:"base_url"`
}

func main() {
	// 定义命令行参数
	configFile := flag.String("config", "", "配置文件路径 (YAML 格式)")
	codePath := flag.String("code", "", "源代码路径")
	sseLink := flag.String("sse", "", "SSE 链接")
	streamLink := flag.String("stream", "", "Stream 链接")
	cmdName := flag.String("cmd", "", "命令行名称")
	cmdArgs := flag.String("args", "", "命令行参数，用英文逗号分隔")

	flag.Parse()

	// 检查参数
	if *configFile == "" {
		gologger.Fatalf("请提供配置文件路径 (-config)")
	}

	if *codePath == "" && *sseLink == "" && *streamLink == "" && *cmdName == "" {
		gologger.Fatalf("请至少提供以下一种输入：源代码路径 (-code)、SSE 链接 (-sse)、Stream 链接 (-stream) 或命令行 (-cmd)")
	}

	// 读取配置文件
	config, err := readConfig(*configFile)
	if err != nil {
		gologger.Fatalf("读取配置文件失败: %v", err)
	}

	// 创建 AI 模型
	var aiModel models.AIModel
	switch strings.ToLower(config.Type) {
	case "hunyuan":
		aiModel = models.NewHunyuanAI(config.Token, config.Model, config.BaseURL)
	case "openai":
		aiModel = models.NewOpenAI(config.Token, config.Model, config.BaseURL)
	default:
		gologger.Fatalf("不支持的模型类型: %s", config.Type)
	}

	// 创建扫描器
	scanner := mcp.NewScanner(aiModel)
	scanner.RegisterPlugin()

	// 设置输入
	ctx := context.Background()
	if *codePath != "" {
		err = scanner.InputCodePath(*codePath)
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
	issues, err := scanner.Scan(ctx)
	if err != nil {
		gologger.Fatalf("扫描失败: %v", err)
	}

	// 输出结果
	if len(issues) == 0 {
		gologger.Infof("没有发现问题")
	} else {
		gologger.Infof("发现 %d 个问题:", len(issues))
		for i, issue := range issues {
			fmt.Printf("问题 %d:\n", i+1)
			fmt.Printf("  - 标题: %s\n", issue.Title)
			fmt.Printf("  - 等级: %s\n", issue.Level)
			fmt.Printf("  - 描述: %s\n", issue.Description)
			fmt.Printf("  - 建议修复: %s\n\n", issue.Suggestion)
		}
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
