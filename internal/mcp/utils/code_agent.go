package utils

import (
	"context"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"strconv"
	"strings"

	"github.com/Tencent/AI-Infra-Guard/common/utils/models"
	"github.com/Tencent/AI-Infra-Guard/internal/gologger"
)

// AutoGPT is an agent that can automatically execute tasks, similar to AutoGPT functionality
type AutoGPT struct {
	Goals            []string // List of goals that the agent needs to complete
	AutoSure         bool     // Whether to automatically confirm command execution without user confirmation
	MaxIter          int      // Maximum number of iterations
	history          []map[string]string
	MaxFileReadBytes int
	language         string
	folder           string
}

// NewAutoGPT creates a new AutoGPT instance
func NewAutoGPT(goals []string, language string, folder string) *AutoGPT {
	return &AutoGPT{
		Goals:            goals,
		AutoSure:         false,
		MaxIter:          60,
		MaxFileReadBytes: 10 * 1024, // Maximum read size
		language:         language,
		folder:           folder,
	}
}

// userPrompt generates initial system prompt
func (a *AutoGPT) userPrompt(ctx context.Context) string {
	// Build goals string
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
	var infoPrompt string
	if ctx.Value("collection_prompt") != nil {
		infoPrompt = ctx.Value("collection_prompt").(string)
		if infoPrompt != "" {
			infoPrompt = "**Project Info:**\n" + infoPrompt + "\n"
		}
	}
	systemPrompt = fmt.Sprintf(systemPrompt, infoPrompt, goalsStr.String(), LanguagePrompt(a.language))
	return strings.TrimSpace(systemPrompt)
}

// NextPrompt generates next prompt
func (a *AutoGPT) NextPrompt(retMsg string, round int) string {
	return fmt.Sprintf("The current round is the %dth conversation. Please try to minimize the number of exchanges to obtain the result.\n.The returned result is as follows. Please draw your conclusion in the \"reply format\".Determine which next command to use, and respond using the format specified above.\nReturn:%s", round, retMsg)
}

// ExtractTag extracts tag part from text
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

// Command represents command structure returned by LLM
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
			return errors.New("filepath parameter not found, please re-output the command in the format specified")
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
			return errors.New("filepath parameter not found, please re-output the command in the format specified")
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
			return errors.New("filepath parameter not found, please re-output the command in the format specified")
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

