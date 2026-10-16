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
	"net/url"
	"os"
	"path/filepath"
	"strings"

	"github.com/Tencent/AI-Infra-Guard/common/redteam"
	"github.com/Tencent/AI-Infra-Guard/common/scenario"
	"github.com/Tencent/AI-Infra-Guard/common/utils"
	"github.com/google/uuid"
	"trpc.group/trpc-go/trpc-agent-go/model"
	trpcopenai "trpc.group/trpc-go/trpc-agent-go/model/openai"
)

const scenarioStepID = "scenario-run"

type scenarioParams struct {
	Scenario   string            `json:"scenario"`
	Purpose    string            `json:"purpose"`
	TargetURL  string            `json:"target_url"`
	AgentID    string            `json:"agent_id"`
	AgentData  string            `json:"agent_data"`
	Headers    map[string]string `json:"headers"`
	Model      json.RawMessage   `json:"model"`
	EvalModel  json.RawMessage   `json:"eval_model"`
	Plugins    []string          `json:"plugins"`
	Strategies []string          `json:"strategies"`
}

type scenarioModel struct {
	Model   string `json:"model"`
	Token   string `json:"token"`
	BaseURL string `json:"base_url"`
}

func (t *GuidedScanTask) runScenario(ctx context.Context, request TaskRequest, callbacks TaskCallbacks) error {
	var params scenarioParams
	if len(request.Params) > 0 {
		if err := json.Unmarshal(request.Params, &params); err != nil {
			return fmt.Errorf("parse scenario params: %w", err)
		}
	}
	root := t.Root
	if root == "" {
		root = scenario.ResolveRoot()
	}
	items, err := scenario.Load(root)
	if err != nil {
		return err
	}
	selected, ok := scenario.ByID(items, strings.TrimSpace(params.Scenario))
	if !ok {
		return fmt.Errorf("unknown scenario %s", params.Scenario)
	}
	lang := request.Language
	if lang != "en" {
		lang = "zh"
	}
	cred := firstModel(params.Model)
	if cred.BaseURL == "" {
		cred = firstModel(params.EvalModel)
	}
	purpose := strings.TrimSpace(params.Purpose)
	if purpose == "" {
		purpose = strings.TrimSpace(request.Content)
	}
	targetURL := strings.TrimSpace(params.TargetURL)
	uploadDir, cleanup, err := t.materializeUploads(request)
	if err != nil {
		return err
	}
	defer cleanup()
	hasCode := uploadDir != "" || strings.Contains(strings.ToLower(targetURL), "github.com") || strings.Contains(strings.ToLower(purpose), "github.com")
	hasURL := targetURL != "" && !strings.Contains(strings.ToLower(targetURL), "github.com")
	if err := selected.Missing(scenario.Input{
		HasModel:   cred.Token != "" && cred.BaseURL != "" && cred.Name != "",
		HasPurpose: purpose != "",
		HasURL:     hasURL,
		HasCode:    hasCode,
		HasAgent:   strings.TrimSpace(params.AgentData) != "" || strings.TrimSpace(params.AgentID) != "",
	}, lang); err != nil {
		return err
	}

	title := selected.Title(lang)
	planner := newStepPlanner([]SubTask{
		CreateSubTask(SubTaskStatusTodo, title, 0, scenarioStepID),
	}, callbacks.PlanUpdateCallback)
	planner.emit()
	planner.set(scenarioStepID, SubTaskStatusDoing)
	if callbacks.NewPlanStepCallback != nil {
		callbacks.NewPlanStepCallback(scenarioStepID, title)
	}
	logStatus(callbacks, "running", title, selected.Summary(lang))

	rules := t.Rules
	if rules == "" {
		rules = redteam.ResolveRoot()
	}
	allPlugins, allStrategies, err := redteam.Load(rules)
	if err != nil {
		return err
	}
	pluginIDs := params.Plugins
	if len(pluginIDs) == 0 {
		pluginIDs = selected.Plugins
	}
	strategyIDs := params.Strategies
	if len(strategyIDs) == 0 {
		strategyIDs = selected.Strategies
	}
	plugins, err := pickPlugins(allPlugins, pluginIDs, lang)
	if err != nil {
		return err
	}
	strategies, err := pickStrategies(allStrategies, strategyIDs, lang)
	if err != nil {
		return err
	}
	box := &scenarioToolBox{
		headers:   params.Headers,
		uploadDir: uploadDir,
		model:     cred,
		agentData: params.AgentData,
		language:  lang,
	}
	if hasURL {
		parsed, err := parseTarget(targetURL)
		if err != nil {
			return err
		}
		box.target = parsed
	}
	grader := cred
	if eval := firstModel(params.EvalModel); eval.Token != "" && eval.BaseURL != "" && eval.Name != "" {
		grader = eval
	}
	report, err := redteam.Run(ctx, redteam.Input{
		Language:   lang,
		Purpose:    purpose,
		Plugins:    plugins,
		Strategies: strategies,
		Evidence:   box.collectEvidence(ctx, plugins),
		Brain: func(ctx context.Context, system, user string) (string, error) {
			return completeModel(ctx, grader, system, user, 800)
		},
		Target: func(ctx context.Context, system, user string) (string, error) {
			return completeModel(ctx, cred, system, user, 400)
		},
		OnProgress: func(phase, detail string) {
			logStatus(callbacks, "running", detail, phase)
		},
	})
	planner.set(scenarioStepID, SubTaskStatusDone)
	if err != nil {
		return err
	}
	if callbacks.ResultCallback != nil {
		callbacks.ResultCallback(map[string]any{
			"msgType":  "guidedReport",
			"content":  report.Summary,
			"scenario": selected.ID,
			"verdict":  report.Verdict,
			"report":   report,
		})
	}
	return nil
}

