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
	"encoding/json"
	"testing"

	"github.com/Tencent/AI-Infra-Guard/common/catalog"
	"github.com/stretchr/testify/require"
)

func TestExpandRunsCodeAndBlackboxTogether(t *testing.T) {
	plugins := []catalog.Plugin{
		{
			ID: "mcp-scan", Name: "MCP 扫描", TaskType: TaskTypeMcpScan,
			Modes: []string{catalog.ModeCodeAudit, catalog.ModeBlackbox},
			Needs: catalog.Needs{Model: true, CodeOrURL: true},
		},
		{
			ID: "model-redteam", Name: "模型体检", TaskType: TaskTypeModelRedteamReport,
			Modes: []string{catalog.ModeBlackbox},
			Needs: catalog.Needs{Model: true, Purpose: true},
		},
	}
	runs, err := ExpandRuns(plugins, RunInput{
		Purpose:     "这是一个内部知识库助手",
		TargetURL:   "http://127.0.0.1:8080",
		Attachments: []string{"code.zip"},
		HasModel:    true,
		Language:    "zh",
	})
	require.NoError(t, err)
	require.Len(t, runs, 3)

	var code, live, model PluginRun
	for _, run := range runs {
		switch run.StepID {
		case "mcp-scan:code-audit":
			code = run
		case "mcp-scan:blackbox":
			live = run
		case "model-redteam:blackbox":
			model = run
		}
	}
	require.Equal(t, []string{"code.zip"}, code.Attachments)
	require.Equal(t, "这是一个内部知识库助手", code.Content)
	require.Empty(t, live.Attachments)
	require.Equal(t, "http://127.0.0.1:8080", live.Content)
	require.Empty(t, model.Attachments)
	require.Equal(t, "这是一个内部知识库助手", model.Content)
}

func TestExpandRunsRequiresMissingInput(t *testing.T) {
	plugins := []catalog.Plugin{{
		ID: "skill-scan", Name: "Skill 扫描", TaskType: TaskTypeSkillScan,
		Modes: []string{catalog.ModeCodeAudit},
		Needs: catalog.Needs{Code: true, Model: true},
	}}
	_, err := ExpandRuns(plugins, RunInput{HasModel: true, Language: "zh"})
	require.Error(t, err)
	require.Contains(t, err.Error(), "code")
}

func TestParamsForChildShapesModel(t *testing.T) {
	raw := json.RawMessage(`{"model":{"model":"demo","token":"t","base_url":"http://llm"}}`)
	out, err := paramsForChild(raw, TaskTypeModelRedteamReport)
	require.NoError(t, err)
	var payload struct {
		Model []ModelParams `json:"model"`
	}
	require.NoError(t, json.Unmarshal(out, &payload))
	require.Len(t, payload.Model, 1)
	require.Equal(t, "demo", payload.Model[0].Model)

	back, err := paramsForChild(out, TaskTypeMcpScan)
	require.NoError(t, err)
	var single struct {
		Model ModelParams `json:"model"`
	}
	require.NoError(t, json.Unmarshal(back, &single))
	require.Equal(t, "demo", single.Model.Model)
}
