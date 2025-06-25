package mcp

import (
	"bytes"
	"github.com/stretchr/testify/assert"
	"testing"
	"text/template"
)

func TestRegisterPlugins(t *testing.T) {
	scanner := NewScanner(nil, nil)
	for _, plugin := range scanner.PluginConfigs {
		t.Logf("plugin: %s", plugin.Info.Name)
		tpl, err := template.New("template").Parse(plugin.PromptTemplate)
		assert.NoError(t, err)
		var buf bytes.Buffer
		err = tpl.Execute(&buf, McpTemplate{
			CodePath:              "",
			DirectoryStructure:    "",
			StaticAnalysisResults: "",
			OriginalReports:       "",
			McpStructure:          "",
		})
		assert.NoError(t, err)
		//t.Logf("template: %s", buf.String())
	}
}
