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

// Package scenario loads guided-scan scenes.
//
// Each directory under data/scenarios contains scenario.yaml and SKILL.md.
// scenario.yaml is what the wizard shows. SKILL.md is the instruction the
// single agent loads. enabled: false keeps a directory on disk as an example
// and hides it from the wizard.
package scenario

import (
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"strings"

	"gopkg.in/yaml.v3"
)

// Needs is the smallest input set a scene requires.
type Needs struct {
	Model   bool     `yaml:"model" json:"model"`
	Purpose bool     `yaml:"purpose" json:"purpose"`
	URL     bool     `yaml:"url" json:"url"`
	Code    bool     `yaml:"code" json:"code"`
	Agent   bool     `yaml:"agent" json:"agent"`
	Any     []string `yaml:"any,omitempty" json:"any,omitempty"`
}

// Scenario is one selectable scene.
type Scenario struct {
	ID            string   `yaml:"id" json:"id"`
	Enabled       *bool    `yaml:"enabled,omitempty" json:"-"`
	Name          string   `yaml:"name" json:"name"`
	NameEn        string   `yaml:"name_en" json:"name_en"`
	Description   string   `yaml:"description" json:"description"`
	DescriptionEn string   `yaml:"description_en" json:"description_en"`
	Order         int      `yaml:"order" json:"order"`
	Tools         []string `yaml:"tools" json:"tools"`
	Plugins       []string `yaml:"plugins,omitempty" json:"plugins,omitempty"`
	Strategies    []string `yaml:"strategies,omitempty" json:"strategies,omitempty"`
	Needs         Needs    `yaml:"needs" json:"needs"`
	Dir           string   `yaml:"-" json:"-"`
}

// Input is what the user supplied for one run.
type Input struct {
	HasModel   bool
	HasPurpose bool
	HasURL     bool
	HasCode    bool
	HasAgent   bool
}

// Title returns the display name for a language.
func (s Scenario) Title(lang string) string {
	if lang == "en" && strings.TrimSpace(s.NameEn) != "" {
		return s.NameEn
	}
	if strings.TrimSpace(s.Name) != "" {
		return s.Name
	}
	return s.ID
}

// Summary returns the display description for a language.
func (s Scenario) Summary(lang string) string {
	if lang == "en" && strings.TrimSpace(s.DescriptionEn) != "" {
		return s.DescriptionEn
	}
	return s.Description
}

// Missing reports the first required input that is absent.
func (s Scenario) Missing(in Input, lang string) error {
	need := func(key string) string {
		if lang == "en" {
			switch key {
			case "model":
				return "select a model"
			case "purpose":
				return "write the application prompt"
			case "url":
				return "enter a live URL"
			case "code":
				return "upload code"
			case "agent":
				return "select an agent config"
			default:
				return key
			}
		}
		switch key {
		case "model":
			return "需要选择模型"
		case "purpose":
			return "需要填写应用说明"
		case "url":
			return "需要填写在线地址"
		case "code":
			return "需要上传代码"
		case "agent":
			return "需要选择 Agent 配置"
		default:
			return key
		}
	}
	if s.Needs.Model && !in.HasModel {
		return fmt.Errorf("%s", need("model"))
	}
	if s.Needs.Purpose && !in.HasPurpose {
		return fmt.Errorf("%s", need("purpose"))
	}
	if s.Needs.URL && !in.HasURL {
		return fmt.Errorf("%s", need("url"))
	}
	if s.Needs.Code && !in.HasCode {
		return fmt.Errorf("%s", need("code"))
	}
	if s.Needs.Agent && !in.HasAgent {
		return fmt.Errorf("%s", need("agent"))
	}
	if len(s.Needs.Any) == 0 {
		return nil
	}
	for _, key := range s.Needs.Any {
		switch key {
		case "url":
			if in.HasURL {
				return nil
			}
		case "code":
			if in.HasCode {
				return nil
			}
		case "agent":
			if in.HasAgent {
				return nil
			}
		default:
			return fmt.Errorf("unknown any input %s", key)
		}
	}
	parts := make([]string, 0, len(s.Needs.Any))
	for _, key := range s.Needs.Any {
		parts = append(parts, need(key))
	}
	if lang == "en" {
		return fmt.Errorf("provide one of: %s", strings.Join(parts, ", "))
	}
	return fmt.Errorf("至少提供一项：%s", strings.Join(parts, "、"))
}

