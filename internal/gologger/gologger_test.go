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

package gologger

import (
	"bytes"
	"errors"
	"strings"
	"sync"
	"testing"
)

func testDebug() {
	Debug("test debug func")
}
func TestLogger(t *testing.T) {
	Debugln("test debug")
	testDebug()
	Infoln("test info")
	Warnln("test warn")
	Errorln("test error")
	WithError(errors.New("test error")).Errorln("error")
}

func TestLoggerFile(t *testing.T) {
	//writer1 := os.Stdout
	//writer2, err := os.OpenFile("test.txt", os.O_WRONLY|os.O_APPEND|os.O_CREATE, 0644)
	//defer writer2.Close()
	//if err != nil {
	//	log.Fatalf("create file log.txt failed: %v", err)
	//}
	//Logger.SetOutput(io.MultiWriter(writer1, writer2))
	//Infoln("test info")
}

// TestLoggerConcurrentCallerLookup logs from several goroutines at once. Run
// with -race: getCaller used to write a package-level variable on every call.
func TestLoggerConcurrentCallerLookup(t *testing.T) {
	logger := NewLogger()
	var buf bytes.Buffer
	logger.Logrus().SetOutput(&buf) // logrus serialises writes to the output

	const goroutines, perGoroutine = 8, 50
	var wg sync.WaitGroup
	for i := 0; i < goroutines; i++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			for j := 0; j < perGoroutine; j++ {
				logger.Infof("concurrent %d", j)
			}
		}()
	}
	wg.Wait()

	lines := strings.Split(strings.TrimSpace(buf.String()), "\n")
	if len(lines) != goroutines*perGoroutine {
		t.Fatalf("got %d log lines, want %d", len(lines), goroutines*perGoroutine)
	}
	for _, line := range lines {
		if !strings.Contains(line, "gologger_test.go:") {
			t.Fatalf("log line does not report the calling file: %q", line)
		}
	}
}
