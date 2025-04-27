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
	history          []map[string]string
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
func (a *AutoGPT) userPrompt(ctx context.Context) string {
	// 构建目标字符串
	var goalsStr strings.Builder
	for _, goal := range a.Goals {
		goalsStr.WriteString(fmt.Sprintf("%s\n", goal))
	}

	systemPrompt := `
You are an AI agent capable of performing various tasks. Your objective is to accomplish the goals listed below.
All decisions must be made independently without seeking user assistance. Leverage your strengths and employ straightforward, legally compliant strategies.
%s

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
4. grep: Search for a pattern in a file or directory and return matching lines with context. arg is <path>#<pattern1,pattern2,...>#<context_lines>, path can be a file or directory with absolute path. Multiple patterns can be separated by commas.
5. finish: When the GOALS are completed, trigger the finish command to indicate that the task has been perfectly executed. arg is "finish"

Limitations:
- You cannot read directories or files outside the specified root directory.
- Your output format must follow the following specifications: Output in the order of conclusion,think,command,criticism,plan.
- Keep realistic and detailed.Don't use fake data or irrelevant information.

Response in chinese.

RESPONSE FORMAT:
Your response includes five aspects: [Integration Phase: Consolidate key information from dialogue history, user feedback, and system observations to generate actionable conclusions], [Distributed Reasoning: Break down complex problems into sequential thinking steps, using weighted indicators to evaluate solution feasibility], [Strategic Basis: Explain decision criteria based on an evidence chain, comparing alternatives through cost-benefit analysis], [Critical Reflection: Conduct a SWOT analysis of the current strategy, proposing three improvement directions with specific examples], and [Action Blueprint: Define next-step goals using the SMART principle, clarifying success criteria and risk responses]. Then provide the response instruction: the command is the next step to use the command, must use the tags and to specify the command name and parameters. Only return one command.
Command Format:
<command>
<name>command name</name>
<arg>parameter,don't need quote</arg>
</command>
`
	var infoPromtp string
	if ctx.Value("collection_prompt") != nil {
		infoPromtp = ctx.Value("collection_prompt").(string)
		if infoPromtp != "" {
			infoPromtp = "项目概览:\n" + infoPromtp
		}
	}
	systemPrompt = fmt.Sprintf(systemPrompt, infoPromtp, goalsStr.String())
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

// Grep 在文件或目录中搜索特定模式并返回匹配行及其上下文
func (a *AutoGPT) Grep(path string, pattern string, contextLines int) (string, error) {
	// 检查路径是文件还是目录
	fileInfo, err := os.Stat(path)
	if err != nil {
		return "", err
	}

	// 支持多个表达式，通过逗号分隔
	patterns := strings.Split(pattern, ",")
	if len(patterns) == 0 {
		return "", fmt.Errorf("未提供搜索模式")
	}

	// 编译所有正则表达式
	regexps := make([]*regexp.Regexp, 0, len(patterns))
	for _, p := range patterns {
		p = strings.TrimSpace(p)
		if p == "" {
			continue
		}
		re, err := regexp.Compile(p)
		if err != nil {
			return "", fmt.Errorf("正则表达式无效 '%s': %v", p, err)
		}
		regexps = append(regexps, re)
	}

	if len(regexps) == 0 {
		return "", fmt.Errorf("没有有效的正则表达式")
	}

	var results []string
	if fileInfo.IsDir() {
		// 如果是目录，遍历目录中的所有文件
		patternStr := strings.Join(patterns, "', '")
		results = append(results, fmt.Sprintf("在目录 '%s' 中搜索模式 ['%s']:\n", path, patternStr))
		err = a.grepDirectoryMulti(path, regexps, contextLines, &results)
		if err != nil {
			return "", err
		}
	} else {
		// 如果是文件，直接搜索文件
		fileResults, err := a.grepFileMulti(path, regexps, contextLines)
		if err != nil {
			return "", err
		}
		if fileResults != "" {
			results = append(results, fmt.Sprintf("文件: %s\n", path))
			results = append(results, fileResults)
		}
	}

	if len(results) == 0 || (len(results) == 1 && strings.HasPrefix(results[0], "在目录")) {
		patternStr := strings.Join(patterns, "', '")
		return fmt.Sprintf("未找到匹配模式 ['%s'] 的内容", patternStr), nil
	}

	return strings.Join(results, "\n"), nil
}

// grepDirectoryMulti 在目录中搜索多个模式
func (a *AutoGPT) grepDirectoryMulti(dirPath string, regexps []*regexp.Regexp, contextLines int, results *[]string) error {
	entries, err := os.ReadDir(dirPath)
	if err != nil {
		return err
	}

	foundMatches := false
	for _, entry := range entries {
		entryPath := fmt.Sprintf("%s/%s", dirPath, entry.Name())

		// 跳过隐藏文件和目录
		if strings.HasPrefix(entry.Name(), ".") {
			continue
		}

		if entry.IsDir() {
			// 递归搜索子目录
			err := a.grepDirectoryMulti(entryPath, regexps, contextLines, results)
			if err != nil {
				// 只记录错误，继续处理其他文件
				*results = append(*results, fmt.Sprintf("搜索目录 %s 时出错: %v", entryPath, err))
			}
		} else {
			// 只处理常见文本文件类型
			if isTextFile(entry.Name()) {
				fileResults, err := a.grepFileMulti(entryPath, regexps, contextLines)
				if err != nil {
					// 只记录错误，继续处理其他文件
					continue
				}

				if fileResults != "" {
					if !foundMatches {
						foundMatches = true
					}
					*results = append(*results, fmt.Sprintf("\n文件: %s", entryPath))
					*results = append(*results, fileResults)
				}
			}
		}
	}

	return nil
}

// grepFileMulti 在单个文件中搜索多个模式
func (a *AutoGPT) grepFileMulti(filename string, regexps []*regexp.Regexp, contextLines int) (string, error) {
	file, err := os.Open(filename)
	if err != nil {
		return "", err
	}
	defer file.Close()

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
	matchFound := false
	matchedLines := make(map[int]bool) // 记录哪些行已经匹配过，避免重复

	// 对每个正则表达式进行匹配
	for _, re := range regexps {
		for i, line := range lines {
			if re.MatchString(line) && !matchedLines[i] {
				matchFound = true
				matchedLines[i] = true

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
	}

	if !matchFound {
		return "", nil
	}

	return strings.Join(results, "\n"), nil
}

// isTextFile 检查文件是否为文本文件
func isTextFile(filename string) bool {
	// 常见文本文件扩展名
	textExtensions := []string{
		".txt", ".md", ".go", ".py", ".js", ".ts", ".html", ".css",
		".json", ".xml", ".yaml", ".yml", ".toml", ".ini", ".conf",
		".c", ".cpp", ".h", ".hpp", ".java", ".sh", ".bat", ".ps1",
		".php", ".rb", ".rs", ".swift", ".kt", ".scala", ".sql",
	}

	lowerFilename := strings.ToLower(filename)

	for _, ext := range textExtensions {
		if strings.HasSuffix(lowerFilename, ext) {
			return true
		}
	}

	return false
}

// GrepFile 保留旧函数作为兼容层，内部调用新的Grep函数
func (a *AutoGPT) GrepFile(filename string, pattern string, contextLines int) (string, error) {
	return a.Grep(filename, pattern, contextLines)
}

func (a *AutoGPT) GetHistory() []map[string]string {
	return a.history
}

// Run 运行AutoGPT代理
func (a *AutoGPT) Run(ctx context.Context, aiModel *models.OpenAI) (string, error) {
	history := []map[string]string{
		{
			"role":    "user",
			"content": a.userPrompt(ctx),
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
		gologger.Infof("------------------- 第%d轮 -------------------\n", index+1)
		index++

		// 调用LLM API生成响应
		m := history
		stream := aiModel.ChatStream(ctx, m)
		msg := ""
		for chunk := range stream {
			gologger.Print(chunk)
			msg += chunk
		}
		if msg == "" {
			return "", fmt.Errorf("ai empty response")
		}
		gologger.Print("\n")
		// 添加响应到历史记录
		history = append(history, map[string]string{
			"role":    "assistant",
			"content": msg,
		})
		a.history = history

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
				"content": fmt.Sprintf("你的输出格式错误\n请根据上一个问题回答并重新整理你的输出格式,你需要保证输出<command></command>标签以及<name></name>标签"),
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

		gologger.Infof("Executing command: %s with args: %s\n", command.Name, command.Arg1)

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

		case "grep":
			// 解析参数: path#pattern1,pattern2,pattern3#context_lines
			args := strings.Split(command.Arg1, "#")
			if len(args) < 2 {
				userPrompt = "grep 命令格式错误，正确格式: path#pattern1,pattern2,pattern3#context_lines"
			} else {
				path := args[0]
				pattern := args[1]

				contextLines := 3 // 默认值
				if len(args) > 2 {
					fmt.Sscanf(args[2], "%d", &contextLines)
				}

				// 执行grep
				results, err := a.Grep(path, pattern, contextLines)
				if err != nil {
					userPrompt = fmt.Sprintf("搜索失败: %v", err)
				} else {
					patternDesc := strings.Replace(pattern, ",", "', '", -1)
					if strings.Contains(pattern, ",") {
						patternDesc = fmt.Sprintf("['%s']", patternDesc)
					} else {
						patternDesc = fmt.Sprintf("'%s'", pattern)
					}
					userPrompt = fmt.Sprintf("搜索结果 (路径: %s, 模式: %s, 上下文行数: %d):\n%s",
						path, patternDesc, contextLines, results)
				}
			}

		case "finish":
			gologger.Infoln("任务完成")
			result := command.Arg1
			return result, nil
		default:
			userPrompt = fmt.Sprintf("未知命令：%s 你只能使用 read_file, continue_read, list_dir, grep, finish 命令", command.Name)
		}
		maxLength := 200
		if len(userPrompt) < maxLength {
			maxLength = len(userPrompt)
		}
		gologger.Infoln("executing result:", userPrompt[:maxLength], "...")
		// 添加用户提示到历史记录
		history = append(history, map[string]string{
			"role":    "user",
			"content": a.NextPrompt(userPrompt),
		})
		a.history = history
	}
}

// grepFile 在单个文件中搜索特定模式 (兼容旧版本)
func (a *AutoGPT) grepFile(filename string, re *regexp.Regexp, contextLines int) (string, error) {
	// 使用新的多模式搜索函数
	return a.grepFileMulti(filename, []*regexp.Regexp{re}, contextLines)
}

// grepDirectory 在目录中搜索特定模式 (兼容旧版本)
func (a *AutoGPT) grepDirectory(dirPath string, re *regexp.Regexp, contextLines int, results *[]string) error {
	// 使用新的多模式搜索函数
	return a.grepDirectoryMulti(dirPath, []*regexp.Regexp{re}, contextLines, results)
}
