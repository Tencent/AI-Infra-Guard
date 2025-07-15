package agent

import (
	"encoding/json"
	"fmt"
	"github.com/google/uuid"
	"os"

	"github.com/Tencent/AI-Infra-Guard/internal/gologger"
)

type CmdNewPlanStep struct {
	Title  string `json:"title"`
	StepId string `json:"stepId"`
}

type CmdStatusUpdate struct {
	Brief       string `json:"brief"`
	Description string `json:"description"`
	StepId      string `json:"stepId"`
}

type CmdToolUsed struct {
	ToolId   string `json:"tool_id"`
	ToolName string `json:"tool_name"`
	Brief    string `json:"brief"`
	Status   string `json:"status"`
	StepId   string `json:"stepId"`
}

type CmdActionLog struct {
	ToolId   string `json:"tool_id"`
	ToolName string `json:"tool_name"`
	Log      string `json:"log"`
	StepId   string `json:"stepId"`
}

type CmdContent struct {
	Type    string          `json:"type"`
	Content json.RawMessage `json:"content"`
}

var statusId string

func ParseStdoutLine(tasks []SubTask, line string, callbacks TaskCallbacks) {
	var cmd CmdContent
	if err := json.Unmarshal([]byte(line), &cmd); err != nil {
		fmt.Println(line)
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
		// 更新任务状态
		for i, _ := range tasks {
			if tasks[i].StepId < content.StepId {
				tasks[i].Status = SubTaskStatusDone
			} else if tasks[i].StepId == content.StepId {
				tasks[i].Status = SubTaskStatusDoing
			}
		}
		callbacks.PlanUpdateCallback(tasks)
	case AgentMsgTypeStatusUpdate:
		var content CmdStatusUpdate
		if err := json.Unmarshal(cmd.Content, &content); err != nil {
			gologger.WithError(err).Errorln("Failed to AgentMsgTypeStatusUpdate unmarshal command", cmd.Content)
			return
		}
		statusId = uuid.NewString()
		callbacks.StepStatusUpdateCallback(content.StepId, statusId, AgentStatusCompleted, content.Brief, content.Description)
	case AgentMsgTypeToolUsed:
		var content CmdToolUsed
		if err := json.Unmarshal(cmd.Content, &content); err != nil {
			gologger.WithError(err).Errorln("Failed to AgentMsgTypeToolUsed unmarshal command", cmd.Content)
			return
		}
		tool := CreateTool(content.ToolId, content.ToolId, statusString(content.Status), content.Brief, content.Brief, "", "")
		callbacks.ToolUsedCallback(content.StepId, statusId, content.Brief, []Tool{tool})
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
		for i, _ := range tasks {
			tasks[i].Status = SubTaskStatusDone
		}
		callbacks.PlanUpdateCallback(tasks)

		content["msgType"] = "markdown"
		filename := content["content"].(string)
		data, err := os.ReadFile(filename)
		if err != nil {
			gologger.WithError(err).Errorln("Failed to read result file", filename)
			return
		}
		content["content"] = string(data)
		callbacks.ResultCallback(content)
	}
}
