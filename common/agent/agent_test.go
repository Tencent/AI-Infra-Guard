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

package agent

import (
	"encoding/json"
	"fmt"
	"net/http"
	"net/http/httptest"
	"strings"
	"time"

	"testing"

	"github.com/gorilla/websocket"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

// TestLargeDataSend 测试发送大字节数据
func TestLargeDataSend(t *testing.T) {
	// 启动本地 WebSocket 服务器，接收并校验 Agent 发出的消息
	received := make(chan map[string]interface{}, 8)
	serverDone := make(chan struct{})
	upgrader := websocket.Upgrader{}
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		conn, err := upgrader.Upgrade(w, r, nil)
		if err != nil {
			t.Errorf("服务器升级 WebSocket 失败: %v", err)
			return
		}
		defer conn.Close()
		defer close(serverDone)
		// 大数据消息可能超过默认读限制
		conn.SetReadLimit(1024 * 1024 * 10)
		for {
			_, data, err := conn.ReadMessage()
			if err != nil {
				return
			}
			var msg map[string]interface{}
			if err := json.Unmarshal(data, &msg); err != nil {
				t.Errorf("服务器反序列化消息失败: %v", err)
				return
			}
			received <- msg
		}
	}))
	defer server.Close()

	// 创建Agent实例，连接到本地测试服务器
	agent := NewAgent(AgentConfig{
		ServerURL: strings.Replace(server.URL, "http://", "ws://", 1),
		Info: AgentInfo{
			ID:       "test-large-data",
			HostName: "test-host",
			IP:       "127.0.0.1",
			Version:  "0.1",
			Metadata: "",
		},
	})
	err := agent.connect()
	require.NoError(t, err)
	// 启动发送协程
	go agent.handleSend()

	// 创建大数据内容 - 生成约1MB的数据
	largeContent := generateLargeContent(1024 * 1024) // 1MB

	// 创建包含大数据的任务结果
	largeResult := map[string]interface{}{
		"type":        "large_data_test",
		"timestamp":   time.Now().Unix(),
		"data_size":   len(largeContent),
		"content":     largeContent,
		"description": "测试发送大字节数据的能力",
		"metadata": map[string]interface{}{
			"compression": false,
			"encoding":    "utf-8",
			"chunks":      1,
		},
	}

	// 测试序列化大数据
	jsonData, err := json.Marshal(largeResult)
	assert.NoError(t, err, "大数据JSON序列化应该成功")

	dataSize := len(jsonData)
	t.Logf("生成的JSON数据大小: %d bytes (%.2f MB)", dataSize, float64(dataSize)/(1024*1024))

	// 测试通过sendChan发送大数据（模拟真实发送）
	sessionId := "test-session-large-data"

	// 发送大数据
	err = agent.SendTaskResult(sessionId, largeResult)
	assert.NoError(t, err, "发送大数据任务结果应该成功")

	// 等待服务器收到完整消息（跳过 register 等前置消息）
	deadline := time.After(30 * time.Second)
	for {
		select {
		case msg := <-received:
			if msg["type"] != AgentMsgTypeResultUpdate {
				continue
			}
			content, ok := msg["content"].(map[string]interface{})
			require.True(t, ok, "消息应包含 content 对象")
			event, ok := content["event"].(map[string]interface{})
			require.True(t, ok, "content 应包含 event 对象")
			result, ok := event["result"].(map[string]interface{})
			require.True(t, ok, "event 应包含 result 对象")
			assert.Equal(t, largeContent, result["content"], "服务器应收到完整的大数据内容")
			agent.Stop()
			<-serverDone
			t.Log("大字节数据发送测试完成")
			return
		case <-deadline:
			t.Fatal("等待服务器接收大数据消息超时")
		}
	}
}

// generateLargeContent 生成指定大小的大内容
func generateLargeContent(size int) string {
	// 创建基础模板
	template := "这是一段测试数据，用于验证大字节数据的传输能力。包含中文字符以测试编码处理。Data chunk %d. "

	var builder strings.Builder
	builder.Grow(size) // 预分配容量

	chunkCount := 0
	for builder.Len() < size {
		chunk := fmt.Sprintf(template, chunkCount)
		if builder.Len()+len(chunk) > size {
			// 添加剩余字符直到达到目标大小
			remaining := size - builder.Len()
			builder.WriteString(chunk[:remaining])
			break
		}
		builder.WriteString(chunk)
		chunkCount++
	}

	return builder.String()
}
