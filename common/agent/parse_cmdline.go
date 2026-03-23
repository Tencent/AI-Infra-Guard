package agent

import (
	"encoding/json"
	"fmt"
	"path"

	"github.com/Tencent/AI-Infra-Guard/common/utils"
	"github.com/Tencent/AI-Infra-Guard/internal/gologger"
	"github.com/google/uuid"
)

type CmdNewPlanStep struct {
	Title  string `json:"title"`
	StepId string `json:"stepId"`
}

type CmdStatusUpdate struct {
	Brief       string `json:"brief"`
	Description string `json:"description"`
	StepId      string `json:"stepId"`
	Status      string `json:"status"`
}

type CmdToolUsed struct {
	ToolId   string `json:"tool_id"`
	ToolName string `json:"tool_name"`
	Brief    string `json:"brief"`
	Status   string `json:"status"`
	StepId   string `json:"stepId"`
	Params   string `json:"params,omitempty"`
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

type CmdConfig struct {
	StatusId string
	Status   string
}

type PromptContent struct {
	Results    []PromptResults `json:"results"`
	Total      int             `json:"total"`
	Score      float32         `json:"score"`
	Attachment string          `json:"attachment"`
	Jailbreak  int             `json:"jailbreak"`
}
type PromptResults struct {
	Status        string `json:"status"`
	ModelName     string `json:"modelName"`
	Vulnerability string `json:"vulnerability"`
	AttackMethod  string `json:"attackMethod"`
	Input         string `json:"input"`
	Output        string `json:"output"`
	Reason        string `json:"reason"`
}

func ParseStdoutLine(server, rootDir string, tasks []SubTask, line string, callbacks TaskCallbacks, config *CmdConfig, upload bool) {
	var cmd CmdContent
	if len(line) > 1 {
		if line[0] == '{' {
			if err := json.Unmarshal([]byte(line), &cmd); err != nil {
				fmt.Println(line)
				return
			}
		} else {
			fmt.Println(line)
			return
		}
	} else {
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
		for i, v := range tasks {
			if v.Status == SubTaskStatusDone {
				continue
			} else {
				if v.StepId == content.StepId {
					tasks[i].Status = SubTaskStatusDoing
					if i > 0 {
						for j := 0; j < i; j++ {
							tasks[j].Status = SubTaskStatusDone
						}
					}
				}
			}
		}
		callbacks.PlanUpdateCallback(tasks)
	case AgentMsgTypeStatusUpdate:
		var content CmdStatusUpdate
		if err := json.Unmarshal(cmd.Content, &content); err != nil {
			gologger.WithError(err).Errorln("Failed to AgentMsgTypeStatusUpdate unmarshal command", cmd.Content)
			return
		}
		if content.Status == AgentStatusRunning {
			config.StatusId = uuid.NewString()
			config.Status = "running"
		} else if content.Status == AgentStatusCompleted {
			if config.Status == "completed" {
				config.StatusId = uuid.NewString()
			}
			config.Status = "completed"
		}
		callbacks.StepStatusUpdateCallback(content.StepId, config.StatusId, content.Status, content.Brief, content.Description)
	case AgentMsgTypeToolUsed:
		var content CmdToolUsed
		if err := json.Unmarshal(cmd.Content, &content); err != nil {
			gologger.WithError(err).Errorln("Failed to AgentMsgTypeToolUsed unmarshal command", cmd.Content)
			return
		}
		tool := CreateTool(content.ToolId, content.ToolId, statusString(content.Status), content.Brief, content.Brief, "", content.Params)
		callbacks.ToolUsedCallback(content.StepId, config.StatusId, content.Brief, []Tool{tool})
	case AgentMsgTypeActionLog:
		var content CmdActionLog
		if err := json.Unmarshal(cmd.Content, &content); err != nil {
			gologger.WithError(err).Errorln("Failed to AgentMsgTypeActionLog unmarshal command", cmd.Content)
			return
		}
		callbacks.ToolUseLogCallback(content.ToolId, content.ToolName, content.StepId, content.Log)
	case AgentMsgTypeResultUpdate:
		for i, _ := range tasks {
			tasks[i].Status = SubTaskStatusDone
		}
		callbacks.PlanUpdateCallback(tasks)
		var content map[string]interface{}
		if err := json.Unmarshal(cmd.Content, &content); err != nil {
			gologger.WithError(err).Errorln("Failed to AgentMsgTypeResultUpdate unmarshal command", cmd.Content)
			return
		}
		if upload {
			var ret []map[string]interface{}
			dd, err := json.Marshal(content["content"])
			if err != nil {
				gologger.WithError(err).Errorln("Failed to parse result file json")
				return
			}
			if err := json.Unmarshal(dd, &ret); err != nil {
				gologger.WithError(err).Errorln("Failed to parse result file")
				return
			}
			gologger.Infoln("开始上传文件")
			for i, v := range ret {
				attachment, ok := v["attachment"]
				if !ok || attachment == "" {
					continue
				}
				info, err := utils.UploadFile(server, path.Join(rootDir, attachment.(string)))
				if err != nil {
					gologger.WithError(err).Errorln("Failed to upload file")
					return
				}
				gologger.Infoln("上传文件成功")
				v["attachment"] = info.Data.FileUrl
				ret[i] = v
			}
			dd, err = json.Marshal(ret)
			if err != nil {
				gologger.WithError(err).Errorln("Failed to parse result file json")
				return
			}
			var content2 []map[string]interface{}
			if err := json.Unmarshal(dd, &content2); err != nil {
				gologger.WithError(err).Errorln("Failed to parse result file json")
				return
			}
			content["content"] = content2
		}
		callbacks.ResultCallback(content)
	case AgentMsgTypeError:
		content := string(cmd.Content)
		callbacks.ErrorCallback(content)
	}
}
