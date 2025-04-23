package models

import (
	"context"
	"fmt"
	"testing"
)

func TestHunyuanAI_ChatStream(t *testing.T) {
	// 创建HunyuanAI实例，指向模拟服务器
	ai := NewHunyuanAI("xx", "hunyuan", "")

	// 准备测试数据
	history := []map[string]string{
		{"role": "user", "content": "你好"},
	}
	stream := ai.ChatStream(context.Background(), history)

	// 收集结果
	for text := range stream {
		fmt.Print(text)
	}
}