func (t *GuidedScanTask) materializeUploads(request TaskRequest) (string, func(), error) {
	noop := func() {}
	if len(request.Attachments) == 0 {
		return "", noop, nil
	}
	dir, err := os.MkdirTemp("", "aig-scenario-*")
	if err != nil {
		return "", noop, err
	}
	cleanup := func() { _ = os.RemoveAll(dir) }
	for i, name := range request.Attachments {
		dest := filepath.Join(dir, fmt.Sprintf("%02d-%s", i, filepath.Base(name)))
		if info, statErr := os.Stat(name); statErr == nil && !info.IsDir() {
			raw, readErr := os.ReadFile(name)
			if readErr != nil {
				cleanup()
				return "", noop, readErr
			}
			if writeErr := os.WriteFile(dest, raw, 0o600); writeErr != nil {
				cleanup()
				return "", noop, writeErr
			}
			continue
		}
		if strings.TrimSpace(t.Server) == "" {
			cleanup()
			return "", noop, fmt.Errorf("cannot download attachment %s", filepath.Base(name))
		}
		if err := utils.DownloadFile(t.Server, request.SessionId, name, dest); err != nil {
			cleanup()
			return "", noop, err
		}
	}
	return dir, cleanup, nil
}

func firstModel(raw json.RawMessage) modelCreds {
	raw = bytesTrim(raw)
	if len(raw) == 0 || string(raw) == "null" {
		return modelCreds{}
	}
	if raw[0] == '[' {
		var list []scenarioModel
		if err := json.Unmarshal(raw, &list); err != nil || len(list) == 0 {
			return modelCreds{}
		}
		return modelCreds{Name: list[0].Model, Token: list[0].Token, BaseURL: list[0].BaseURL}
	}
	var one scenarioModel
	if err := json.Unmarshal(raw, &one); err != nil {
		return modelCreds{}
	}
	return modelCreds{Name: one.Model, Token: one.Token, BaseURL: one.BaseURL}
}

func bytesTrim(raw json.RawMessage) json.RawMessage {
	return json.RawMessage(strings.TrimSpace(string(raw)))
}