// ResolveRoot finds data/scenarios from AIG_DATA_DIR, the executable, or the working directory.
func ResolveRoot() string {
	candidates := make([]string, 0, 8)
	if env := strings.TrimSpace(os.Getenv("AIG_DATA_DIR")); env != "" {
		candidates = append(candidates, filepath.Join(env, "scenarios"))
	}
	if exe, err := os.Executable(); err == nil {
		candidates = append(candidates, filepath.Join(filepath.Dir(exe), "data", "scenarios"))
	}
	if wd, err := os.Getwd(); err == nil {
		dir := wd
		for i := 0; i < 5; i++ {
			candidates = append(candidates, filepath.Join(dir, "data", "scenarios"))
			parent := filepath.Dir(dir)
			if parent == dir {
				break
			}
			dir = parent
		}
	}
	candidates = append(candidates, "data/scenarios")
	for _, candidate := range candidates {
		info, err := os.Stat(candidate)
		if err == nil && info.IsDir() {
			return candidate
		}
	}
	return "data/scenarios"
}

// Load reads runnable scenarios from root.
func Load(root string) ([]Scenario, error) {
	entries, err := os.ReadDir(root)
	if err != nil {
		return nil, fmt.Errorf("read scenarios: %w", err)
	}
	items := make([]Scenario, 0, len(entries))
	for _, entry := range entries {
		if !entry.IsDir() {
			continue
		}
		dir := filepath.Join(root, entry.Name())
		raw, err := os.ReadFile(filepath.Join(dir, "scenario.yaml"))
		if err != nil {
			return nil, fmt.Errorf("read %s: %w", entry.Name(), err)
		}
		var item Scenario
		if err := yaml.Unmarshal(raw, &item); err != nil {
			return nil, fmt.Errorf("parse %s: %w", entry.Name(), err)
		}
		if item.Enabled != nil && !*item.Enabled {
			continue
		}
		item.Dir = dir
		if err := validate(item); err != nil {
			return nil, err
		}
		if _, err := os.Stat(filepath.Join(dir, "SKILL.md")); err != nil {
			return nil, fmt.Errorf("scenario %s is missing SKILL.md", item.ID)
		}
		items = append(items, item)
	}
	sort.Slice(items, func(i, j int) bool {
		if items[i].Order == items[j].Order {
			return items[i].ID < items[j].ID
		}
		return items[i].Order < items[j].Order
	})
	return items, nil
}

// ByID returns one runnable scenario.
func ByID(items []Scenario, id string) (Scenario, bool) {
	for _, item := range items {
		if item.ID == id {
			return item, true
		}
	}
	return Scenario{}, false
}

func validate(item Scenario) error {
	if strings.TrimSpace(item.ID) == "" {
		return fmt.Errorf("scenario id is empty")
	}
	if strings.TrimSpace(item.Name) == "" {
		return fmt.Errorf("scenario %s is missing a name", item.ID)
	}
	if len(item.Tools) == 0 {
		return fmt.Errorf("scenario %s has no tools", item.ID)
	}
	for _, name := range item.Tools {
		if !knownTool(name) {
			return fmt.Errorf("scenario %s uses unknown tool %s", item.ID, name)
		}
	}
	for _, key := range item.Needs.Any {
		switch key {
		case "url", "code", "agent":
		default:
			return fmt.Errorf("scenario %s has unknown any input %s", item.ID, key)
		}
	}
	return nil
}

func knownTool(name string) bool {
	switch name {
	case "http_fetch", "fingerprint_scan", "probe_model", "list_uploads", "read_text_file", "read_agent_config":
		return true
	default:
		return false
	}
}
