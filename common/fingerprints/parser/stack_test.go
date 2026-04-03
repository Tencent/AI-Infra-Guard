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

package parser

import (
	"testing"

	"github.com/stretchr/testify/assert"
)

// TestStack_IsEmpty 测试空栈判断
func TestStack_IsEmpty(t *testing.T) {
	s := NewStack()
	// 新建的栈应该是空的
	assert.True(t, s.isEmpty(), "新建栈应为空")
}

// TestStack_PushAndIsEmpty 测试 push 后栈非空
func TestStack_PushAndIsEmpty(t *testing.T) {
	s := NewStack()
	s.push(1)
	// push 之后栈不应该为空
	assert.False(t, s.isEmpty(), "push 元素后栈不应为空")
}

// TestStack_Top 测试 top 方法返回栈顶元素但不弹出
func TestStack_Top(t *testing.T) {
	s := NewStack()
	s.push("hello")
	// top 应该返回栈顶元素
	assert.Equal(t, "hello", s.top(), "top 应返回栈顶元素 'hello'")
	// top 之后栈仍然非空
	assert.False(t, s.isEmpty(), "top 不应弹出元素，栈仍非空")
}

// TestStack_TopOnEmpty 测试空栈 top 返回 nil
func TestStack_TopOnEmpty(t *testing.T) {
	s := NewStack()
	// 空栈 top 应该返回 nil
	assert.Nil(t, s.top(), "空栈 top 应返回 nil")
}

// TestStack_Pop 测试 pop 方法弹出栈顶元素
func TestStack_Pop(t *testing.T) {
	s := NewStack()
	s.push(42)
	val := s.pop()
	// pop 应返回之前 push 的值
	assert.Equal(t, 42, val, "pop 应返回 42")
	// pop 之后栈应为空
	assert.True(t, s.isEmpty(), "pop 元素后栈应为空")
}

// TestStack_PopOnEmpty 测试空栈 pop 返回 nil
func TestStack_PopOnEmpty(t *testing.T) {
	s := NewStack()
	// 空栈 pop 应该返回 nil
	assert.Nil(t, s.pop(), "空栈 pop 应返回 nil")
}

// TestStack_LIFO 测试栈的后进先出顺序
func TestStack_LIFO(t *testing.T) {
	s := NewStack()
	// 依次压入三个元素
	s.push(1)
	s.push(2)
	s.push(3)

	// 弹出顺序应为 3、2、1（后进先出）
	assert.Equal(t, 3, s.pop(), "第一次 pop 应返回最后压入的 3")
	assert.Equal(t, 2, s.pop(), "第二次 pop 应返回 2")
	assert.Equal(t, 1, s.pop(), "第三次 pop 应返回最先压入的 1")
	assert.True(t, s.isEmpty(), "所有元素弹出后栈应为空")
}

// TestStack_MultiplePush 测试多次 push 和 top
func TestStack_MultiplePush(t *testing.T) {
	s := NewStack()
	s.push("a")
	s.push("b")
	s.push("c")

	// top 应返回最后压入的元素
	assert.Equal(t, "c", s.top(), "top 应返回最后压入的 'c'")
	// pop 后 top 应变为 "b"
	s.pop()
	assert.Equal(t, "b", s.top(), "pop 一次后 top 应为 'b'")
}

// TestStack_MixedTypes 测试压入不同类型的元素
func TestStack_MixedTypes(t *testing.T) {
	s := NewStack()
	s.push("string")
	s.push(100)
	s.push(3.14)

	// 按后进先出顺序验证
	assert.Equal(t, 3.14, s.pop(), "pop 应返回最后压入的 float64 值 3.14")
	assert.Equal(t, 100, s.pop(), "pop 应返回 int 值 100")
	assert.Equal(t, "string", s.pop(), "pop 应返回 string 值 'string'")
}
