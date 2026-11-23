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

package websocket

import (
	"fmt"
	"net/http"
	"sync"
	"sync/atomic"
	"testing"
	"time"
)

type overlapWriter struct {
	active  int32
	overlap int32
	delay   time.Duration
}

func (w *overlapWriter) Header() http.Header { return http.Header{} }

func (w *overlapWriter) WriteHeader(int) {}

func (w *overlapWriter) Flush() {}

func (w *overlapWriter) Write(p []byte) (int, error) {
	if atomic.AddInt32(&w.active, 1) > 1 {
		atomic.StoreInt32(&w.overlap, 1)
	}
	time.Sleep(w.delay)
	atomic.AddInt32(&w.active, -1)
	return len(p), nil
}

func TestSSEWritesAreSerialized(t *testing.T) {
	writer := &overlapWriter{delay: time.Millisecond}
	conn := &SSEConnection{SessionID: "sse-write", Writer: writer, Flusher: writer}
	sm := NewSSEManager()

	var wg sync.WaitGroup
	for worker := 0; worker < 2; worker++ {
		wg.Add(1)
		go func(worker int) {
			defer wg.Done()
			for i := 0; i < 20; i++ {
				_ = sm.sendEventToConnection(conn,
					fmt.Sprintf("event-%d-%d", worker, i),
					"statusUpdate",
					map[string]string{"worker": fmt.Sprint(worker)},
				)
			}
		}(worker)
	}
	wg.Wait()

	if atomic.LoadInt32(&writer.overlap) != 0 {
		t.Fatal("heartbeat/event writes overlapped on one SSE ResponseWriter")
	}
}
