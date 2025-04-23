package models

import (
	"context"
	"testing"
)

func TestSiliconflowToken(t *testing.T) {
	token := "xx"
	model := "deepseek-ai/DeepSeek-V3"
	baseUrl := "https://api.xx.cn"
	openai := NewOpenAI(token, model, baseUrl)
	for word := range openai.ChatStream(context.Background(), []map[string]string{
		{"role": "user", "content": "你叫什么名字"},
	}) {
		t.Log(word)
	}
}
