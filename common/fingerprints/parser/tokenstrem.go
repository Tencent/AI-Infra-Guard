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

// Package parser 实现词法分析栈结构
package parser

import "errors"

// TokenStream represents a stream of tokens that can be traversed
// 表示一个可以遍历的 token 流
type tokenStream struct {
	tokens      []Token // slice of tokens to process 要处理的token切片
	index       int     // current position in the stream 当前处理位置
	tokenLength int     // total number of tokens 总token数量
}

// newTokenStream creates a new token stream from a slice of tokens
// 从token切片创建新的token流
func newTokenStream(tokens []Token) *tokenStream {
	ret := new(tokenStream)
	ret.tokens = tokens
	ret.tokenLength = len(tokens)
	return ret
}

// rewind moves the current position back by one
// 将当前位置回退一步
func (ts *tokenStream) rewind() {
	ts.index -= 1
}

// next returns the next token in the stream and advances the position
// 返回流中的下一个token并前进位置
func (ts *tokenStream) next() (Token, error) {
	// Fix the logic error: check bounds before accessing token
	if ts.index >= len(ts.tokens) {
		return Token{}, errors.New("token index great token's length")
	}
	token := ts.tokens[ts.index]
	ts.index += 1
	return token, nil
}

// hasNext checks if there are more tokens available in the stream
// 检查流中是否还有更多token可用
func (ts tokenStream) hasNext() bool {
	return ts.index < ts.tokenLength
}
