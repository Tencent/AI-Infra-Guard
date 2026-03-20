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

// Package gologger error包装器
package gologger

import (
	"fmt"
)

// WarpError combines an existing error with an additional message
// 将现有的错误和新的错误信息组合成一个新的错误
// Parameters:
//   - err: original error object (原始错误对象)
//   - message: additional error message to append (要附加的额外错误信息)
//
// Returns:
//   - error: a new error combining both messages (返回组合后的新错误)
func WarpError(err error, message string) error {
	return fmt.Errorf("%s %s", err.Error(), message)
}
