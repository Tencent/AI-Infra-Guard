package utils

import (
	"net/http"
	"net/http/httptest"
	"path/filepath"
	"strings"
	"testing"
	"time"
)

// unresponsiveServer accepts requests but never answers until released.
func unresponsiveServer(t *testing.T) string {
	t.Helper()
	release := make(chan struct{})
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		select {
		case <-release:
		case <-r.Context().Done():
		}
	}))
	t.Cleanup(func() {
		close(release)
		srv.Close()
	})
	return strings.TrimPrefix(srv.URL, "http://")
}

func shortTimeouts(t *testing.T) {
	t.Helper()
	oldH, oldR := responseHeaderTimeout, requestTimeout
	responseHeaderTimeout, requestTimeout = 200*time.Millisecond, 200*time.Millisecond
	t.Cleanup(func() { responseHeaderTimeout, requestTimeout = oldH, oldR })
}

func expectPrompt(t *testing.T, name string, fn func() error) {
	t.Helper()
	done := make(chan error, 1)
	go func() { done <- fn() }()
	select {
	case err := <-done:
		if err == nil {
			t.Fatalf("%s: expected an error from an unresponsive server", name)
		}
	case <-time.After(5 * time.Second):
		t.Fatalf("%s: still blocked on an unresponsive server", name)
	}
}

func TestAPICallsTimeOutOnUnresponsiveServer(t *testing.T) {
	shortTimeouts(t)
	server := unresponsiveServer(t)
	dir := t.TempDir()

	expectPrompt(t, "DownloadFile", func() error {
		return DownloadFile(server, "s1", "u", filepath.Join(dir, "out.bin"))
	})
	expectPrompt(t, "GetEvaluationsDetail", func() error {
		_, err := GetEvaluationsDetail(server, "x")
		return err
	})
	expectPrompt(t, "LoadRemoteFingerPrints", func() error {
		_, err := LoadRemoteFingerPrints(server)
		return err
	})
	expectPrompt(t, "LoadRemoteVulStruct", func() error {
		_, err := LoadRemoteVulStruct("http://" + server + "/v")
		return err
	})
}
