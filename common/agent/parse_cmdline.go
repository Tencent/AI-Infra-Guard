package agent

import (
	"encoding/json"

	"github.com/Tencent/AI-Infra-Guard/internal/gologger"
)

type CmdNewPlanStep struct {
	StepId string `json:"stepId"`
	Title  string `json:"title"`
}

type CmdStatusUpdate struct {
	StepId      string `json:"stepId"`
	Brief       string `json:"brief"`
	Description string `json:"description"`
}

type CmdToolUsed struct {
	StepId   string `json:"stepId"`
	ToolId   string `json:"tool_id"`
	ToolName string `json:"tool_name"`
	Brief    string `json:"brief"`
	Status   string `json:"status"`
}

type CmdActionLog struct {
	ToolId   string `json:"tool_id"`
	ToolName string `json:"tool_name"`
	StepId   string `json:"stepId"`
	Log      string `json:"log"`
}

type CmdContent struct {
	Type    string          `json:"type"`
	Content json.RawMessage `json:"content"`
}

func ParseStdoutLine(planId string, line string, callbacks TaskCallbacks) {
	var cmd CmdContent
	if err := json.Unmarshal([]byte(line), &cmd); err != nil {
		gologger.WithError(err).Errorln("Failed to parse stdout line", line)
		return
	}
	switch cmd.Type {
	case AgentMsgTypeNewPlanStep:
		var content CmdNewPlanStep
		if err := json.Unmarshal(cmd.Content, &content); err != nil {
			gologger.WithError(err).Errorln("Failed to AgentMsgTypeNewPlanStep unmarshal command", cmd.Content)
			return
		}
		callbacks.NewPlanStepCallback(content.StepId, content.Title)
	case AgentMsgTypeStatusUpdate:
		var content CmdStatusUpdate
		if err := json.Unmarshal(cmd.Content, &content); err != nil {
			gologger.WithError(err).Errorln("Failed to AgentMsgTypeStatusUpdate unmarshal command", cmd.Content)
			return
		}
		callbacks.StepStatusUpdateCallback(planId, content.StepId, AgentStatusCompleted, content.Brief, content.Description)
	case AgentMsgTypeToolUsed:
		var content CmdToolUsed
		if err := json.Unmarshal(cmd.Content, &content); err != nil {
			gologger.WithError(err).Errorln("Failed to AgentMsgTypeToolUsed unmarshal command", cmd.Content)
			return
		}
		tool := CreateTool(content.ToolId, content.ToolName, statusString(content.Status), content.Brief, "", "", "")
		callbacks.ToolUsedCallback(planId, content.StepId, content.Brief, []Tool{tool})
	case AgentMsgTypeActionLog:
		var content CmdActionLog
		if err := json.Unmarshal(cmd.Content, &content); err != nil {
			gologger.WithError(err).Errorln("Failed to AgentMsgTypeActionLog unmarshal command", cmd.Content)
			return
		}
		callbacks.ToolUseLogCallback(content.ToolId, content.ToolName, content.StepId, content.Log)
	case AgentMsgTypeResultUpdate:
		var content map[string]interface{}
		if err := json.Unmarshal(cmd.Content, &content); err != nil {
			gologger.WithError(err).Errorln("Failed to AgentMsgTypeResultUpdate unmarshal command", cmd.Content)
			return
		}
		callbacks.ResultCallback(content)
	}
}