func parseTarget(raw string) (*url.URL, error) {
	parsed, err := url.Parse(raw)
	if err != nil || parsed.Host == "" || (parsed.Scheme != "http" && parsed.Scheme != "https") {
		return nil, fmt.Errorf("target url must be http or https")
	}
	return parsed, nil
}

func logStatus(callbacks TaskCallbacks, status, brief, description string) {
	if callbacks.StepStatusUpdateCallback != nil {
		callbacks.StepStatusUpdateCallback(scenarioStepID, uuid.NewString(), status, brief, description)
	}
}

func pickPlugins(all []redteam.Plugin, ids []string, lang string) ([]redteam.Plugin, error) {
	return pickNamed(len(all), ids, func(id string) (redteam.Plugin, bool) {
		for _, item := range all {
			if item.ID == id {
				return item, true
			}
		}
		return redteam.Plugin{}, false
	}, 8, lang, "plugin", "插件")
}

func pickStrategies(all []redteam.Strategy, ids []string, lang string) ([]redteam.Strategy, error) {
	if len(ids) == 0 {
		for _, item := range all {
			if item.ID == "direct" {
				return []redteam.Strategy{item}, nil
			}
		}
	}
	return pickNamed(len(all), ids, func(id string) (redteam.Strategy, bool) {
		for _, item := range all {
			if item.ID == id {
				return item, true
			}
		}
		return redteam.Strategy{}, false
	}, 3, lang, "strategy", "策略")
}

func pickNamed[T any](size int, ids []string, find func(string) (T, bool), limit int, lang, enName, zhName string) ([]T, error) {
	out := make([]T, 0, size)
	seen := map[string]bool{}
	for _, id := range ids {
		id = strings.TrimSpace(id)
		if id == "" || seen[id] {
			continue
		}
		item, ok := find(id)
		if !ok {
			if lang == "en" {
				return nil, fmt.Errorf("unknown %s %s", enName, id)
			}
			return nil, fmt.Errorf("未知%s %s", zhName, id)
		}
		seen[id] = true
		out = append(out, item)
		if len(out) >= limit {
			break
		}
	}
	if len(out) == 0 {
		if lang == "en" {
			return nil, fmt.Errorf("select at least one %s", enName)
		}
		return nil, fmt.Errorf("至少选择一个%s", zhName)
	}
	return out, nil
}

func completeModel(ctx context.Context, cred modelCreds, system, user string, maxTokens int) (string, error) {
	if cred.BaseURL == "" || cred.Token == "" || cred.Name == "" {
		return "", fmt.Errorf("模型配置不完整")
	}
	llm := trpcopenai.New(cred.Name, trpcopenai.WithAPIKey(cred.Token), trpcopenai.WithBaseURL(cred.BaseURL))
	temperature := 0.0
	messages := make([]model.Message, 0, 2)
	if strings.TrimSpace(system) != "" {
		messages = append(messages, model.NewSystemMessage(system))
	}
	messages = append(messages, model.NewUserMessage(user))
	stream, err := llm.GenerateContent(ctx, &model.Request{
		Messages: messages,
		GenerationConfig: model.GenerationConfig{
			Temperature: &temperature,
			MaxTokens:   &maxTokens,
			Stream:      false,
		},
	})
	if err != nil {
		return "", fmt.Errorf("模型请求失败")
	}
	var text string
	for resp := range stream {
		if resp == nil || resp.IsPartial || len(resp.Choices) == 0 {
			if resp != nil && resp.Error != nil {
				return "", fmt.Errorf("模型请求失败")
			}
			continue
		}
		if resp.Error != nil {
			return "", fmt.Errorf("模型请求失败")
		}
		if content := strings.TrimSpace(resp.Choices[0].Message.Content); content != "" {
			text = content
		}
	}
	if text == "" {
		return "", fmt.Errorf("模型没有返回内容")
	}
	return text, nil
}
