package models

import (
	"context"
	"github.com/Tencent/AI-Infra-Guard/internal/gologger"
	"github.com/openai/openai-go"
	"github.com/openai/openai-go/option"
	"strings"
)

type AIModel interface {
	ChatStream(ctx context.Context, history []map[string]string) <-chan string
}

type OpenAI struct {
	Key       string
	BaseUrl   string
	Model     string
	UseToken  int64
	CacheText string
}

func NewOpenAI(key string, model string, url string) *OpenAI {
	if url == "" {
		url = "https://api.openai.com/"
	}
	if !strings.HasSuffix(url, "/") {
		url += "/"
	}
	return &OpenAI{
		Key:     key,
		BaseUrl: url,
		Model:   model,
	}
}
func (ai *OpenAI) ChatStream(ctx context.Context, history []map[string]string) <-chan string {
	client := openai.NewClient(option.WithBaseURL(ai.BaseUrl), option.WithAPIKey(ai.Key))
	resp := make(chan string)
	chatMessages := make([]openai.ChatCompletionMessageParamUnion, 0)
	for _, item := range history {
		role := item["role"]
		content := item["content"]
		switch role {
		case "assistant":
			chatMessages = append(chatMessages, openai.AssistantMessage(content))
		case "user":
			chatMessages = append(chatMessages, openai.UserMessage(content))
		}
	}
	stream := client.Chat.Completions.NewStreaming(ctx, openai.ChatCompletionNewParams{
		Messages: openai.F(chatMessages),
		Seed:     openai.Int(24),
		Model:    openai.F(ai.Model),
	})
	// 循环读取结果
	go func() {
		for stream.Next() {
			evt := stream.Current()
			if len(evt.Choices) > 0 {
				word := evt.Choices[0].Delta.Content
				if evt.Usage.TotalTokens > 0 {
					ai.UseToken = evt.Usage.TotalTokens
				}
				ai.CacheText += word
				resp <- word
			}
		}
		if stream.Err() != nil {
			// 处理错误
			gologger.WithError(stream.Err()).Errorln("ChatStream error")
		}
		close(resp)
	}()
	return resp
}

func (ai *OpenAI) GetTotalToken() int64 {
	return ai.UseToken
}

func (ai *OpenAI) ResetToken() {
	ai.UseToken = 0
}
