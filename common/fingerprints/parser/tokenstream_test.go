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
	"github.com/stretchr/testify/require"
)

// TestTokenStream_HasNext_Empty 测试空 token 流的 hasNext
func TestTokenStream_HasNext_Empty(t *testing.T) {
	ts := newTokenStream([]Token{})
	// 空流没有下一个 token
	assert.False(t, ts.hasNext(), "空 tokenStream 的 hasNext 应返回 false")
}

// TestTokenStream_HasNext_NonEmpty 测试非空 token 流的 hasNext
func TestTokenStream_HasNext_NonEmpty(t *testing.T) {
	tokens := []Token{
		{name: tokenText, content: "hello"},
	}
	ts := newTokenStream(tokens)
	// 有元素时 hasNext 应返回 true
	assert.True(t, ts.hasNext(), "非空 tokenStream 的 hasNext 应返回 true")
}

// TestTokenStream_Next 测试 next 依次返回 token
func TestTokenStream_Next(t *testing.T) {
	tokens := []Token{
		{name: tokenText, content: "first"},
		{name: tokenText, content: "second"},
	}
	ts := newTokenStream(tokens)

	// 第一次调用 next 返回第一个 token
	tok, err := ts.next()
	require.NoError(t, err, "第一次 next 不应报错")
	assert.Equal(t, "first", tok.content, "第一次 next 应返回 'first'")

	// 第二次调用 next 返回第二个 token
	tok, err = ts.next()
	require.NoError(t, err, "第二次 next 不应报错")
	assert.Equal(t, "second", tok.content, "第二次 next 应返回 'second'")

	// 流已耗尽，hasNext 应返回 false
	assert.False(t, ts.hasNext(), "所有 token 消费后 hasNext 应返回 false")
}

// TestTokenStream_Next_Exhausted 测试超出范围时 next 返回错误
func TestTokenStream_Next_Exhausted(t *testing.T) {
	ts := newTokenStream([]Token{})
	// 空流调用 next 应返回错误
	_, err := ts.next()
	assert.Error(t, err, "空流调用 next 应返回错误")
}

// TestTokenStream_Rewind 测试 rewind 回退一步
func TestTokenStream_Rewind(t *testing.T) {
	tokens := []Token{
		{name: tokenText, content: "a"},
		{name: tokenText, content: "b"},
	}
	ts := newTokenStream(tokens)

	// 消费第一个 token
	tok, err := ts.next()
	require.NoError(t, err)
	assert.Equal(t, "a", tok.content, "next 应返回 'a'")

	// 回退后再次 next 应返回同一个 token
	ts.rewind()
	tok, err = ts.next()
	require.NoError(t, err, "rewind 后 next 不应报错")
	assert.Equal(t, "a", tok.content, "rewind 后 next 应再次返回 'a'")
}

// TestTokenStream_HasNext_AfterConsumingAll 测试消费完所有 token 后 hasNext
func TestTokenStream_HasNext_AfterConsumingAll(t *testing.T) {
	tokens := []Token{
		{name: tokenAnd, content: "&&"},
	}
	ts := newTokenStream(tokens)

	assert.True(t, ts.hasNext(), "消费前 hasNext 应为 true")
	_, err := ts.next()
	require.NoError(t, err)
	// 消费完后 hasNext 应为 false
	assert.False(t, ts.hasNext(), "消费完所有 token 后 hasNext 应为 false")
}

// TestTokenStream_RewindThenHasNext 测试 rewind 后 hasNext 的行为
func TestTokenStream_RewindThenHasNext(t *testing.T) {
	tokens := []Token{
		{name: tokenText, content: "x"},
	}
	ts := newTokenStream(tokens)

	// 消费唯一的 token
	_, err := ts.next()
	require.NoError(t, err)
	assert.False(t, ts.hasNext(), "消费后 hasNext 应为 false")

	// rewind 回退后 hasNext 应重新为 true
	ts.rewind()
	assert.True(t, ts.hasNext(), "rewind 后 hasNext 应重新为 true")
}

// TestTokenStream_MultipleTokens_Sequential 测试顺序消费多个 token
func TestTokenStream_MultipleTokens_Sequential(t *testing.T) {
	// 使用真实解析器生成 token，验证 tokenStream 与解析流程集成
	tokens, err := ParseTokens(`body="test" && header="x-header"`)
	require.NoError(t, err, "ParseTokens 不应报错")

	ts := newTokenStream(tokens)
	count := 0
	for ts.hasNext() {
		_, err := ts.next()
		require.NoError(t, err)
		count++
	}
	// 应恰好消费完所有 token
	assert.Equal(t, len(tokens), count, "消费的 token 数应等于总 token 数")
}
