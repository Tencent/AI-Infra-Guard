package models

import (
	"bufio"
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"strings"
)

type HunyuanAI struct {
	Key     string
	BaseUrl string
	Model   string
}

func NewHunyuanAI(key string, model string, url string) *HunyuanAI {
	if url == "" {
		url = "http://hunyuanapi.woa.com/openapi/v1"
	}
	if model == "" {
		model = "hunyuan"
	}
	return &HunyuanAI{
		Key:     key,
		BaseUrl: url,
		Model:   model,
	}
}

func (ai *HunyuanAI) ChatStream(ctx context.Context, history []map[string]string) <-chan string {
	resp := make(chan string)

	messages := make([]map[string]string, 0)
	for _, item := range history {
		role := item["role"]
		content := item["content"]
		messages = append(messages, map[string]string{
			"role":    role,
			"content": content,
		})
	}

	payload := map[string]interface{}{
		"model":       ai.Model,
		"stream":      true,
		"messages":    messages,
		"top_p":       0.8,
		"temperature": 0.6,
	}

	jsonPayload, err := json.Marshal(payload)
	if err != nil {
		close(resp)
		return resp
	}

	url := fmt.Sprintf("%s/chat/completions", ai.BaseUrl)
	req, err := http.NewRequestWithContext(ctx, "POST", url, bytes.NewBuffer(jsonPayload))
	if err != nil {
		close(resp)
		return resp
	}

	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("Authorization", fmt.Sprintf("Bearer %s", ai.Key))

	client := &http.Client{}

	go func() {
		defer close(resp)

		response, err := client.Do(req)
		if err != nil {
			return
		}
		defer response.Body.Close()

		scanner := bufio.NewScanner(response.Body)
		for scanner.Scan() {
			line := scanner.Text()
			if line == "" {
				continue
			}

			// 处理SSE格式
			if strings.HasPrefix(line, "data: ") {
				data := line[6:] // 去掉 "data: " 前缀
				if data == "[DONE]" {
					return
				}

				var result map[string]interface{}
				if err := json.Unmarshal([]byte(data), &result); err != nil {
					continue
				}

				choices, ok := result["choices"].([]interface{})
				if !ok || len(choices) == 0 {
					continue
				}

				choice, ok := choices[0].(map[string]interface{})
				if !ok {
					continue
				}

				// 检查是否完成
				if finishReason, ok := choice["finish_reason"].(string); ok && finishReason == "stop" {
					continue
				}

				// 获取内容
				delta, ok := choice["delta"].(map[string]interface{})
				if !ok {
					continue
				}

				content, ok := delta["content"].(string)
				if ok {
					resp <- content
				}
			}
		}
	}()

	return resp
}
