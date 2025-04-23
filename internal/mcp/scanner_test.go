package mcp

import (
	"context"
	"github.com/Tencent/AI-Infra-Guard/internal/mcp/models"
	"github.com/stretchr/testify/assert"
	"testing"
)

func TestScanner(t *testing.T) {
	model := models.NewHunyuanAI("x", "hunyuan-turbo", "")
	scanner := NewScanner(model)
	scanner.RegisterPlugin()
	err := scanner.InputCodePath("/Users/python/Downloads/damn-vulnerable-MCP-server-main/challenges/easy/challenge2")
	assert.NoError(t, err)
	issues, err := scanner.Scan(context.Background())
	assert.NoError(t, err)
	for _, issue := range issues {
		t.Logf("issue: %v", issue)
	}
}
