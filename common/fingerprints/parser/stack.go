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

// Package parser 实现栈结构
package parser

import (
	"container/list"
)

// Stack represents a LIFO (Last In First Out) data structure
// 使用Go标准库中的list实现栈结构
type Stack struct {
	list *list.List
}

// NewStack creates and initializes a new Stack
// 创建并初始化一个新的栈
func NewStack() *Stack {
	return &Stack{list: list.New()}
}

// pop removes and returns the top element from the stack
// 从栈顶移除并返回元素，如果栈为空则返回nil
func (stack *Stack) pop() interface{} {
	e := stack.list.Back()
	if e != nil {
		stack.list.Remove(e)
		return e.Value
	}
	return nil
}

// push adds a new element to the top of the stack
// 将新元素添加到栈顶
func (stack *Stack) push(v interface{}) {
	stack.list.PushBack(v)
}

// isEmpty checks if the stack has no elements
// 检查栈是否为空
func (stack *Stack) isEmpty() bool {
	return stack.list.Len() == 0
}

// top returns the top element without removing it from the stack
// 返回栈顶元素但不移除它，如果栈为空则返回nil
func (stack *Stack) top() interface{} {
	e := stack.list.Back()
	if e != nil {
		return e.Value
	}
	return nil
}
