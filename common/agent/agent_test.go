package agent

import (
	"encoding/json"
	"fmt"
	"strings"
	"time"

	"testing"

	"github.com/stretchr/testify/assert"
)

// TestLargeDataSend 测试发送大字节数据
func TestLargeDataSend(t *testing.T) {
	// 创建Agent实例（不连接到真实服务器）
	agent := NewAgent(AgentConfig{
		ServerURL: "ws://xx/api/v1/agents/ws", // 使用测试URL
		Info: AgentInfo{
			ID:       "test-large-data",
			HostName: "test-host",
			IP:       "127.0.0.1",
			Version:  "0.1",
			Metadata: "",
		},
	})
	err := agent.connect()
	assert.NoError(t, err)
	// 启动各种协程
	go agent.handleSend()
	go agent.handleReceive()

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

	// 等待一小段时间确保消息被处理
	time.Sleep(5 * time.Second)

	t.Log("大字节数据发送测试完成")
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
