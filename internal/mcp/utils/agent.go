package utils

import (
	"bufio"
	"context"
	"fmt"
	"os"
	"regexp"
	"strings"

	"github.com/Tencent/AI-Infra-Guard/internal/gologger"
	"github.com/Tencent/AI-Infra-Guard/internal/mcp/models"
)

// AutoGPT 是一个代理，可以自动执行任务，类似于AutoGPT功能
type AutoGPT struct {
	Goals    []string // 代理需要完成的目标列表
	AutoSure bool     // 是否自动确认命令执行，无需用户确认
	MaxIter  int      // 最大迭代次数
	// 文件读取相关配置
	MaxFileReadLines int                         // 单次读取文件的最大行数
	MaxFileReadBytes int                         // 单次读取文件的最大字节数
	FileReaderState  map[string]*FileReaderState // 文件读取状态
}

// FileReaderState 保存文件读取的状态
type FileReaderState struct {
	Filename     string // 文件名
	CurrentLine  int    // 当前读取的行号
	LastReadMsg  string // 上次读取的消息
	HistoryIndex int    // 历史记录中对应的索引
}

// NewAutoGPT 创建一个新的AutoGPT实例
func NewAutoGPT(goals []string) *AutoGPT {
	return &AutoGPT{
		Goals:            goals,
		AutoSure:         false,
		MaxIter:          60,
		MaxFileReadLines: 300,       // 默认每次读取100行
		MaxFileReadBytes: 20 * 1024, // 默认每次读取10KB
		FileReaderState:  make(map[string]*FileReaderState),
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
You are an AI agent capable of performing various tasks. Your objective is to accomplish the goals listed below.
All decisions must be made independently without seeking user assistance. Leverage your strengths and employ straightforward, legally compliant strategies.

GOALS:
%s

Performance Evaluation:
1. Continuously review and analyze your actions to ensure you are performing to the best of your abilities.
2. Constructively self-criticize your big-picture behavior constantly.
3. Reflect on past decisions and strategies to refine your approach.
4. Every command has a cost, so be smart and efficient. Aim to complete tasks in the least number of steps.
5. Your main goal is to follow the USER's instructions at each message,Be conversational but professional

You can only use the following commands:

COMMANDS:
1. read_file: Use this tool when you need to read a file. arg is filename must be absolute path. 
2. continue_read: Continue reading the previous file. args: arg is "next" to read next chunk.
3. list_dir: Use this tool when you need to list a directory. arg is dir must be absolute path.
4. grep_file: Search for a pattern in a file and return matching lines with context. arg is <filename>|<pattern>|<context_lines>,filename must be absolute path
5. finish: Triggers completion. The program will return the final vulnerability scan results, which must be valid and wrapped in <arg> tags (e.g., <arg>[RESULT FORMAT]</arg>). If no results, return <arg></arg>.

RESULT FORMAT:
<result>  
  <title>Vulnerability Name</title>  
  <desc>Detailed vulnerability description, including code paths and contextual examples (Markdown format).</desc>  
  <level>Severity level (critical/high/medium/low)</level>  
  <suggestion>Remediation suggestions</suggestion>  
</result>

Limitations:
- You cannot read directories or files outside the specified root directory.
- Your output format must follow the following specifications: Output in the order of conclusion,think,command,criticism,plan.
- Keep realistic and detailed.Don't use fake data or irrelevant information.

Response in chinese.

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

command is next step to use command, must use tag <name></name> and <arg></arg> to specify the command name and parameters.only return one command.
<command>
<name>command name</name>
<arg>parameter,don't need quote</arg>
</command>
`
	systemPrompt = fmt.Sprintf(systemPrompt, goalsStr.String())
	return strings.TrimSpace(systemPrompt)
}

// NextPrompt 生成下一个提示
func (a *AutoGPT) NextPrompt(retMsg string) string {
	return fmt.Sprintf("The returned result is as follows. Please draw your conclusion in the \"conclusion\" part.Determine which next command to use, and respond using the format specified above.\nReturn:%s", retMsg)
}

// ExtractTag 从文本中提取tag部分
func (a *AutoGPT) ExtractTag(text, tag string) string {
	startText := fmt.Sprintf("<%s>", tag)
	endText := fmt.Sprintf("</%s>", tag)
	startIndex := strings.Index(text, startText)
	if startIndex == -1 {
		return ""
	}
	tmp := text[startIndex+len(startText):]
	endIndex := strings.Index(tmp, endText) + startIndex + len(startText)
	if startIndex == -1 || endIndex == -1 || endIndex <= startIndex {
		return ""
	}
	return strings.TrimSpace(text[startIndex+len(startText) : endIndex])
}

// Command 表示LLM返回的命令结构
type Command struct {
	Name string `json:"name"`
	Arg1 string `json:"arg"`
}

// ReadFileChunk 读取文件的一部分
func (a *AutoGPT) ReadFileChunk(filename string, startLine int, maxLines int, maxBytes int) (string, int, error) {
	file, err := os.Open(filename)
	if err != nil {
		return "", 0, err
	}
	defer file.Close()

	scanner := bufio.NewScanner(file)

	// 跳过之前的行
	currentLine := 0
	for currentLine < startLine && scanner.Scan() {
		currentLine++
	}

	// 读取指定的行数或字节数
	var sb strings.Builder
	bytesRead := 0
	linesRead := 0

	for currentLine < startLine+maxLines && scanner.Scan() && bytesRead < maxBytes {
		line := scanner.Text() + "\n"
		sb.WriteString(line)
		bytesRead += len(line)
		linesRead++
		currentLine++
	}

	if err := scanner.Err(); err != nil {
		return "", 0, err
	}

	// 检查是否还有更多内容
	hasMore := scanner.Scan()

	result := sb.String()
	if len(result) > 0 {
		if hasMore {
			result += fmt.Sprintf("\n... (文件还有更多内容，当前已读取到第 %d 行，共读取了 %d 行，约 %d 字节)\n",
				currentLine, linesRead, bytesRead)
		} else {
			result += fmt.Sprintf("\n... (文件已读取完毕，最后一行为第 %d 行)\n", currentLine)
		}
	}

	return result, currentLine, nil
}

// GrepFile 在文件中搜索特定模式并返回匹配行及其上下文
func (a *AutoGPT) GrepFile(filename string, pattern string, contextLines int) (string, error) {
	file, err := os.Open(filename)
	if err != nil {
		return "", err
	}
	defer file.Close()

	// 编译正则表达式
	re, err := regexp.Compile(pattern)
	if err != nil {
		return "", fmt.Errorf("正则表达式无效: %v", err)
	}

	// 读取文件的所有行
	var lines []string
	scanner := bufio.NewScanner(file)
	for scanner.Scan() {
		lines = append(lines, scanner.Text())
	}
	if err := scanner.Err(); err != nil {
		return "", err
	}

	// 搜索匹配行并保存上下文
	var results []string
	for i, line := range lines {
		if re.MatchString(line) {
			// 添加匹配行的上下文
			startLine := i - contextLines
			if startLine < 0 {
				startLine = 0
			}
			endLine := i + contextLines
			if endLine >= len(lines) {
				endLine = len(lines) - 1
			}

			// 添加行号和上下文
			results = append(results, fmt.Sprintf("=== 匹配行 %d ===", i+1))
			for j := startLine; j <= endLine; j++ {
				prefix := "  "
				if j == i {
					prefix = ">"
				}
				results = append(results, fmt.Sprintf("%s %d: %s", prefix, j+1, lines[j]))
			}
			results = append(results, "")
		}
	}

	if len(results) == 0 {
		return fmt.Sprintf("未找到匹配模式 '%s' 的内容", pattern), nil
	}

	return strings.Join(results, "\n"), nil
}

// Run 运行AutoGPT代理
func (a *AutoGPT) Run(ctx context.Context, aiModel *models.OpenAI) (string, error) {
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
			userPrompt := fmt.Sprintf("已达到最大迭代次数: %d,请根据历史记录直接完成，输出command为finish，生成最终结果", a.MaxIter)
			// history删除上一个
			if len(history) > 1 {
				history = history[:len(history)-1]
			}
			history = append(history, map[string]string{
				"role":    "user",
				"content": userPrompt,
			})
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
		if msg == "" {
			return "", fmt.Errorf("ai empty response")
		}
		fmt.Println()

		// 添加响应到历史记录
		history = append(history, map[string]string{
			"role":    "assistant",
			"content": msg,
		})

		// 尝试解析JSON命令
		jsonStr := a.ExtractTag(msg, "command")
		if jsonStr == "" {
			gologger.Warningln("command 解析失败,重新尝试中")
			// JSON解析失败
			history = append(history, map[string]string{
				"role":    "user",
				"content": "你的输出command格式错误,请根据上一个问题回答并重新整理你的输出格式 以<command>整理格式重新回答",
			})
			continue
		}

		var command Command
		command.Name = a.ExtractTag(jsonStr, "name")
		command.Arg1 = a.ExtractTag(jsonStr, "arg")
		if command.Name == "" {
			// JSON解析失败
			history = append(history, map[string]string{
				"role":    "user",
				"content": fmt.Sprintf("你的输出格式错误\n请根据上一个问题回答并重新整理你的输出格式"),
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
			// 获取文件信息
			fileInfo, err := os.Stat(command.Arg1)
			if err != nil {
				gologger.WithError(err).Warningln("读取文件失败")
				userPrompt = fmt.Sprintf("读取文件 %s 失败: %v", command.Arg1, err)
			} else {
				// 检查文件大小，决定如何读取
				if fileInfo.Size() < int64(a.MaxFileReadBytes) {
					// 小文件，直接全部读取
					data, err := os.ReadFile(command.Arg1)
					if err != nil {
						userPrompt = fmt.Sprintf("读取文件失败: %v", err)
					} else {
						userPrompt = fmt.Sprintf("读取文件完成，path:%s\ncontent:%s", command.Arg1, string(data))
					}
				} else {
					// 大文件，分批读取
					content, lastLine, err := a.ReadFileChunk(command.Arg1, 0, a.MaxFileReadLines, a.MaxFileReadBytes)
					if err != nil {
						userPrompt = fmt.Sprintf("读取文件失败: %v", err)
					} else {
						userPrompt = fmt.Sprintf("读取文件部分内容，path:%s\n文件总大小: %d 字节\n内容:\n%s",
							command.Arg1, fileInfo.Size(), content)

						// 保存读取状态，用于继续读取
						a.FileReaderState[command.Arg1] = &FileReaderState{
							Filename:     command.Arg1,
							CurrentLine:  lastLine,
							LastReadMsg:  userPrompt,
							HistoryIndex: len(history) + 1, // +1 因为我们还没有添加这个提示到历史
						}
					}
				}
			}

		case "continue_read":
			// 获取上次读取的文件
			var lastFile string
			for filename := range a.FileReaderState {
				lastFile = filename
				break
			}

			if lastFile == "" {
				userPrompt = "没有找到之前读取的文件记录"
			} else {
				state := a.FileReaderState[lastFile]

				// 从历史记录中删除上一次读取的消息
				if state.HistoryIndex >= 0 && state.HistoryIndex < len(history) {
					// 从历史记录中删除而不是更新，避免历史太长
					historyLen := len(history)
					if historyLen > state.HistoryIndex+1 {
						history = append(history[:state.HistoryIndex], history[state.HistoryIndex+1:]...)
					}
				}

				// 继续读取文件
				content, lastLine, err := a.ReadFileChunk(lastFile, state.CurrentLine, a.MaxFileReadLines, a.MaxFileReadBytes)
				if err != nil {
					userPrompt = fmt.Sprintf("继续读取文件失败: %v", err)
				} else {
					userPrompt = fmt.Sprintf("继续读取文件 %s (从第 %d 行开始):\n%s",
						lastFile, state.CurrentLine+1, content)

					// 更新状态
					state.CurrentLine = lastLine
					state.LastReadMsg = userPrompt
					state.HistoryIndex = len(history) + 1
				}
			}

		case "grep_file":
			// 解析参数: filename|pattern|context_lines
			args := strings.Split(command.Arg1, "|")
			if len(args) < 2 {
				userPrompt = "grep_file 命令格式错误，正确格式: filename|pattern|context_lines"
			} else {
				filename := args[0]
				pattern := args[1]

				contextLines := 3 // 默认值
				if len(args) > 2 {
					fmt.Sscanf(args[2], "%d", &contextLines)
				}

				// 执行grep
				results, err := a.GrepFile(filename, pattern, contextLines)
				if err != nil {
					userPrompt = fmt.Sprintf("在文件中搜索失败: %v", err)
				} else {
					userPrompt = fmt.Sprintf("在文件 %s 中搜索 '%s' (上下文行数: %d):\n%s",
						filename, pattern, contextLines, results)
				}
			}

		case "finish":
			fmt.Println("任务完成")
			result := command.Arg1
			return result, nil
		default:
			userPrompt = fmt.Sprintf("未知命令：%s 你只能使用 read_file, continue_read, list_dir, grep_file, finish 命令", command.Name)
		}

		// 添加用户提示到历史记录
		history = append(history, map[string]string{
			"role":    "user",
			"content": a.NextPrompt(userPrompt),
		})
	}
}
