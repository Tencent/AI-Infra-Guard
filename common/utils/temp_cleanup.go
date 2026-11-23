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
	"strings"
)

// TempCleanup removes task-scoped temporary files and directories after the
// scanner process exits. It is safe to call Close more than once.
type TempCleanup struct {
	paths []string
}

// NewTempCleanup creates an empty cleanup set.
func NewTempCleanup() *TempCleanup {
	return &TempCleanup{}
}

// Add records paths to remove. Empty paths are ignored.
func (c *TempCleanup) Add(paths ...string) {
	if c == nil {
		return
	}
	for _, path := range paths {
		if path = strings.TrimSpace(path); path != "" {
			c.paths = append(c.paths, path)
		}
	}
}

// Close removes every recorded path. Errors are intentionally ignored:
// cleanup must not turn a completed scan into a failed one.
func (c *TempCleanup) Close() {
	if c == nil {
		return
	}
	for _, path := range c.paths {
		_ = os.RemoveAll(path)
	}
	c.paths = nil
}
