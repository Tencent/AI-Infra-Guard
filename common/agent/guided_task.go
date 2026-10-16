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
	"strings"
	"sync"
	"time"

	"github.com/Tencent/AI-Infra-Guard/common/catalog"
)

// GuidedScanTask runs one scene as generated cases, strategy delivery, and per-case grading.
// Root is data/scenarios. Rules is data/redteam. Runners is unused.
type GuidedScanTask struct {
	Server  string
	Root    string
	Rules   string
	Runners map[string]TaskInterface
}

func (t *GuidedScanTask) GetName() string {
	return TaskTypeGuidedScan
}

// RunInput is the part of a guided scan that decides which lanes run.
type RunInput struct {
	Purpose     string
	TargetURL   string
	Attachments []string
	HasModel    bool
	HasAgent    bool
	Language    string
}

// PluginRun is one engine invocation inside a guided scan.
type PluginRun struct {
	Plugin      catalog.Plugin
	Mode        string
	StepID      string
	Title       string
	Content     string
	Attachments []string
}

type guidedParams struct {
	Plugins   []string `json:"plugins"`
	Purpose   string   `json:"purpose"`
	TargetURL string   `json:"target_url"`
	ModelID   any      `json:"model_id"`
	AgentID   string   `json:"agent_id"`
	AgentData string   `json:"agent_data"`
	Model     any      `json:"model"`
}

func (t *GuidedScanTask) Execute(ctx context.Context, request TaskRequest, callbacks TaskCallbacks) error {
	return t.runScenario(ctx, request, callbacks)
}

// ExpandRuns turns selected plugins into concrete engine runs.
// A plugin that declares both modes produces two runs when code and a live URL both exist.
func ExpandRuns(plugins []catalog.Plugin, input RunInput) ([]PluginRun, error) {
	if len(plugins) == 0 {
		return nil, fmt.Errorf("select at least one plugin")
	}
	hasCode := hasCodeInput(input)
	hasURL := hasBlackboxURL(input.TargetURL)
	runs := make([]PluginRun, 0, len(plugins))
	for _, plugin := range plugins {
		if err := missingNeed(plugin, input, hasCode, hasURL); err != nil {
			return nil, err
		}
		if plugin.HasMode(catalog.ModeCodeAudit) && hasCode && codeModeApplies(plugin, hasCode) {
			runs = append(runs, PluginRun{
				Plugin:      plugin,
				Mode:        catalog.ModeCodeAudit,
				StepID:      plugin.ID + ":code-audit",
				Title:       runTitle(plugin, catalog.ModeCodeAudit, input.Language),
				Content:     codeContent(input),
				Attachments: append([]string(nil), input.Attachments...),
			})
		}
		if plugin.HasMode(catalog.ModeBlackbox) && blackboxApplies(plugin, hasURL) {
			runs = append(runs, PluginRun{
				Plugin:      plugin,
				Mode:        catalog.ModeBlackbox,
				StepID:      plugin.ID + ":blackbox",
				Title:       runTitle(plugin, catalog.ModeBlackbox, input.Language),
				Content:     blackboxContent(plugin, input),
				Attachments: nil,
			})
		}
	}
	if len(runs) == 0 {
		return nil, fmt.Errorf("no plugin can run with the current inputs")
	}
	return runs, nil
}

func codeModeApplies(plugin catalog.Plugin, hasCode bool) bool {
	if !hasCode {
		return false
	}
	if plugin.Needs.Code || plugin.Needs.CodeOrURL {
		return true
	}
	// A hybrid plugin with a code-audit mode still audits when code exists.
	return plugin.HasMode(catalog.ModeCodeAudit) && plugin.HasMode(catalog.ModeBlackbox)
}

func blackboxApplies(plugin catalog.Plugin, hasURL bool) bool {
	if plugin.Needs.URL || plugin.Needs.CodeOrURL {
		return hasURL
	}
	// Model and agent black-box runs do not need a URL.
	return !plugin.Needs.URL && !plugin.Needs.CodeOrURL
}

