package agent

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"strconv"

	"github.com/Tencent/AI-Infra-Guard/common/utils"
)

const AgentScanDir = "/app/agent-scan"

type AgentTask struct {
	Server string
}

func (m *AgentTask) GetName() string {
	return TaskTypeAgentScan
}

func (m *AgentTask) Execute(ctx context.Context, request TaskRequest, callbacks TaskCallbacks) error {
	type EvalModel struct {
		Model         string `json:"model"`
		ApiKey        string `json:"token"`
		BaseUrl       string `json:"base_url"`
		MaxConcurrent int    `json:"limit"`
	}

	type AgentScanParams struct {
		AgentData string    `json:"agent_data"` // yaml content from dispatchTask
		EvalModel EvalModel `json:"eval_model"`
	}

	var params AgentScanParams
	if err := json.Unmarshal(request.Params, &params); err != nil {
		return err
	}

	// Validate required fields
	if params.AgentData == "" {
		return errors.New("agent_data is required")
	}
	if params.EvalModel.Model == "" {
		return errors.New("eval_model.model is required")
	}
	if params.EvalModel.ApiKey == "" {
		return errors.New("eval_model.token is required")
	}
	if params.EvalModel.BaseUrl == "" {
		return errors.New("eval_model.base_url is required")
	}

	// Set default max_concurrent
	if params.EvalModel.MaxConcurrent == 0 {
		params.EvalModel.MaxConcurrent = 10
	}

	// Create temp file for agent provider yaml
	tmpFile, err := os.CreateTemp("", "agent_provider_*.yaml")
	if err != nil {
		return fmt.Errorf("failed to create temp file: %v", err)
	}
	defer os.Remove(tmpFile.Name())

	if _, err := tmpFile.WriteString(params.AgentData); err != nil {
		tmpFile.Close()
		return fmt.Errorf("failed to write agent config: %v", err)
	}
	tmpFile.Close()

	// Get language
	language := request.Language
	if language == "" {
		language = "zh"
	}

	// Build command arguments
	var argv []string
	argv = append(argv, "run", "main.py")
	argv = append(argv, "-m", params.EvalModel.Model)
	argv = append(argv, "-k", params.EvalModel.ApiKey)
	argv = append(argv, "-u", params.EvalModel.BaseUrl)
	argv = append(argv, "--agent_provider", tmpFile.Name())
	argv = append(argv, "--language", language)

	// Define task titles
	taskTitles := []string{
		"Info Collection",
		"Vulnerability Detection",
		"Vulnerability Review",
	}

	var tasks []SubTask
	for i, title := range taskTitles {
		tasks = append(tasks, CreateSubTask(SubTaskStatusTodo, title, 0, strconv.Itoa(i+1)))
	}
	callbacks.PlanUpdateCallback(tasks)
	config := CmdConfig{StatusId: ""}
	err = utils.RunCmd(AgentScanDir, NAME, argv, func(line string) {
		ParseStdoutLine(m.Server, AgentScanDir, tasks, line, callbacks, &config, false)
	})
	return err
}
