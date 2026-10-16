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

package catalog

import (
	"os"
	"path/filepath"
	"testing"

	"github.com/stretchr/testify/require"
)

func TestLoadRepoCatalog(t *testing.T) {
	root := filepath.Join("..", "..", "data", "catalog")
	cat, err := Load(root)
	require.NoError(t, err)
	require.Len(t, cat.Plugins, 5)
	require.GreaterOrEqual(t, len(cat.Presets), 6)

	ids := map[string]struct{}{}
	for _, plugin := range cat.Plugins {
		ids[plugin.ID] = struct{}{}
		require.NotEqual(t, "example-custom-check", plugin.ID)
	}
	for _, want := range []string{"mcp-scan", "skill-scan", "agent-scan", "model-redteam", "infra-scan"} {
		_, ok := ids[want]
		require.True(t, ok, want)
	}
	_, ok := cat.PluginByID("example-custom-check")
	require.False(t, ok)
}

func TestLoadRejectsUnknownPresetPlugin(t *testing.T) {
	dir := t.TempDir()
	require.NoError(t, os.MkdirAll(filepath.Join(dir, "plugins"), 0o755))
	require.NoError(t, os.MkdirAll(filepath.Join(dir, "presets"), 0o755))
	require.NoError(t, os.WriteFile(filepath.Join(dir, "plugins", "one.yaml"), []byte(`
id: one
kind: builtin
name: One
task_type: Mcp-Scan
modes: [code-audit]
needs:
  code: true
`), 0o644))
	require.NoError(t, os.WriteFile(filepath.Join(dir, "presets", "bad.yaml"), []byte(`
id: bad
name: Bad
plugins: [missing]
`), 0o644))

	_, err := Load(dir)
	require.Error(t, err)
	require.Contains(t, err.Error(), "missing")
}
