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

//go:build !windows

package utils

import (
	"os/exec"
	"syscall"
)

// setProcessGroup 将子进程放入独立进程组，便于按组终止整个进程树
// （uv 会派生 Python 子进程，仅杀 uv 自身会留下孤儿进程继续发送请求）
func setProcessGroup(cmd *exec.Cmd) {
	cmd.SysProcAttr = &syscall.SysProcAttr{Setpgid: true}
}

// killProcessGroup 向整个进程组发送 SIGKILL，终止 cmd 及其所有子进程
func killProcessGroup(cmd *exec.Cmd) {
	if cmd.Process != nil {
		// 负 PID 表示向进程组整体发送信号
		_ = syscall.Kill(-cmd.Process.Pid, syscall.SIGKILL)
	}
}
