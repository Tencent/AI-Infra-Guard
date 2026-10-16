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

// Package redteam runs a promptfoo-style scan: plugins generate cases,
// strategies change delivery, and each case is graded on its own.
package redteam

import (
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"strings"

	"gopkg.in/yaml.v3"
)

// Plugin is one check. Kind prompt generates cases for a model.
// Other kinds grade a single piece of evidence.
type Plugin struct {
	ID       string `yaml:"id" json:"id"`
	Enabled  *bool  `yaml:"enabled,omitempty" json:"-"`
	Name     string `yaml:"name" json:"name"`
	NameEn   string `yaml:"name_en" json:"name_en"`
	Severity string `yaml:"severity" json:"severity"`
	Kind     string `yaml:"kind" json:"kind"`
	Num      int    `yaml:"num" json:"-"`
	Generate string `yaml:"generate" json:"-"`
	Grade    string `yaml:"grade" json:"-"`
}

// Strategy changes how a generated prompt is delivered.
type Strategy struct {
	ID       string `yaml:"id" json:"id"`
	Enabled  *bool  `yaml:"enabled,omitempty" json:"-"`
	Name     string `yaml:"name" json:"name"`
	NameEn   string `yaml:"name_en" json:"name_en"`
	Kind     string `yaml:"kind" json:"kind"`
	Prefix   string `yaml:"prefix" json:"-"`
	PrefixEn string `yaml:"prefix_en" json:"-"`
}

// Title returns the display name.
func (p Plugin) Title(lang string) string {
	if lang == "en" && strings.TrimSpace(p.NameEn) != "" {
		return p.NameEn
	}
	if strings.TrimSpace(p.Name) != "" {
		return p.Name
	}
	return p.ID
}

// Title returns the display name.
func (s Strategy) Title(lang string) string {
	if lang == "en" && strings.TrimSpace(s.NameEn) != "" {
		return s.NameEn
	}
	if strings.TrimSpace(s.Name) != "" {
		return s.Name
	}
	return s.ID
}

// Apply wraps a prompt. Direct delivery returns the prompt unchanged.
func (s Strategy) Apply(prompt, lang string) string {
	if s.Kind != "prefix" {
		return prompt
	}
	prefix := s.Prefix
	if lang == "en" && strings.TrimSpace(s.PrefixEn) != "" {
		prefix = s.PrefixEn
	}
	prefix = strings.TrimSpace(prefix)
	if prefix == "" {
		return prompt
	}
	return prefix + "\n" + prompt
}

// ResolveRoot finds data/redteam.
func ResolveRoot() string {
	candidates := make([]string, 0, 8)
	if env := strings.TrimSpace(os.Getenv("AIG_DATA_DIR")); env != "" {
		candidates = append(candidates, filepath.Join(env, "redteam"))
	}
	if exe, err := os.Executable(); err == nil {
		candidates = append(candidates, filepath.Join(filepath.Dir(exe), "data", "redteam"))
	}
	if wd, err := os.Getwd(); err == nil {
		dir := wd
		for i := 0; i < 5; i++ {
			candidates = append(candidates, filepath.Join(dir, "data", "redteam"))
			parent := filepath.Dir(dir)
			if parent == dir {
				break
			}
			dir = parent
		}
	}
	candidates = append(candidates, "data/redteam")
	for _, candidate := range candidates {
		info, err := os.Stat(candidate)
		if err == nil && info.IsDir() {
			return candidate
		}
	}
	return "data/redteam"
}

// Load reads plugins and strategies from root/plugins and root/strategies.
func Load(root string) ([]Plugin, []Strategy, error) {
	plugins, err := loadPlugins(filepath.Join(root, "plugins"))
	if err != nil {
		return nil, nil, err
	}
	strategies, err := loadStrategies(filepath.Join(root, "strategies"))
	if err != nil {
		return nil, nil, err
	}
	return plugins, strategies, nil
}

func loadPlugins(dir string) ([]Plugin, error) {
	entries, err := os.ReadDir(dir)
	if err != nil {
		return nil, fmt.Errorf("read plugins: %w", err)
	}
	items := make([]Plugin, 0, len(entries))
	for _, entry := range entries {
		if entry.IsDir() || !strings.HasSuffix(entry.Name(), ".yaml") {
			continue
		}
		raw, err := os.ReadFile(filepath.Join(dir, entry.Name()))
		if err != nil {
			return nil, err
		}
		var item Plugin
		if err := yaml.Unmarshal(raw, &item); err != nil {
			return nil, fmt.Errorf("parse %s: %w", entry.Name(), err)
		}
		if item.Enabled != nil && !*item.Enabled {
			continue
		}
		if err := validatePlugin(item); err != nil {
			return nil, err
		}
		items = append(items, item)
	}
	sort.Slice(items, func(i, j int) bool { return items[i].ID < items[j].ID })
	return items, nil
}

func loadStrategies(dir string) ([]Strategy, error) {
	entries, err := os.ReadDir(dir)
	if err != nil {
		return nil, fmt.Errorf("read strategies: %w", err)
	}
	items := make([]Strategy, 0, len(entries))
	for _, entry := range entries {
		if entry.IsDir() || !strings.HasSuffix(entry.Name(), ".yaml") {
			continue
		}
		raw, err := os.ReadFile(filepath.Join(dir, entry.Name()))
		if err != nil {
			return nil, err
		}
		var item Strategy
		if err := yaml.Unmarshal(raw, &item); err != nil {
			return nil, fmt.Errorf("parse %s: %w", entry.Name(), err)
		}
		if item.Enabled != nil && !*item.Enabled {
			continue
		}
		if strings.TrimSpace(item.ID) == "" {
			return nil, fmt.Errorf("strategy id is empty in %s", entry.Name())
		}
		if item.Kind != "direct" && item.Kind != "prefix" {
			return nil, fmt.Errorf("strategy %s has unknown kind %s", item.ID, item.Kind)
		}
		if item.Kind == "prefix" && strings.TrimSpace(item.Prefix) == "" {
			return nil, fmt.Errorf("strategy %s is missing a prefix", item.ID)
		}
		items = append(items, item)
	}
	sort.Slice(items, func(i, j int) bool { return items[i].ID < items[j].ID })
	return items, nil
}

func validatePlugin(item Plugin) error {
	if strings.TrimSpace(item.ID) == "" {
		return fmt.Errorf("plugin id is empty")
	}
	switch item.Severity {
	case "high", "medium", "low":
	default:
		return fmt.Errorf("plugin %s has unknown severity %s", item.ID, item.Severity)
	}
	switch item.Kind {
	case "prompt", "http", "code", "fingerprint", "agent":
	default:
		return fmt.Errorf("plugin %s has unknown kind %s", item.ID, item.Kind)
	}
	if strings.TrimSpace(item.Grade) == "" {
		return fmt.Errorf("plugin %s is missing a grade rubric", item.ID)
	}
	if item.Kind == "prompt" && strings.TrimSpace(item.Generate) == "" {
		return fmt.Errorf("plugin %s is missing a generate rubric", item.ID)
	}
	return nil
}
