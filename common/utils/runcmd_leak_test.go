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
	"context"
	"runtime"
	"strconv"
	"testing"
	"time"
)

// TestRunCmdWithContextNoGoroutineLeakOnStartFailure: the reader goroutine was
// started before cmd.Start(). When Start fails it is never drained, so it
// blocks forever on the pipe or on the done channel. Repeated failures (a
// missing interpreter, a removed working dir) leak goroutines and file handles.
func TestRunCmdWithContextNoGoroutineLeakOnStartFailure(t *testing.T) {
	before := runtime.NumGoroutine()

	for i := 0; i < 20; i++ {
		name := "nonexistent-aig-binary-" + strconv.Itoa(i)
		if err := RunCmdWithContext(context.Background(), t.TempDir(), name, nil, func(string) {}); err == nil {
			t.Fatalf("expected Start to fail for missing binary %q", name)
		}
	}

	deadline := time.Now().Add(2 * time.Second)
	for time.Now().Before(deadline) {
		runtime.GC()
		if runtime.NumGoroutine()-before <= 5 {
			return
		}
		time.Sleep(50 * time.Millisecond)
	}
	t.Fatalf("goroutine leak on Start failure: before=%d after=%d", before, runtime.NumGoroutine())
}
