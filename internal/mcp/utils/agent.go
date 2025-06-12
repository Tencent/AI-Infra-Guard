package utils

import (
	"context"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"strconv"
	"strings"

	"github.com/Tencent/AI-Infra-Guard/internal/gologger"
	"github.com/Tencent/AI-Infra-Guard/internal/mcp/models"
)

// AutoGPT 是一个代理，可以自动执行任务，类似于AutoGPT功能
type AutoGPT struct {
	Goals            []string // 代理需要完成的目标列表
	AutoSure         bool     // 是否自动确认命令执行，无需用户确认
	MaxIter          int      // 最大迭代次数
	history          []map[string]string
	MaxFileReadBytes int
	language         string
	folder           string
}

// FileReaderState 保存文件读取的状态
type FileReaderState struct {
	Filename     string // 文件名
	CurrentLine  int    // 当前读取的行号
	LastReadMsg  string // 上次读取的消息
	HistoryIndex int    // 历史记录中对应的索引
}

// NewAutoGPT 创建一个新的AutoGPT实例
func NewAutoGPT(goals []string, language string, folder string) *AutoGPT {
	return &AutoGPT{
		Goals:            goals,
		AutoSure:         false,
		MaxIter:          60,
		MaxFileReadBytes: 10 * 1024, // 最大读取
		language:         language,
		folder:           folder,
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

You have access to the following tools. Use them precisely when needed:
You have access to the following tools. Use them precisely when needed:

1.  Command: read_file
       Purpose: Read the content of a file. IMPORTANT: Due to resource limitations, this tool may only return a PARTIAL file segment (i.e., specific line range). You will be informed of the total number of lines and the current read line range. You MUST evaluate if further reads are needed to complete the task and issue subsequent read_file commands accordingly.Determine the file size. If it is less than 5KB, the entire file can be read. If reading line by line, it is recommended to read 200 lines.
       Parameters:
           filepath (string, required): Absolute path to the file.
           startline (integer, optional): Starting line number (0-indexed). Default is 0.
           endline (integer, optional): Ending line number (inclusive). Default is 0.

2.  Command: list_dir
       Purpose: List the contents of a directory. Can filter using regex.
       Parameters:
           filepath (string, required): Absolute path to the directory.
           depth (integer, optional): Recursion depth. 1 lists only immediate children, -1 lists all recursively. Default is 3.
           exts (string, optional): Only retrieve specified suffixes, separate multiple ones with commas, e.g.: .txt,.md,leave empty for no suffix restrictions,default is empty.Unless you want to get a specific file, it is recommended to leave it blank to read all files.

3.  Command: grep
       Purpose: Search file(s) for lines matching a regular expression pattern. Can search a single file or all files in a directory recursively. Outputs matching lines with surrounding context.
       Parameters:
           filepath (string, required): Absolute path to the target file or directory.
           regex (string, required): Regular expression pattern to search for.
           contextline (integer, optional): Number of context lines to display above and below each match. Default is 3.

4.  Command: finish
       Purpose: Signal task completion. Call this command ONLY when you are certain that the user's GOALS have been fully and perfectly executed. This command terminates the process.
       Parameters: None.

Command Format:
<command>
<name>command name</name>
<arg>
	<parameters name>parameter content</parameters name>
	<parameters name>parameter content</parameters name>
</arg>
</command>

For example:
<command>
<name>read_file</name>
<arg>
	<filepath>/path/to/file.txt</filepath>
	<startline>1</startline>
	<endline>10</endline>
</arg>
</command>

Limitations:
- You cannot read directories or files outside the specified root directory.
- Your output format must follow the following specifications: Output in the order of conclusion,think,command,criticism,plan.
- Keep realistic and detailed.Don't use fake data or irrelevant information.

Please output your response in the reply format, and then output the next command in the command format.%s

Reply FORMAT:
Your response includes five aspects: [Integration Phase: Consolidate key information from dialogue history, user feedback, and system observations to generate actionable conclusions], [Distributed Reasoning: Break down complex problems into sequential thinking steps, using weighted indicators to evaluate solution feasibility], [Strategic Basis: Explain decision criteria based on an evidence chain, comparing alternatives through cost-benefit analysis], [Critical Reflection: Conduct a SWOT analysis of the current strategy, proposing three improvement directions with specific examples], and [Action Blueprint: Define next-step goals using the SMART principle, clarifying success criteria and risk responses]. Then provide the response instruction: the command is the next step to use the command, must use the tags and to specify the command name and parameters. Only return one command.
`
	var infoPromtp string
	if ctx.Value("collection_prompt") != nil {
		infoPromtp = ctx.Value("collection_prompt").(string)
		if infoPromtp != "" {
			infoPromtp = "项目概览:\n" + infoPromtp
		}
	}
	systemPrompt = fmt.Sprintf(systemPrompt, infoPromtp, goalsStr.String(), LanguagePrompt(a.language))
	return strings.TrimSpace(systemPrompt)
}

// NextPrompt 生成下一个提示
func (a *AutoGPT) NextPrompt(retMsg string) string {
	return fmt.Sprintf("The returned result is as follows. Please draw your conclusion in the \"reply format\".Determine which next command to use, and respond using the format specified above.\nReturn:%s", retMsg)
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
	if strings.Index(tmp, endText) == -1 {
		return ""
	}
	endIndex := strings.Index(tmp, endText) + startIndex + len(startText)
	if startIndex == -1 || endIndex == -1 || endIndex <= startIndex {
		return ""
	}
	return strings.TrimSpace(text[startIndex+len(startText) : endIndex])
}

// Command 表示LLM返回的命令结构
type Command struct {
	Name string
	Arg1 string
}

type ReadFileParam struct {
	FilePath  string
	StartLine int
	EndLine   int
}

type ListDirParam struct {
	FilePath string
	Depth    int
	Exts     string
}

type GrepParam struct {
	FilePath string
	Pattern  string
	Context  int
}

type FinishParam struct {
}

func (a *AutoGPT) ParseCommandParam(arg string, param interface{}) error {
	if arg == "" {
		return errors.New("empty command")
	}
	switch param := param.(type) {
	case *ReadFileParam:
		param.FilePath = a.ExtractTag(arg, "filepath")
		if param.FilePath == "" {
			return errors.New("filepath参数未找到，请按照command格式重新输出")
		}
		param.StartLine = 0
		param.EndLine = 0
		startarg := a.ExtractTag(arg, "startline")
		endarg := a.ExtractTag(arg, "endline")
		if startarg != "" && endarg != "" {
			startliene, err := strconv.Atoi(startarg)
			if err != nil {
				return err
			}
			endline, err := strconv.Atoi(endarg)
			if err != nil {
				return err
			}
			param.StartLine = startliene
			param.EndLine = endline
		}
	case *ListDirParam:
		param.FilePath = a.ExtractTag(arg, "filepath")
		if param.FilePath == "" {
			return errors.New("filepath参数未找到，请按照command格式重新输出")
		}
		param.Depth = 3
		param.Exts = a.ExtractTag(arg, "exts")
		depthArg := a.ExtractTag(arg, "depth")
		if depthArg != "" {
			depth, err := strconv.Atoi(depthArg)
			if err != nil {
				return err
			}
			param.Depth = depth
		}
	case *GrepParam:
		param.FilePath = a.ExtractTag(arg, "filepath")
		if param.FilePath == "" {
			return errors.New("filepath参数未找到，请按照command格式重新输出")
		}
		param.Pattern = a.ExtractTag(arg, "regex")
		param.Pattern = strings.Replace(param.Pattern, "&lt;", "<", -1)
		param.Pattern = strings.Replace(param.Pattern, "&gt;", ">", -1)
		param.Context = 3
		contextArg := a.ExtractTag(arg, "contextline")
		if contextArg != "" {
			context2, err := strconv.Atoi(contextArg)
			if err != nil {
				return err
			}
			param.Context = context2
		}
	case *FinishParam:
	}
	return nil
}

func (a *AutoGPT) GetHistory() []map[string]string {
	return a.history
}

// Run 运行AutoGPT代理
func (a *AutoGPT) Run(ctx context.Context, aiModel *models.OpenAI, logger *gologger.Logger) (string, error) {
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
		logger.Infof("------------------- 第%d轮 -------------------\n", index+1)
		index++

		// 调用LLM API生成响应
		m := history
		stream := aiModel.ChatStream(ctx, m)
		msg := ""
		for chunk := range stream {
			logger.Print(chunk)
			msg += chunk
		}
		if msg == "" {
			return "", fmt.Errorf("ai empty response")
		}
		logger.Print("\n")
		// 添加响应到历史记录
		history = append(history, map[string]string{
			"role":    "assistant",
			"content": msg,
		})
		a.history = history

		// 尝试解析JSON命令
		jsonStr := a.ExtractTag(msg, "command")
		if jsonStr == "" {
			logger.Warningln("command 解析失败,重新尝试中")
			// JSON解析失败
			history = append(history, map[string]string{
				"role":    "user",
				"content": "你的输出command格式错误,请根据上一个问题回答并重新整理你的command输出格式 以 <command><name>command name</name><arg><parameters1>parameter content</parameters1><parameters2>parameter content</parameters2></arg></command> 整理格式重新回答",
			})
			continue
		}

		var command Command
		command.Name = a.ExtractTag(jsonStr, "name")
		command.Arg1 = a.ExtractTag(jsonStr, "arg")

		// 检查命令格式是否正确
		if command.Name == "" || (command.Name != "finish" && command.Arg1 == "") {
			history = append(history, map[string]string{
				"role":    "user",
				"content": "你的输出command格式错误,请根据上一个问题回答并重新整理你的command输出格式,以 <command><name>command name</name><arg><parameters1>parameter content</parameters1><parameters2>parameter content</parameters2></arg></command> 整理格式重新回答",
			})
			continue
		}

		logger.Infof("Executing command: %s with args: %s\n", command.Name, command.Arg1)

		// 执行命令
		var userPrompt string
		switch command.Name {
		case "list_dir":
			var parameter ListDirParam
			err := a.ParseCommandParam(command.Arg1, &parameter)
			if err != nil {
				userPrompt = fmt.Sprintf("解析command参数失败: %v", err)
				break
			}
			err = a.inFolder(parameter.FilePath)
			if err != nil {
				userPrompt = err.Error()
				break
			}
			data, err := ListDir(parameter.FilePath, parameter.Depth, parameter.Exts)
			if err != nil {
				userPrompt = fmt.Sprintf("读取目录失败: %v 请确认目录路径是否正确", err)
			} else {
				userPrompt = fmt.Sprintf("读取目录完成，dir path:%s\nDir tree:\n%s\n", parameter.FilePath, data)
			}
		case "read_file":
			var parameter ReadFileParam
			err := a.ParseCommandParam(command.Arg1, &parameter)
			if err != nil {
				userPrompt = fmt.Sprintf("解析command参数失败: %v", err)
				break
			}
			err = a.inFolder(parameter.FilePath)
			if err != nil {
				userPrompt = err.Error()
				break
			}
			// 获取文件信息
			fileInfo, err := os.Stat(parameter.FilePath)
			if err != nil {
				logger.WithError(err).Warningln("读取文件失败")
				userPrompt = fmt.Sprintf("读取文件 %s 失败: %v", parameter.FilePath, err)
				break
			}
			// 检查文件大小，决定如何读取
			if fileInfo.Size() < int64(a.MaxFileReadBytes) {
				// 小文件，直接全部读取
				data, err := os.ReadFile(parameter.FilePath)
				if err != nil {
					userPrompt = fmt.Sprintf("读取文件失败: %v", err)
				} else {
					userPrompt = fmt.Sprintf("读取文件完成，filename:%s\nfile content:\n%s", parameter.FilePath, string(data))
				}
			} else {
				startline := parameter.StartLine
				endline := parameter.EndLine
				if startline == 0 && endline == 0 {
					startline = 0
					endline = 200
				}
				if endline < startline {
					userPrompt = fmt.Sprintf("endline(%d)不能小于startline(%d)", endline, startline)
					break
				}
				// 大文件，分批读取
				content, err := ReadFileChunk(parameter.FilePath, startline, endline, a.MaxFileReadBytes)
				if err != nil {
					userPrompt = fmt.Sprintf("读取文件失败: %v", err)
				} else {
					userPrompt = content
				}
			}
		case "grep":
			var parameter GrepParam
			err := a.ParseCommandParam(command.Arg1, &parameter)
			if err != nil {
				userPrompt = fmt.Sprintf("解析command参数失败: %v", err)
				break
			}
			err = a.inFolder(parameter.FilePath)
			if err != nil {
				userPrompt = err.Error()
				break
			}
			// 执行grep
			results, err := Grep(parameter.FilePath, parameter.Pattern, parameter.Context)
			if err != nil {
				userPrompt = fmt.Sprintf("搜索失败: %v", err)
			} else {
				pattern := parameter.Pattern
				patternDesc := strings.Replace(pattern, ",", "', '", -1)
				if strings.Contains(pattern, ",") {
					patternDesc = fmt.Sprintf("['%s']", patternDesc)
				} else {
					patternDesc = fmt.Sprintf("'%s'", pattern)
				}
				userPrompt = fmt.Sprintf("搜索结果 (路径: %s, 模式: %s, 上下文行数: %d):\n%s",
					parameter.FilePath, patternDesc, parameter.Context, results)
			}
		case "finish":
			result := command.Arg1
			return result, nil
		default:
			userPrompt = fmt.Sprintf("未知命令：%s 你只能使用 read_file, list_dir, grep, finish 命令", command.Name)
		}
		maxLength := 200
		userPrompt2 := []rune(userPrompt)
		if len(userPrompt2) < maxLength {
			maxLength = len(userPrompt2)
		}
		logger.Infoln("executing result:", string(userPrompt2[:maxLength]), "...")
		// 添加用户提示到历史记录
		history = append(history, map[string]string{
			"role":    "user",
			"content": a.NextPrompt(userPrompt),
		})
		a.history = history
	}
}

func (a *AutoGPT) inFolder(arg1 string) error {
	folder, err := filepath.Abs(arg1)
	if err != nil {
		return errors.New(fmt.Sprintf("读取目录失败: %v", err))
	}
	if !strings.HasPrefix(folder, a.folder) {
		return errors.New(fmt.Sprintf("安全策略限制，你无法读取%s之外目录, %s 不在当前目录下", a.folder, folder))
	}
	return nil
}
