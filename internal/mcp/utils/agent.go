package utils

import (
	"context"
	"encoding/json"
	"fmt"
	"github.com/Tencent/AI-Infra-Guard/internal/gologger"
	"github.com/Tencent/AI-Infra-Guard/internal/mcp/models"
	"os"
	"strings"
)

// AutoGPT 是一个代理，可以自动执行任务，类似于AutoGPT功能
type AutoGPT struct {
	Goals        []string // 代理需要完成的目标列表
	ResultFormat string
	AutoSure     bool // 是否自动确认命令执行，无需用户确认
	MaxIter      int  // 最大迭代次数
}

// NewAutoGPT 创建一个新的AutoGPT实例
func NewAutoGPT(goals []string, resultFormat string) *AutoGPT {
	return &AutoGPT{
		Goals:        goals,
		ResultFormat: resultFormat,
		AutoSure:     false,
		MaxIter:      200,
	}
}

// userPrompt 生成初始系统提示
func (a *AutoGPT) userPrompt() string {
	// 构建目标字符串
	var goalsStr strings.Builder
	for _, goal := range a.Goals {
		goalsStr.WriteString(fmt.Sprintf("- %s\n", goal))
	}

	systemPrompt := `
Your decisions must always be made independently without seeking user assistance. Play to your strengths and pursue simple strategies with no legal complications.

GOALS:
%s

Performance Evaluation:
1. Continuously review and analyze your actions to ensure you are performing to the best of your abilities.
2. Constructively self-criticize your big-picture behavior constantly.
3. Reflect on past decisions and strategies to refine your approach.
4. Every command has a cost, so be smart and efficient. Aim to complete tasks in the least number of steps.

You can only use the following commands:

COMMANDS:
1. read_file: Use this tool when you need to read a file. args: "arg": "<filename>", filename must be absolute path.
2. list_dir: Use this tool when you need to list a directory. args: "arg": "<dir>", dir must be absolute path.
3. finish: Complete the task at hand and report back results.if task can't finish,you can return "". args: "arg": "<result format>"

Your output format must follow the following specifications: Output in the order of conclusion,think,command,criticism,plan.
Keep realistic and detailed.Don't use fake data or irrelevant information.
The command should be in JSON format and can only contain a name field and a code field.

Response in chinese.

RESULT FORMAT:
%s

RESPONSE FORMAT:
## conclusion
Extract key information from the previous round, and user responses to generate a rich and detailed conclusion.
## think
Think step by step about the next actions.
## reason
Explain why you chose a certain command or strategy.
## criticism
Critique your mistakes, offer suggestions for improvement, and always be goal-oriented.
## plan
Plan the next step.
## command
` + "```command\n" + `
{
    "name": "<command name>",
    "arg": "<arg>"
}
` + "`"
	systemPrompt = fmt.Sprintf(systemPrompt, goalsStr.String(), a.ResultFormat)
	return strings.TrimSpace(systemPrompt)
}

// NextPrompt 生成下一个提示
func (a *AutoGPT) NextPrompt(retMsg string) string {
	return fmt.Sprintf("The returned result is as follows. Please draw your conclusion in the \"conclusion\" part.Determine which next command to use, and respond using the format specified above.\nReturn:%s", retMsg)
}

// ExtractJSON 从文本中提取JSON部分
func (a *AutoGPT) ExtractJSON(text string) string {
	startIndex := strings.Index(text, "```command")
	tmp := text[startIndex+len("```command"):]
	endIndex := strings.Index(tmp, "```") + startIndex + len("```command")
	if startIndex == -1 || endIndex == -1 || endIndex <= startIndex {
		return ""
	}
	return strings.TrimSpace(text[startIndex+len("```command") : endIndex])
}

// Command 表示LLM返回的命令结构
type Command struct {
	Name string `json:"name"`
	Arg1 string `json:"arg"`
}

// Run 运行AutoGPT代理
func (a *AutoGPT) Run(ctx context.Context, aiModel models.AIModel) (string, error) {
	history := []map[string]string{
		{
			"role":    "user",
			"content": a.userPrompt(),
		},
	}

	// 开始主循环
	index := 0
	for {
		if a.MaxIter > 0 && index >= a.MaxIter {
			return "", fmt.Errorf("maximum iteration reached")
		}
		fmt.Printf("------------------- 第%d轮 -------------------\n", index+1)
		index++

		// 调用LLM API生成响应
		m := history
		stream := aiModel.ChatStream(ctx, m)
		msg := ""
		for chunk := range stream {
			fmt.Print(chunk)
			msg += chunk
		}
		fmt.Println()

		// 添加响应到历史记录
		history = append(history, map[string]string{
			"role":    "assistant",
			"content": msg,
		})

		// 尝试解析JSON命令
		jsonStr := a.ExtractJSON(msg)
		if jsonStr == "" {
			gologger.Warningln("JSON解析失败,重新尝试中")
			// JSON解析失败
			history = append(history, map[string]string{
				"role":    "user",
				"content": "你的输出json格式错误,请根据上一个问题回答并重新整理你的输出格式",
			})
			continue
		}

		var command Command
		if err := json.Unmarshal([]byte(jsonStr), &command); err != nil {
			// JSON解析失败
			history = append(history, map[string]string{
				"role":    "user",
				"content": fmt.Sprintf("你的输出json格式错误Error decoding JSON: %v\n\n请根据上一个问题回答并重新整理你的输出格式", err),
			})
			continue
		}

		// 检查命令格式是否正确
		if command.Name == "" || (command.Name != "finish" && command.Arg1 == "") {
			history = append(history, map[string]string{
				"role":    "user",
				"content": "你的输出json格式错误，正确是command->code 请根据上一个问题回答并重新整理你的输出格式",
			})
			continue
		}

		fmt.Printf("Executing command: %s with args: %s\n", command.Name, command.Arg1)

		// 执行命令
		var userPrompt string
		switch command.Name {
		case "list_dir":
			data, err := os.ReadDir(command.Arg1)
			if err != nil {
				userPrompt = fmt.Sprintf("读取目录失败: %v", err)
			} else {
				userPrompt = fmt.Sprintf("读取目录完成，path:%s\n", command.Arg1)
			}
			for _, file := range data {
				userPrompt += fmt.Sprintf("- %s (%s)\n", file.Name(), file.Type())
			}

		case "read_file":
			data, err := os.ReadFile(command.Arg1)
			if err != nil {
				userPrompt = fmt.Sprintf("读取文件失败: %v", err)
			} else {
				userPrompt = fmt.Sprintf("读取文件完成，path:%s\ncontent:%s", command.Arg1, string(data))
			}

		case "finish":
			fmt.Println("任务完成")
			result := command.Arg1
			return result, nil
		default:
			userPrompt = fmt.Sprintf("未知命令：%s 你只能使用 read_file list_dir finish命令", command.Name)
		}

		// 添加用户提示到历史记录
		history = append(history, map[string]string{
			"role":    "user",
			"content": a.NextPrompt(userPrompt),
		})
	}
}
