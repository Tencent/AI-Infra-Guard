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

package httpx

import (
	"errors"
	"io"
	"testing"
)

type stubBody struct {
	readErr  error
	closeErr error
	closed   bool
}

func (s *stubBody) Read(p []byte) (int, error) {
	if s.readErr != nil {
		return 0, s.readErr
	}
	return 0, io.EOF
}

func (s *stubBody) Close() error {
	s.closed = true
	return s.closeErr
}

// TestReadAndCloseBodyClosesOnReadError: a mid-body reset must still close the
// body, or the connection leaks.
func TestReadAndCloseBodyClosesOnReadError(t *testing.T) {
	body := &stubBody{readErr: errors.New("connection reset")}
	if _, err := readAndCloseBody(body); err == nil {
		t.Fatal("expected the read error to be returned")
	}
	if !body.closed {
		t.Fatal("body was not closed after a read error")
	}
}

// TestReadAndCloseBodyReturnsCloseError: a close failure on the successful read
// path is still surfaced.
func TestReadAndCloseBodyReturnsCloseError(t *testing.T) {
	body := &stubBody{closeErr: errors.New("close failed")}
	if _, err := readAndCloseBody(body); err == nil {
		t.Fatal("expected the close error to be returned")
	}
	if !body.closed {
		t.Fatal("body should be marked closed")
	}
}

// TestReadAndCloseBodySuccess: the normal path returns no error and closes.
func TestReadAndCloseBodySuccess(t *testing.T) {
	body := &stubBody{}
	if _, err := readAndCloseBody(body); err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if !body.closed {
		t.Fatal("body was not closed on success")
	}
}
