package utils

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"strings"

	"github.com/Tencent/AI-Infra-Guard/common/utils/models"
	"github.com/Tencent/AI-Infra-Guard/internal/gologger"
	"github.com/mark3labs/mcp-go/client"
	"github.com/mark3labs/mcp-go/mcp"
)

// AutoWEBGPT is an agent that can automatically execute tasks, similar to AutoWEBGPT functionality
type AutoWEBGPT struct {
	MaxIter  int // Maximum number of iterations
	history  []map[string]string
	language string
}

// NewAutoWEBGPT creates a new AutoWEBGPT instance
func NewAutoWEBGPT(language string) *AutoWEBGPT {
	return &AutoWEBGPT{
		MaxIter:  60,
		history:  make([]map[string]string, 0),
		language: language,
	}
}

type CallTool struct {
	Name      string
	Parameter string
}

// userPrompt generates initial system prompt
func (a *AutoWEBGPT) userPrompt(ctx context.Context, goals string) string {
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

Command: call_tool
   Purpose: Invoke a specified tool to execute commands.
   Parameters:
       name (string, required): Name of the tool to be called.
       arg (json string, required): Input parameters for the target tool, formatted as a valid JSON object. Must contain all required arguments for the specified tool.

Command: finish
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
<name>call_tool</name>
<arg>
	<name>get_content_file</name>
	<param>{"url":"http://example.com"}</param>
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
	systemPrompt = fmt.Sprintf(systemPrompt, infoPrompt, goals, LanguagePrompt(a.language))

	return strings.TrimSpace(systemPrompt)
}

// NextPrompt generates next prompt
func (a *AutoWEBGPT) NextPrompt(retMsg string, round int) string {
	return fmt.Sprintf("The current round is the %dth conversation. Please try to minimize the number of exchanges to obtain the result.\n.The returned result is as follows. Please draw your conclusion in the \"reply format\".Determine which next command to use, and respond using the format specified above.\nReturn:%s", round, retMsg)
}

// ExtractTag extracts tag part from text
func (a *AutoWEBGPT) ExtractTag(text, tag string) string {
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

func (a *AutoWEBGPT) ParseCommandParam(arg string, param interface{}) error {
	if arg == "" {
		return errors.New("empty command")
	}
	switch param := param.(type) {
	case *CallTool:
		param.Name = a.ExtractTag(arg, "name")
		param.Parameter = a.ExtractTag(arg, "param")
	case *FinishParam:
	}
	return nil
}

func (a *AutoWEBGPT) GetHistory() []map[string]string {
	return a.history
}

// Run runs AutoWEBGPT agent
func (a *AutoWEBGPT) Run(ctx context.Context, aiModel *models.OpenAI, logger *gologger.Logger, client *client.Client, prompt string) (string, error) {
	history := []map[string]string{
		{
			"role":    "user",
			"content": a.userPrompt(ctx, prompt),
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
		case "finish":
			result := command.Arg1
			return result, nil
		case "call_tool":
			var callTool CallTool
			err := a.ParseCommandParam(command.Arg1, &callTool)
			if err != nil {
				userPrompt = fmt.Sprintf("Command format error: %s, please re-answer", err.Error())
				continue
			}
			arg := make(map[string]interface{})
			err = json.Unmarshal([]byte(callTool.Parameter), &arg)
			if err != nil {
				userPrompt = fmt.Sprintf("Command format error: %s, please re-answer", err.Error())
				continue
			}
			result, err := client.CallTool(ctx, mcp.CallToolRequest{
				Params: mcp.CallToolParams{
					Name:      callTool.Name,
					Arguments: arg,
				},
			})
			if err != nil {
				userPrompt = fmt.Sprintf("Command execution error: %s, please re-answer", err.Error())
				continue
			}
			if len(result.Content) > 0 {
				c := result.Content[0]
				switch c.(type) {
				case mcp.TextContent:
					userPrompt = fmt.Sprintf("Command execution result: %s", c.(mcp.TextContent).Text)
				default:
					userPrompt = fmt.Sprintf("Command execution result: %v", c)
				}
			} else {
				userPrompt = "Command execution result: empty"
			}
		default:
			userPrompt = fmt.Sprintf("Unknown command: %s You can only use finish commands", command.Name)
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
