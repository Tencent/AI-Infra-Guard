package models

import (
	"context"
	"encoding/base64"
	"errors"
	"io"
	"os"
	"strings"

	"github.com/openai/openai-go/option"

	"github.com/Tencent/AI-Infra-Guard/internal/gologger"
	"github.com/openai/openai-go"
)

type AIModel interface {
	ChatStream(ctx context.Context, history []map[string]string) <-chan string
}

type OpenAI struct {
	Key      string
	BaseUrl  string
	Model    string
	UseToken int64
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

// 验证OpenAI是否可用
func (ai *OpenAI) Vaild(ctx context.Context) error {
	client := openai.NewClient(option.WithBaseURL(ai.BaseUrl), option.WithAPIKey(ai.Key))
	res, err := client.Chat.Completions.New(ctx, openai.ChatCompletionNewParams{
		Messages: []openai.ChatCompletionMessageParamUnion{
			openai.UserMessage("only return '1'"),
		},
		Model: ai.Model,
		Seed:  openai.Int(24),
	})
	if err != nil {
		return err
	}
	if len(res.Choices) == 0 {
		return errors.New("no response")
	}
	if len(res.Choices[0].Message.Content) == 0 {
		return errors.New("invalid response")
	}
	return nil
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
		Messages: chatMessages,
		Seed:     openai.Int(24),
		Model:    ai.Model,
	})
	// 循环读取结果
	go func() {
		var totalToken int64 = 0
		for stream.Next() {
			evt := stream.Current()
			if len(evt.Choices) > 0 {
				word := evt.Choices[0].Delta.Content
				if evt.Usage.TotalTokens > 0 {
					totalToken = evt.Usage.TotalTokens
				}
				resp <- word
			}
		}
		if totalToken > 0 {
			ai.UseToken += totalToken
		}
		if stream.Err() != nil {
			// 处理错误
			gologger.WithError(stream.Err()).Errorln("ChatStream error")
		}
		close(resp)
	}()
	return resp
}

func (ai *OpenAI) ChatResponse(ctx context.Context, prompt string) (string, error) {
	history := []map[string]string{
		{"role": "user", "content": prompt},
	}
	var ret string
	for resp := range ai.ChatStream(ctx, history) {
		ret += resp
	}
	return ret, nil
}

func (ai *OpenAI) ChatWithImage(ctx context.Context, prompt string, imagePath string) (string, error) {
	msgs := []openai.ChatCompletionContentPartUnionParam{
		openai.TextContentPart(prompt),
	}
	if len(imagePath) > 0 {
		file, err := os.Open(imagePath)
		if err != nil {
			return "", err
		}
		defer file.Close()
		data, err := io.ReadAll(file)
		if err != nil {
			return "", err
		}
		imageBase64 := base64.StdEncoding.EncodeToString(data)
		msgs = append(msgs, openai.ImageContentPart(openai.ChatCompletionContentPartImageImageURLParam{
			URL: "data:image/jpeg;base64," + imageBase64,
		}))
	}
	params := openai.ChatCompletionNewParams{
		Messages: []openai.ChatCompletionMessageParamUnion{
			openai.UserMessage(msgs),
		},
		Model: ai.Model,
	}

	client := openai.NewClient(option.WithBaseURL(ai.BaseUrl), option.WithAPIKey(ai.Key))

	completion, err := client.Chat.Completions.New(ctx, params)
	if err != nil {
		return "", err
	}
	return completion.Choices[0].Message.Content, nil
}

func (ai *OpenAI) ChatWithImageByte(ctx context.Context, prompt string, imageData []byte) (string, error) {
	msg := []openai.ChatCompletionContentPartUnionParam{
		openai.TextContentPart(prompt),
	}
	if len(imageData) > 0 {
		imageBase64 := base64.StdEncoding.EncodeToString(imageData)
		msg = append(msg, openai.ImageContentPart(openai.ChatCompletionContentPartImageImageURLParam{
			URL: "data:image/jpeg;base64," + imageBase64,
		}))
	}
	params := openai.ChatCompletionNewParams{
		Messages: []openai.ChatCompletionMessageParamUnion{
			openai.UserMessage(msg),
		},
		Model: ai.Model,
	}

	client := openai.NewClient(option.WithBaseURL(ai.BaseUrl), option.WithAPIKey(ai.Key))

	completion, err := client.Chat.Completions.New(ctx, params)
	if err != nil {
		return "", err
	}
	return completion.Choices[0].Message.Content, nil
}

func (ai *OpenAI) GetTotalToken() int64 {
	return ai.UseToken
}

func (ai *OpenAI) ResetToken() {
	ai.UseToken = 0
}

func GetJsonString(data string) string {
	startIndex := strings.Index(data, "```json")
	endIndex := strings.LastIndex(data, "```")
	if startIndex >= 0 && endIndex > 0 {
		return data[startIndex+7 : endIndex]
	}
	return ""
}