func missingNeed(plugin catalog.Plugin, input RunInput, hasCode, hasURL bool) error {
	name := plugin.Title(input.Language)
	if plugin.Needs.Model && !input.HasModel {
		return fmt.Errorf("%s requires a model", name)
	}
	if plugin.Needs.Agent && !input.HasAgent {
		return fmt.Errorf("%s requires an agent", name)
	}
	if plugin.Needs.Purpose && strings.TrimSpace(input.Purpose) == "" {
		return fmt.Errorf("%s requires an application prompt", name)
	}
	if plugin.Needs.Code && !hasCode {
		return fmt.Errorf("%s requires code", name)
	}
	if plugin.Needs.URL && !hasURL {
		return fmt.Errorf("%s requires a url", name)
	}
	if plugin.Needs.CodeOrURL && !hasCode && !hasURL {
		return fmt.Errorf("%s requires code or a url", name)
	}
	return nil
}

func hasCodeInput(input RunInput) bool {
	if len(input.Attachments) > 0 {
		return true
	}
	return strings.Contains(input.TargetURL, "github.com") || strings.Contains(input.Purpose, "github.com")
}

func hasBlackboxURL(target string) bool {
	target = strings.TrimSpace(target)
	if target == "" || strings.Contains(target, "github.com") {
		return false
	}
	return true
}

func codeContent(input RunInput) string {
	if len(input.Attachments) == 0 {
		if strings.Contains(input.TargetURL, "github.com") {
			return input.TargetURL
		}
		if strings.Contains(input.Purpose, "github.com") {
			return input.Purpose
		}
	}
	return input.Purpose
}

func blackboxContent(plugin catalog.Plugin, input RunInput) string {
	if plugin.TaskType == TaskTypeAIInfraScan || plugin.Needs.URL || plugin.Needs.CodeOrURL {
		if hasBlackboxURL(input.TargetURL) {
			return input.TargetURL
		}
	}
	return input.Purpose
}

func runTitle(plugin catalog.Plugin, mode, lang string) string {
	label := "黑盒"
	if mode == catalog.ModeCodeAudit {
		label = "代码审计"
	}
	if lang == "en" {
		label = "Black-box"
		if mode == catalog.ModeCodeAudit {
			label = "Code audit"
		}
	}
	return plugin.Title(lang) + " · " + label
}

func paramsForChild(raw json.RawMessage, taskType string) (json.RawMessage, error) {
	if len(raw) == 0 {
		return raw, nil
	}
	var payload map[string]any
	if err := json.Unmarshal(raw, &payload); err != nil {
		return nil, err
	}
	model, ok := payload["model"]
	if !ok {
		return raw, nil
	}
	if taskType == TaskTypeModelRedteamReport {
		if _, isObj := model.(map[string]any); isObj {
			payload["model"] = []any{model}
		}
	} else if list, isList := model.([]any); isList && len(list) > 0 {
		payload["model"] = list[0]
	}
	return json.Marshal(payload)
}

type stepPlanner struct {
	mu     sync.Mutex
	steps  []SubTask
	emitFn func([]SubTask)
}

func newStepPlanner(steps []SubTask, emit func([]SubTask)) *stepPlanner {
	copied := append([]SubTask(nil), steps...)
	return &stepPlanner{steps: copied, emitFn: emit}
}

func (p *stepPlanner) emit() {
	if p.emitFn == nil {
		return
	}
	p.mu.Lock()
	snapshot := append([]SubTask(nil), p.steps...)
	p.mu.Unlock()
	p.emitFn(snapshot)
}

func (p *stepPlanner) set(stepID string, status statusString) {
	p.mu.Lock()
	for i := range p.steps {
		if p.steps[i].StepId == stepID {
			p.steps[i].Status = status
			if status == SubTaskStatusDoing && p.steps[i].StartedAt == 0 {
				p.steps[i].StartedAt = time.Now().Unix()
			}
		}
	}
	snapshot := append([]SubTask(nil), p.steps...)
	p.mu.Unlock()
	if p.emitFn != nil {
		p.emitFn(snapshot)
	}
}
