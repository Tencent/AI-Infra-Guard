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
