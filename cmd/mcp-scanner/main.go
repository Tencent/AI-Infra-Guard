package main

import (
	"flag"
	"fmt"
	"os"
	"time"

	"github.com/Tencent/AI-Infra-Guard/internal/gologger"
	"github.com/Tencent/AI-Infra-Guard/internal/mcp"
)

var (
	input   string
	timeout int
	verbose bool
)

func init() {
	flag.StringVar(&input, "input", "", "要检测的MCP输入（命令行、SSE链接或代码文件路径）")
	flag.IntVar(&timeout, "timeout", 60, "检测超时时间（秒）")
	flag.BoolVar(&verbose, "verbose", false, "是否输出详细日志")

	flag.Usage = func() {
		fmt.Fprintf(os.Stderr, "MCP协议安全检测工具\n\n")
		fmt.Fprintf(os.Stderr, "用法: %s [选项]\n\n", os.Args[0])
		fmt.Fprintf(os.Stderr, "选项:\n")
		flag.PrintDefaults()

		fmt.Fprintf(os.Stderr, "\n示例:\n")
		fmt.Fprintf(os.Stderr, "  %s --input 'mcp --port=3000'\n", os.Args[0])
		fmt.Fprintf(os.Stderr, "  %s --input http://example.com/mcp/events\n", os.Args[0])
		fmt.Fprintf(os.Stderr, "  %s --input /path/to/mcp_code.js\n", os.Args[0])
	}
}

func main() {
	flag.Parse()

	if verbose {
		gologger.Logger.SetLevel(gologger.DebugLevel)
	} else {
		gologger.Logger.SetLevel(gologger.InfoLevel)
	}

	if input == "" {
		gologger.Errorln("必须提供--input参数")
		flag.Usage()
		os.Exit(1)
	}

	// 创建MCP检测器
	detector := mcp.NewDetector(time.Duration(timeout) * time.Second)

	// 执行检测
	result, err := detector.DetectInput(input)
	if err != nil {
		gologger.Errorf("检测失败: %v\n", err)
		os.Exit(1)
	}

	// 打印结果
	detector.PrintResults()

	// 根据是否发现安全问题设置退出码
	if len(result.Issues) > 0 {
		os.Exit(2) // 发现安全问题，返回非零退出码
	}
}
