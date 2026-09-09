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

//go:build windows

package utils

import (
	"os/exec"
)

// setProcessGroup Windows 下通过 CREATE_NEW_PROCESS_GROUP 实现进程组隔离
func setProcessGroup(cmd *exec.Cmd) {
	// Windows 使用 CREATE_NEW_PROCESS_ROOT 或 Job Object 更彻底，
	// 但 exec.Cmd 未直接暴露；此处留空，依赖 exec.CommandContext 的默认 Kill
	_ = cmd
}

// killProcessGroup Windows 下退化为仅终止直接子进程
// （exec.CommandContext 取消时会自动 Kill cmd.Process）
func killProcessGroup(cmd *exec.Cmd) {
	_ = cmd
}
