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

// Package httpx title 提取测试
package httpx

import (
	"testing"

	"github.com/stretchr/testify/assert"
)

// TestExtractTitle_Normal 测试正常 HTML 提取 title
func TestExtractTitle_Normal(t *testing.T) {
	html := "<html><head><title>Hello World</title></head><body></body></html>"
	title := ExtractTitle(html)
	assert.Equal(t, "Hello World", title, "应提取出 title 内容")
}

// TestExtractTitle_Empty 测试无 title 标签时返回空字符串
func TestExtractTitle_Empty(t *testing.T) {
	html := "<html><head></head><body>no title here</body></html>"
	title := ExtractTitle(html)
	assert.Equal(t, "", title, "无 title 标签时应返回空字符串")
}

// TestExtractTitle_EmptyTag 测试 title 标签为空时返回空字符串
func TestExtractTitle_EmptyTag(t *testing.T) {
	html := "<html><head><title></title></head></html>"
	title := ExtractTitle(html)
	assert.Equal(t, "", title, "空 title 标签应返回空字符串")
}

// TestExtractTitle_CaseInsensitive 测试 title 标签大写也能匹配
func TestExtractTitle_CaseInsensitive(t *testing.T) {
	html := "<HTML><HEAD><TITLE>Case Test</TITLE></HEAD></HTML>"
	title := ExtractTitle(html)
	assert.Equal(t, "Case Test", title, "title 标签大写也应能正确提取")
}

// TestExtractTitle_WithAttributes 测试 title 标签带属性时也能提取
func TestExtractTitle_WithAttributes(t *testing.T) {
	html := `<html><head><title lang="zh">带属性标题</title></head></html>`
	title := ExtractTitle(html)
	assert.Equal(t, "带属性标题", title, "title 标签含属性时也应能正确提取")
}

// TestExtractTitle_HTMLEntities 测试 HTML 实体被正确反转义
func TestExtractTitle_HTMLEntities(t *testing.T) {
	html := "<html><head><title>AT&amp;T &lt;News&gt;</title></head></html>"
	title := ExtractTitle(html)
	// html.UnescapeString 应将 &amp; 转为 & , &lt; 转为 <
	assert.Equal(t, "AT&T <News>", title, "HTML 实体应被正确反转义")
}

// TestExtractTitle_MultipleTitle 测试多个 title 标签时只返回第一个
func TestExtractTitle_MultipleTitle(t *testing.T) {
	html := "<html><head><title>First</title></head><body><title>Second</title></body></html>"
	title := ExtractTitle(html)
	// 应只返回第一个 title
	assert.Equal(t, "First", title, "多个 title 标签时应只返回第一个")
}

// TestExtractTitle_EmptyInput 测试空字符串输入
func TestExtractTitle_EmptyInput(t *testing.T) {
	title := ExtractTitle("")
	assert.Equal(t, "", title, "空输入应返回空字符串")
}

// TestExtractTitle_ChineseTitle 测试中文 title 提取
func TestExtractTitle_ChineseTitle(t *testing.T) {
	html := "<html><head><title>腾讯安全平台</title></head></html>"
	title := ExtractTitle(html)
	assert.Equal(t, "腾讯安全平台", title, "中文 title 应正确提取")
}
