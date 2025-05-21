package plugins

import (
	"context"
	"github.com/Tencent/AI-Infra-Guard/internal/gologger"
	"github.com/Tencent/AI-Infra-Guard/internal/mcp/models"
	"github.com/stretchr/testify/assert"
	"os"
	"testing"
)

func TestVulnReview(t *testing.T) {
	dd, err := os.ReadFile("test.json")
	assert.NoError(t, err)
	plugin := VulnReviewPlugin(string(dd))
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
