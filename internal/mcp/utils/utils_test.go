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

package utils

import (
	"os"
	"testing"

	"github.com/stretchr/testify/assert"
)

// requireMCPServer 跳过依赖容器内 /mcp-server 目录的用例。
func requireMCPServer(t *testing.T) {
	t.Helper()
	if _, err := os.Stat("/mcp-server"); err != nil {
		t.Skip("requires the in-container /mcp-server tree")
	}
}

func TestListDir(t *testing.T) {
	requireMCPServer(t)
	sb, err := ListDir("/mcp-server", -1, "")
	assert.NoError(t, err)
	t.Log(sb)
}

func TestGrepFile(t *testing.T) {
	requireMCPServer(t)
	sb, err := Grep("/mcp-server/src/mcp_server/server.py", "@mcp\\.tool.*\n.*def", 3)
	assert.NoError(t, err)
	t.Log(sb)
}

func TestGrepDirectory(t *testing.T) {
	requireMCPServer(t)
	sb, err := Grep("/mcp-server", "AppConfig", 3)
	assert.NoError(t, err)
	t.Log(sb)
	p := "SSE|streamable-http|EventSource"
	sb, err = Grep("/mcp-server", p, 3)
	assert.NoError(t, err)
	t.Log(sb)
}

func TestReadBigFile(t *testing.T) {
	requireMCPServer(t)
	sb, err := ReadFileChunk("/mcp-server/src/mcp_server/server.py", 0, 0, 10*1024)
	assert.NoError(t, err)
	t.Log(sb)

	sb, err = ReadFileChunk("/mcp-server/src/mcp_server/server.py", 0, 2, 10*1024)
	assert.NoError(t, err)
	t.Log(sb)
}

func TestReadSmallFile(t *testing.T) {
	requireMCPServer(t)
	sb, err := ReadFileChunk("/mcp-server/src/mcp_server/app_config.py", 0, 0, 10*1024)
	assert.NoError(t, err)
	t.Log(sb)
}
