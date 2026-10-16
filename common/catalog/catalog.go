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

// Package catalog loads the guided-scan plugin and preset manifests.
//
// A plugin file is one YAML document. Copy data/catalog/plugins/example-custom.yaml
// to add a plugin. kind=builtin binds an existing engine through task_type.
// kind=prompt is a draft for an AI-written prompt; this version keeps those files
// on disk but does not expose them as runnable plugins.
package catalog

import (
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"strings"

	"gopkg.in/yaml.v3"
)

const (
	KindBuiltin = "builtin"
	KindPrompt  = "prompt"

	ModeCodeAudit = "code-audit"
	ModeBlackbox  = "blackbox"
)

// Needs describes the inputs a plugin requires before it can run.
type Needs struct {
	Model     bool `yaml:"model" json:"model"`
	Code      bool `yaml:"code" json:"code"`
	URL       bool `yaml:"url" json:"url"`
	Agent     bool `yaml:"agent" json:"agent"`
	CodeOrURL bool `yaml:"code_or_url" json:"code_or_url"`
	Purpose   bool `yaml:"purpose" json:"purpose"`
}

// Plugin is one selectable scan capability.
type Plugin struct {
	ID             string   `yaml:"id" json:"id"`
	Enabled        *bool    `yaml:"enabled,omitempty" json:"-"`
	Kind           string   `yaml:"kind" json:"kind"`
	Name           string   `yaml:"name" json:"name"`
	NameEn         string   `yaml:"name_en" json:"name_en"`
	Description    string   `yaml:"description" json:"description"`
	DescriptionEn  string   `yaml:"description_en" json:"description_en"`
	TaskType       string   `yaml:"task_type" json:"task_type"`
	Category       string   `yaml:"category" json:"category"`
	Modes          []string `yaml:"modes" json:"modes"`
	Needs          Needs    `yaml:"needs" json:"needs"`
	Order          int      `yaml:"order" json:"order"`
	PromptTemplate string   `yaml:"prompt_template,omitempty" json:"prompt_template,omitempty"`
}

// Preset is a named set of plugin ids.
type Preset struct {
	ID            string   `yaml:"id" json:"id"`
	Name          string   `yaml:"name" json:"name"`
	NameEn        string   `yaml:"name_en" json:"name_en"`
	Description   string   `yaml:"description" json:"description"`
	DescriptionEn string   `yaml:"description_en" json:"description_en"`
	Plugins       []string `yaml:"plugins" json:"plugins"`
	Order         int      `yaml:"order" json:"order"`
}

// Catalog is the runnable plugin set plus presets.
type Catalog struct {
	Plugins []Plugin `json:"plugins"`
	Presets []Preset `json:"presets"`
}

// Title returns the display name for a language.
func (p Plugin) Title(lang string) string {
	if lang == "en" && strings.TrimSpace(p.NameEn) != "" {
		return p.NameEn
	}
	if strings.TrimSpace(p.Name) != "" {
		return p.Name
	}
	return p.ID
}

// Summary returns the display description for a language.
func (p Plugin) Summary(lang string) string {
	if lang == "en" && strings.TrimSpace(p.DescriptionEn) != "" {
		return p.DescriptionEn
	}
	return p.Description
}

// HasMode reports whether the plugin declares a mode.
func (p Plugin) HasMode(mode string) bool {
	for _, item := range p.Modes {
		if item == mode {
			return true
		}
	}
	return false
}

// ResolveRoot finds data/catalog from the working directory, the executable
// directory, or AIG_DATA_DIR.
func ResolveRoot() string {
	candidates := make([]string, 0, 8)
	if env := strings.TrimSpace(os.Getenv("AIG_DATA_DIR")); env != "" {
		candidates = append(candidates, filepath.Join(env, "catalog"))
	}
	if exe, err := os.Executable(); err == nil {
		candidates = append(candidates, filepath.Join(filepath.Dir(exe), "data", "catalog"))
	}
	if wd, err := os.Getwd(); err == nil {
		dir := wd
		for i := 0; i < 5; i++ {
			candidates = append(candidates, filepath.Join(dir, "data", "catalog"))
			parent := filepath.Dir(dir)
			if parent == dir {
				break
			}
			dir = parent
		}
	}
	candidates = append(candidates, "data/catalog")
	for _, candidate := range candidates {
		info, err := os.Stat(candidate)
		if err == nil && info.IsDir() {
			return candidate
		}
	}
	return "data/catalog"
}

// Load reads plugins and presets from root.
func Load(root string) (*Catalog, error) {
	plugins, err := loadPlugins(filepath.Join(root, "plugins"))
	if err != nil {
		return nil, err
	}
	presets, err := loadPresets(filepath.Join(root, "presets"), plugins)
	if err != nil {
		return nil, err
	}
	return &Catalog{Plugins: plugins, Presets: presets}, nil
}