// Run runs AutoGPT agent
func (a *AutoGPT) Run(ctx context.Context, aiModel *models.OpenAI, logger *gologger.Logger) (string, error) {
	history := []map[string]string{
		{
			"role":    "user",
			"content": a.userPrompt(ctx),
		},
	}

	// Start main loop
	index := 0
	for {
		if a.MaxIter > 0 && index >= a.MaxIter {
			userPrompt := fmt.Sprintf("Maximum iteration count reached: %d, please complete directly based on history, output command as finish, generate final result", a.MaxIter)
			// Remove last history entry
			if len(history) > 1 {
				history = history[:len(history)-1]
			}
			history = append(history, map[string]string{
				"role":    "user",
				"content": userPrompt,
			})
		}
		logger.Infof("------------------- Round %d -------------------\n", index+1)
		index++

		// Call LLM API to generate response
		m := history
		stream := aiModel.ChatStream(ctx, m)
		msg := ""
		for chunk := range stream {
			logger.Print(chunk)
			msg += chunk
		}
		if msg == "" {
			return "", fmt.Errorf("AI output is empty. Please check for model issues or context limit exceeded")
		}
		logger.Print("\n")
		// Add response to history
		history = append(history, map[string]string{
			"role":    "assistant",
			"content": msg,
		})
		a.history = history

		// Try to parse JSON command
		jsonStr := a.ExtractTag(msg, "command")
		if jsonStr == "" {
			logger.Warningln("Command parsing failed, retrying")
			// JSON parsing failed
			history = append(history, map[string]string{
				"role":    "user",
				"content": "Your command output format is incorrect, please answer based on the previous question and reorganize your command output format as <command><name>command name</name><arg><parameters1>parameter content</parameters1><parameters2>parameter content</parameters2></arg></command> and re-answer",
			})
			continue
		}

		var command Command
		command.Name = a.ExtractTag(jsonStr, "name")
		command.Arg1 = a.ExtractTag(jsonStr, "arg")

		// Check if command format is correct
		if command.Name == "" || (command.Name != "finish" && command.Arg1 == "") {
			history = append(history, map[string]string{
				"role":    "user",
				"content": "Your command output format is incorrect, please answer based on the previous question and reorganize your command output format as <command><name>command name</name><arg><parameters1>parameter content</parameters1><parameters2>parameter content</parameters2></arg></command> and re-answer",
			})
			continue
		}

		logger.Infof("Executing command: %s with args: %s\n", command.Name, command.Arg1)

		// Execute command
		var userPrompt string
		switch command.Name {
		case "list_dir":
			var parameter ListDirParam
			err := a.ParseCommandParam(command.Arg1, &parameter)
			if err != nil {
				userPrompt = fmt.Sprintf("Failed to parse command parameters: %v", err)
				break
			}
			err = a.inFolder(parameter.FilePath)
			if err != nil {
				userPrompt = err.Error()
				break
			}
			data, err := ListDir(parameter.FilePath, parameter.Depth, parameter.Exts)
			if err != nil {
				userPrompt = fmt.Sprintf("Failed to read directory: %v Please confirm if the directory path is correct", err)
			} else {
				userPrompt = fmt.Sprintf("Directory reading completed, dir path:%s\nDir tree:\n%s\n", parameter.FilePath, data)
			}
		case "read_file":
			var parameter ReadFileParam
			err := a.ParseCommandParam(command.Arg1, &parameter)
			if err != nil {
				userPrompt = fmt.Sprintf("Failed to parse command parameters: %v", err)
				break
			}
			err = a.inFolder(parameter.FilePath)
			if err != nil {
				userPrompt = err.Error()
				break
			}
			// Get file information
			fileInfo, err := os.Stat(parameter.FilePath)
			if err != nil {
				logger.WithError(err).Warningln("Failed to read file")
				userPrompt = fmt.Sprintf("Failed to read file %s: %v", parameter.FilePath, err)
				break
			}
			// Check file size, decide how to read
			if fileInfo.Size() < int64(a.MaxFileReadBytes) {
				// Small file, read all at once
				data, err := os.ReadFile(parameter.FilePath)
				if err != nil {
					userPrompt = fmt.Sprintf("Failed to read file: %v", err)
				} else {
					userPrompt = fmt.Sprintf("File reading completed, filename:%s\nfile content:\n%s", parameter.FilePath, string(data))
				}
			} else {
				startline := parameter.StartLine
				endline := parameter.EndLine
				if startline == 0 && endline == 0 {
					startline = 0
					endline = 200
				}
				if endline < startline {
					userPrompt = fmt.Sprintf("endline(%d) cannot be less than startline(%d)", endline, startline)
					break
				}
				// Large file, read in chunks
				content, err := ReadFileChunk(parameter.FilePath, startline, endline, a.MaxFileReadBytes)
				if err != nil {
					userPrompt = fmt.Sprintf("Failed to read file: %v", err)
				} else {
					userPrompt = content
				}
			}
		case "grep":
			var parameter GrepParam
			err := a.ParseCommandParam(command.Arg1, &parameter)
			if err != nil {
				userPrompt = fmt.Sprintf("Failed to parse command parameters: %v", err)
				break
			}
			err = a.inFolder(parameter.FilePath)
			if err != nil {
				userPrompt = err.Error()
				break
			}
			// Execute grep
			results, err := Grep(parameter.FilePath, parameter.Pattern, parameter.Context)
			if err != nil {
				userPrompt = fmt.Sprintf("Search failed: %v", err)
			} else {
				pattern := parameter.Pattern
				patternDesc := strings.Replace(pattern, ",", "', '", -1)
				if strings.Contains(pattern, ",") {
					patternDesc = fmt.Sprintf("['%s']", patternDesc)
				} else {
					patternDesc = fmt.Sprintf("'%s'", pattern)
				}
				userPrompt = fmt.Sprintf("Search results (path: %s, pattern: %s, context lines: %d):\n%s",
					parameter.FilePath, patternDesc, parameter.Context, results)
			}
		case "finish":
			result := command.Arg1
			return result, nil
		default:
			userPrompt = fmt.Sprintf("Unknown command: %s You can only use read_file, list_dir, grep, finish commands", command.Name)
		}
		maxLength := 200
		userPrompt2 := []rune(userPrompt)
		if len(userPrompt2) < maxLength {
			maxLength = len(userPrompt2)
		}
		logger.Infoln("executing result:", string(userPrompt2[:maxLength]), "...")
		// Add user prompt to history
		history = append(history, map[string]string{
			"role":    "user",
			"content": a.NextPrompt(userPrompt, index+1),
		})
		a.history = history
	}
}

func (a *AutoGPT) inFolder(arg1 string) error {
	folder, err := filepath.Abs(arg1)
	if err != nil {
		return errors.New(fmt.Sprintf("Failed to read directory: %v", err))
	}
	if !strings.HasPrefix(folder, a.folder) {
		return errors.New(fmt.Sprintf("Security policy restriction, you cannot read directories outside %s, %s is not in the current directory", a.folder, folder))
	}
	return nil
}
