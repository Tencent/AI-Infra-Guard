// Copyright (c) 2024-2026 Tencent Zhuque Lab. All rights reserved.
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.
//
// Requirement: Any integration or derivative work must explicitly attribute
// Tencent Zhuque Lab (https://github.com/Tencent/AI-Infra-Guard) in its
// documentation or user interface, as detailed in the NOTICE file.

package agent

import (
	"context"
	"encoding/json"
	"fmt"
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

// 创建一个mock回调结构来验证agent执行流程
type MockCallbacks struct {
	ResultCallbackFunc           func(result map[string]interface{})
	ToolUseLogCallbackFunc       func(actionId, tool, planStepId, actionLog string)
	ToolUsedCallbackFunc         func(planStepId, statusId, description string, tools []Tool)
	NewPlanStepCallbackFunc      func(stepId, title string)
	StepStatusUpdateCallbackFunc func(planStepId, statusId, agentStatus, brief, description string)
	PlanUpdateCallbackFunc       func(tasks []SubTask)
}

func NewMockCallbacks() *MockCallbacks {
	mc := &MockCallbacks{}

	// 设置回调函数来收集调用信息
	mc.ResultCallbackFunc = func(result map[string]interface{}) {
		fmt.Println("ResultCallbackFunc", result)
	}

	mc.ToolUseLogCallbackFunc = func(actionId, tool, planStepId, actionLog string) {
		fmt.Println("ToolUseLogCallbackFunc", actionId, tool, planStepId, actionLog)
	}

	mc.ToolUsedCallbackFunc = func(planStepId, statusId, description string, tools []Tool) {
		// 记录工具使用
		fmt.Println("ToolUsedCallbackFunc", planStepId, statusId, description, tools)
	}

	mc.NewPlanStepCallbackFunc = func(stepId, title string) {
		fmt.Println("NewPlanStepCallbackFunc", stepId, title)
	}

	mc.StepStatusUpdateCallbackFunc = func(planStepId, statusId, agentStatus, brief, description string) {
		fmt.Println("StepStatusUpdateCallbackFunc", planStepId, statusId, agentStatus, brief, description)
	}

	mc.PlanUpdateCallbackFunc = func(tasks []SubTask) {
		fmt.Println("PlanUpdateCallbackFunc", tasks)
	}
	return mc
}
func (mc *MockCallbacks) GetCallbacks() TaskCallbacks {
	return TaskCallbacks{
		ResultCallback:           mc.ResultCallbackFunc,
		ToolUseLogCallback:       mc.ToolUseLogCallbackFunc,
		ToolUsedCallback:         mc.ToolUsedCallbackFunc,
		NewPlanStepCallback:      mc.NewPlanStepCallbackFunc,
		StepStatusUpdateCallback: mc.StepStatusUpdateCallbackFunc,
		PlanUpdateCallback:       mc.PlanUpdateCallbackFunc,
	}
}

// TestTaskGetName 验证已注册任务类型的名称与 TaskType 常量一一对应
func TestTaskGetName(t *testing.T) {
	tasks := []struct {
		name string
		task TaskInterface
		want string
	}{
		{"AIInfraScanAgent", &AIInfraScanAgent{}, TaskTypeAIInfraScan},
		{"McpTask", &McpTask{}, TaskTypeMcpScan},
		{"ModelRedteamReport", &ModelRedteamReport{}, TaskTypeModelRedteamReport},
		{"AgentTask", &AgentTask{}, TaskTypeAgentScan},
		{"SkillTask", &SkillTask{}, TaskTypeSkillScan},
	}
	for _, tt := range tasks {
		t.Run(tt.name, func(t *testing.T) {
			assert.Equal(t, tt.want, tt.task.GetName())
		})
	}
}

// TestMcpTaskExecuteInvalidParams 验证非法 JSON 参数直接返回反序列化错误
func TestMcpTaskExecuteInvalidParams(t *testing.T) {
	task := &McpTask{}
	request := TaskRequest{
		SessionId: "mcp-session-invalid",
		TaskType:  TaskTypeMcpScan,
		Params:    json.RawMessage(`{invalid`),
	}
	err := task.Execute(context.Background(), request, NewMockCallbacks().GetCallbacks())
	assert.Error(t, err)
}

// TestAIInfraScanAgentExecuteInvalidParams 验证非法 JSON 参数直接返回反序列化错误
func TestAIInfraScanAgentExecuteInvalidParams(t *testing.T) {
	agent := &AIInfraScanAgent{}
	request := TaskRequest{
		SessionId: "scan-session-invalid",
		TaskType:  TaskTypeAIInfraScan,
		Params:    json.RawMessage(`{invalid`),
	}
	err := agent.Execute(context.Background(), request, NewMockCallbacks().GetCallbacks())
	assert.Error(t, err)
}

// TestModelRedteamReportExecuteValidation 验证 prompt 与 data 的互斥/必填校验
func TestModelRedteamReportExecuteValidation(t *testing.T) {
	agent := &ModelRedteamReport{}

	t.Run("prompt and data both empty", func(t *testing.T) {
		request := TaskRequest{
			SessionId: "redteam-session-empty",
			TaskType:  TaskTypeModelRedteamReport,
			Params:    json.RawMessage(`{}`),
			Content:   "",
		}
		err := agent.Execute(context.Background(), request, NewMockCallbacks().GetCallbacks())
		require.Error(t, err)
		assert.Contains(t, err.Error(), "不能同时为空")
	})

	t.Run("prompt and attachment conflict", func(t *testing.T) {
		request := TaskRequest{
			SessionId:   "redteam-session-conflict",
			TaskType:    TaskTypeModelRedteamReport,
			Params:      json.RawMessage(`{}`),
			Content:     "红队测试内容",
			Attachments: []string{"dataset.json"},
		}
		err := agent.Execute(context.Background(), request, NewMockCallbacks().GetCallbacks())
		require.Error(t, err)
		assert.Contains(t, err.Error(), "不能同时使用")
	})
}

// TestGetDefaultEvalModel 验证默认评测模型的环境变量读取契约
func TestGetDefaultEvalModel(t *testing.T) {
	t.Run("env not set", func(t *testing.T) {
		t.Setenv("eval_base_url", "")
		t.Setenv("eval_api_key", "")
		t.Setenv("eval_model", "")
		_, err := getDefaultEvalModel()
		assert.Error(t, err)
	})

	t.Run("env set", func(t *testing.T) {
		t.Setenv("eval_base_url", "https://example.com/v1")
		t.Setenv("eval_api_key", "test-key")
		t.Setenv("eval_model", "test-model")
		params, err := getDefaultEvalModel()
		require.NoError(t, err)
		assert.Equal(t, "https://example.com/v1", params.BaseUrl)
		assert.Equal(t, "test-key", params.Token)
		assert.Equal(t, "test-model", params.Model)
		assert.Equal(t, 1000, params.Limit)
	})
}
