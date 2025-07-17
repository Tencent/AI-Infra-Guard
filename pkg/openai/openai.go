// Package hunyuan 大模型接口实现
package openai

import (
	"context"
	"errors"
	"os"
	"strings"

	"github.com/openai/openai-go"
	"github.com/openai/openai-go/option"
)

// HunyuanAI Hunyuan 实现
func HunyuanAI(prompt string, key string) (string, error) {
	baseUrl := "https://api.hunyuan.cloud.tencent.com/v1/"
	model := "hunyuan-lite"
	return OpenAI(prompt, key, baseUrl, model)
}

// DeepSeekR1API DeepSeek AI接入
func DeepSeekR1API(prompt, key string) (string, error) {
	baseUrl := "https://api.deepseek.com/v1/"
	model := "deepseek-chat"
	return OpenAI(prompt, key, baseUrl, model)
}

// OpenAI API接入
func OpenAI(prompt, key, baseUrl, model string) (string, error) {
	// 设置默认值
	if key == "" {
		key = os.Getenv("OPENAI_API_KEY")
	}
	// 检查key是否为空
	if key == "" {
		return "", errors.New("OPENAI_API_KEY is empty")
	}
	if baseUrl == "" {
		baseUrl = os.Getenv("OPENAI_BASE_URL")
	}
	if model == "" {
		model = os.Getenv("OPENAI_MODEL")
	}
	client := openai.NewClient(option.WithBaseURL(baseUrl), option.WithAPIKey(key))
	ctx := context.Background()
	stream := client.Chat.Completions.NewStreaming(ctx, openai.ChatCompletionNewParams{
		Messages: []openai.ChatCompletionMessageParamUnion{
			openai.UserMessage(prompt),
		},
		Seed:  openai.Int(24),
		Model: model,
	})
	s := strings.Builder{}
	// 循环读取结果
	for stream.Next() {
		evt := stream.Current()
		if len(evt.Choices) > 0 {
			word := evt.Choices[0].Delta.Content
			s.WriteString(word)
			print(word)
		}
	}
	println()
	if err := stream.Err(); err != nil {
		return "", err
	}
	// 返回结果
	return s.String(), nil
}
