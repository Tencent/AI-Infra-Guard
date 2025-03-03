package openai

import (
	"github.com/stretchr/testify/assert"
	"os"
	"testing"
)

func TestHunyuanAI(t *testing.T) {
	data, err := os.ReadFile("test_prompt.txt")
	assert.NoError(t, err)
	retMsg, err := HunyuanAI(string(data), "xx")
	assert.NoError(t, err)
	t.Log(retMsg)
}

func TestDeepSeekR1API(t *testing.T) {
	s, err := DeepSeekR1API("你好", "xx")
	assert.NoError(t, err)
	t.Log(s)
}
