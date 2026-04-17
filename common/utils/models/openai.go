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

package models

import (
	"context"
	"crypto/tls"
	"encoding/base64"
	"errors"
	"io"
	"net/http"
	"os"
	"strings"
	"time"

	"github.com/openai/openai-go/option"

	"github.com/Tencent/AI-Infra-Guard/internal/gologger"
	"github.com/openai/openai-go"
)

type AIModel interface {
	ChatStream(ctx context.Context, history []map[string]string) <-chan string
}

type OpenAI struct {
	Key                string
	BaseUrl            string
	Model              string
	UseToken           int64
	InsecureSkipVerify bool // skip TLS certificate verification (e.g. self-signed certs)
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

// buildHTTPClient constructs an *http.Client respecting InsecureSkipVerify.
// Returns nil when no TLS customisation is needed (the openai-go default client is used).
func (ai *OpenAI) buildHTTPClient() *http.Client {
	if !ai.InsecureSkipVerify {
		return nil
	}
	return &http.Client{
		Transport: &http.Transport{
			TLSClientConfig: &tls.Config{
				InsecureSkipVerify: true, // #nosec G402 — operator-opt-in only
			},
		},
	}
}

// clientOptions returns the openai-go RequestOption slice for this instance.
func (ai *OpenAI) clientOptions() []option.RequestOption {
	opts := []option.RequestOption{
		option.WithBaseURL(ai.BaseUrl),
		option.WithAPIKey(ai.Key),
	}
	if hc := ai.buildHTTPClient(); hc != nil {
		opts = append(opts, option.WithHTTPClient(hc))
	}
	return opts
}

// 验证OpenAI是否可用
func (ai *OpenAI) Vaild(ctx context.Context) error {
	client := openai.NewClient(ai.clientOptions()...)
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
	client := openai.NewClient(ai.clientOptions()...)
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

	const maxRetries = 3
	go func() {
		defer close(resp)
		var totalToken int64 = 0
		for attempt := 0; attempt < maxRetries; attempt++ {
			if attempt > 0 {
				waitSec := time.Duration(1<<attempt) * time.Second // 2s, 4s
				gologger.Infof("ChatStream retry %d/%d after %v", attempt, maxRetries-1, waitSec)
				select {
				case <-ctx.Done():
					return
				case <-time.After(waitSec):
				}
			}
			stream := client.Chat.Completions.NewStreaming(ctx, openai.ChatCompletionNewParams{
				Messages: chatMessages,
				Seed:     openai.Int(24),
				Model:    ai.Model,
			})
			streamErr := false
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
			if stream.Err() != nil {
				gologger.WithError(stream.Err()).Errorf("ChatStream error (attempt %d/%d)", attempt+1, maxRetries)
				streamErr = true
			}
			if !streamErr {
				break
			}
		}
		if totalToken > 0 {
			ai.UseToken += totalToken
		}
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

	client := openai.NewClient(ai.clientOptions()...)

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

	client := openai.NewClient(ai.clientOptions()...)

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
	return data
}
