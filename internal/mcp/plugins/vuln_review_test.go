package plugins

import (
	"context"
	"github.com/Tencent/AI-Infra-Guard/internal/gologger"
	"github.com/Tencent/AI-Infra-Guard/internal/mcp/models"
	"github.com/stretchr/testify/assert"
	"testing"
)

func TestVulnReview(t *testing.T) {
	plugin := VulnReviewPlugin("")
	codePath := "/Users/python/PycharmProjects/pythonProject/mcp_test_case/mcps/Asteria"
	model := "Qwen/Qwen3-32B"
	token := "empty"
	baseUrl := "http://11.220.10.79:8080/v1"
	aiModel := models.NewOpenAI(token, model, baseUrl)
	config := &McpPluginConfig{
		CodePath:    codePath,
		AIModel:     aiModel,
		SaveHistory: false,
		Language:    "zh",
		Logger:      gologger.NewLogger(),
	}
	issues, err := plugin.Check(context.Background(), config)
	assert.NoError(t, err)
	assert.Greater(t, len(issues), 0)
	t.Logf("issues: %v", issues)
}