// PluginByID returns a runnable plugin.
func (c *Catalog) PluginByID(id string) (Plugin, bool) {
	for _, plugin := range c.Plugins {
		if plugin.ID == id {
			return plugin, true
		}
	}
	return Plugin{}, false
}

func loadPlugins(dir string) ([]Plugin, error) {
	entries, err := os.ReadDir(dir)
	if err != nil {
		return nil, fmt.Errorf("read plugins: %w", err)
	}
	plugins := make([]Plugin, 0)
	seen := map[string]string{}
	for _, entry := range entries {
		if entry.IsDir() || !isYAML(entry.Name()) {
			continue
		}
		path := filepath.Join(dir, entry.Name())
		data, err := os.ReadFile(path)
		if err != nil {
			return nil, fmt.Errorf("read %s: %w", entry.Name(), err)
		}
		var plugin Plugin
		if err := yaml.Unmarshal(data, &plugin); err != nil {
			return nil, fmt.Errorf("parse %s: %w", entry.Name(), err)
		}
		if !plugin.runnable() {
			continue
		}
		if err := plugin.validate(); err != nil {
			return nil, fmt.Errorf("%s: %w", entry.Name(), err)
		}
		if prev, ok := seen[plugin.ID]; ok {
			return nil, fmt.Errorf("duplicate plugin id %s in %s and %s", plugin.ID, prev, entry.Name())
		}
		seen[plugin.ID] = entry.Name()
		plugins = append(plugins, plugin)
	}
	sort.Slice(plugins, func(i, j int) bool {
		if plugins[i].Order == plugins[j].Order {
			return plugins[i].ID < plugins[j].ID
		}
		return plugins[i].Order < plugins[j].Order
	})
	return plugins, nil
}

func loadPresets(dir string, plugins []Plugin) ([]Preset, error) {
	entries, err := os.ReadDir(dir)
	if err != nil {
		return nil, fmt.Errorf("read presets: %w", err)
	}
	known := map[string]struct{}{}
	for _, plugin := range plugins {
		known[plugin.ID] = struct{}{}
	}
	presets := make([]Preset, 0)
	seen := map[string]string{}
	for _, entry := range entries {
		if entry.IsDir() || !isYAML(entry.Name()) {
			continue
		}
		path := filepath.Join(dir, entry.Name())
		data, err := os.ReadFile(path)
		if err != nil {
			return nil, fmt.Errorf("read %s: %w", entry.Name(), err)
		}
		var preset Preset
		if err := yaml.Unmarshal(data, &preset); err != nil {
			return nil, fmt.Errorf("parse %s: %w", entry.Name(), err)
		}
		if strings.TrimSpace(preset.ID) == "" {
			return nil, fmt.Errorf("%s: preset id is empty", entry.Name())
		}
		if len(preset.Plugins) == 0 {
			return nil, fmt.Errorf("%s: preset %s has no plugins", entry.Name(), preset.ID)
		}
		for _, id := range preset.Plugins {
			if _, ok := known[id]; !ok {
				return nil, fmt.Errorf("%s: preset %s references unknown plugin %s", entry.Name(), preset.ID, id)
			}
		}
		if prev, ok := seen[preset.ID]; ok {
			return nil, fmt.Errorf("duplicate preset id %s in %s and %s", preset.ID, prev, entry.Name())
		}
		seen[preset.ID] = entry.Name()
		presets = append(presets, preset)
	}
	sort.Slice(presets, func(i, j int) bool {
		if presets[i].Order == presets[j].Order {
			return presets[i].ID < presets[j].ID
		}
		return presets[i].Order < presets[j].Order
	})
	return presets, nil
}

func (p Plugin) runnable() bool {
	if p.Enabled != nil && !*p.Enabled {
		return false
	}
	kind := p.Kind
	if kind == "" {
		kind = KindBuiltin
	}
	return kind == KindBuiltin
}

func (p *Plugin) validate() error {
	if strings.TrimSpace(p.ID) == "" {
		return fmt.Errorf("plugin id is empty")
	}
	if p.Kind == "" {
		p.Kind = KindBuiltin
	}
	if p.Kind != KindBuiltin {
		return fmt.Errorf("plugin %s kind %s cannot run", p.ID, p.Kind)
	}
	if strings.TrimSpace(p.TaskType) == "" {
		return fmt.Errorf("plugin %s task_type is empty", p.ID)
	}
	if len(p.Modes) == 0 {
		return fmt.Errorf("plugin %s modes is empty", p.ID)
	}
	for _, mode := range p.Modes {
		if mode != ModeCodeAudit && mode != ModeBlackbox {
			return fmt.Errorf("plugin %s has unknown mode %s", p.ID, mode)
		}
	}
	if strings.TrimSpace(p.Name) == "" {
		return fmt.Errorf("plugin %s name is empty", p.ID)
	}
	return nil
}

func isYAML(name string) bool {
	lower := strings.ToLower(name)
	return strings.HasSuffix(lower, ".yaml") || strings.HasSuffix(lower, ".yml")
}
