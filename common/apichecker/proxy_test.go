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

package apichecker

import (
	"bufio"
	"encoding/json"
	"io"
	"net/http"
	"net/http/httptest"
	"path/filepath"
	"strings"
	"sync"
	"testing"
	"time"

	"github.com/Tencent/AI-Infra-Guard/pkg/database"
	"github.com/gin-gonic/gin"
	"github.com/stretchr/testify/require"
)

func newConfiguredProxyServer(
	t *testing.T,
	upstream string,
	username string,
	models ...*database.Model,
) *httptest.Server {
	t.Helper()

	db, err := database.InitDB(database.NewConfig(filepath.Join(t.TempDir(), "api-checker.db")))
	require.NoError(t, err)
	sqlDB, err := db.DB()
	require.NoError(t, err)
	t.Cleanup(func() { _ = sqlDB.Close() })

	taskStore := database.NewTaskStore(db)
	require.NoError(t, taskStore.Init())
	modelStore := database.NewModelStore(db)
	require.NoError(t, modelStore.Init())

	users := make(map[string]struct{})
	for _, model := range models {
		if _, exists := users[model.Username]; !exists {
			require.NoError(t, taskStore.CreateUser(&database.User{
				UserID:   "user-" + model.Username,
				Username: model.Username,
				Email:    model.Username + "@example.test",
			}))
			users[model.Username] = struct{}{}
		}
		require.NoError(t, modelStore.CreateModel(model))
	}

	handler, err := NewWithModelStore(upstream, modelStore)
	require.NoError(t, err)
	gin.SetMode(gin.TestMode)
	router := gin.New()
	handler.EnableConfiguredModelResolution(func(c *gin.Context) {
		c.Set("username", username)
		c.Next()
	})
	handler.Register(router)
	return httptest.NewServer(router)
}

func TestConfiguredRoutesCanBeRegisteredWithRelayProxy(t *testing.T) {
	upstream := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, _ *http.Request) {
		w.WriteHeader(http.StatusNoContent)
	}))
	defer upstream.Close()

	handler, err := NewWithModelStore(upstream.URL, database.NewModelStore(nil))
	require.NoError(t, err)
	router := gin.New()
	require.NotPanics(t, func() {
		handler.EnableConfiguredModelResolution(func(c *gin.Context) { c.Next() })
		handler.Register(router)
	})
}

func TestLegacyConfiguredRoutesAreNotRegistered(t *testing.T) {
	upstream := httptest.NewServer(http.NotFoundHandler())
	defer upstream.Close()
	proxy := newConfiguredProxyServer(t, upstream.URL, "public_user")
	defer proxy.Close()

	for _, test := range []struct {
		method string
		path   string
	}{
		{method: http.MethodGet, path: "/api/v1/api-checker/configured-models"},
		{method: http.MethodPost, path: "/api/v1/api-checker/configured-check/stream"},
	} {
		req, err := http.NewRequest(test.method, proxy.URL+test.path, nil)
		require.NoError(t, err)
		resp, err := http.DefaultClient.Do(req)
		require.NoError(t, err)
		require.Equal(t, http.StatusNotFound, resp.StatusCode)
		resp.Body.Close()
	}
}

func TestConfiguredCheckInjectsStoredCredentialsWithoutLeakingThem(t *testing.T) {
	type forwardedCheck struct {
		Algorithm  string `json:"algorithm"`
		BaseURL    string `json:"base_url"`
		APIKey     string `json:"api_key"`
		Model      string `json:"model"`
		Language   string `json:"language"`
		UseConfig  bool   `json:"use_configured_model"`
		ModelID    string `json:"model_id"`
		Iterations int    `json:"iterations"`
		NoThink    bool   `json:"no_think"`
	}
	requestSeen := make(chan forwardedCheck, 1)
	upstream := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		require.Equal(t, RelayPrefix+"/check/stream", r.URL.Path)
		require.Empty(t, r.Header.Get("Authorization"))
		var forwarded forwardedCheck
		require.NoError(t, json.NewDecoder(r.Body).Decode(&forwarded))
		requestSeen <- forwarded
		w.Header().Set("Content-Type", "text/event-stream")
		_, _ = io.WriteString(w, "event: done\ndata: {\"status\":0,\"message\":\"done\"}\n\n")
	}))
	defer upstream.Close()

	proxy := newConfiguredProxyServer(
		t,
		upstream.URL,
		"public_user",
		&database.Model{
			ModelID:   "system-default",
			Username:  "public_user",
			ModelName: "model-a",
			Token:     "stored-secret",
			BaseURL:   "https://stored.example.test/v1",
		},
	)
	defer proxy.Close()

	req, err := http.NewRequest(
		http.MethodPost,
		proxy.URL+RelayPrefix+"/check/stream",
		strings.NewReader(`{
			"use_configured_model": true,
			"model_id": "system-default",
			"algorithm": "quick",
			"iterations": 50,
			"no_think": true,
			"api_key": "browser-supplied-secret",
			"base_url": "https://attacker.example.test/v1",
			"model": "attacker-model"
		}`),
	)
	require.NoError(t, err)
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("X-Request-ID", "trace-api-checker-123")
	req.Header.Set("Authorization", "Bearer aig-session")

	resp, err := http.DefaultClient.Do(req)
	require.NoError(t, err)
	defer resp.Body.Close()
	body, err := io.ReadAll(resp.Body)
	require.NoError(t, err)

	require.Equal(t, http.StatusOK, resp.StatusCode)
	require.NotContains(t, string(body), "stored-secret")
	forwarded := <-requestSeen
	require.Equal(t, "quick", forwarded.Algorithm)
	require.Equal(t, "https://stored.example.test/v1", forwarded.BaseURL)
	require.Equal(t, "stored-secret", forwarded.APIKey)
	require.Equal(t, "model-a", forwarded.Model)
	require.Equal(t, "zh", forwarded.Language)
	require.False(t, forwarded.UseConfig)
	require.Empty(t, forwarded.ModelID)
	require.Equal(t, 50, forwarded.Iterations)
	require.True(t, forwarded.NoThink)
}

func TestConfiguredCheckForwardsEnglishResultLanguage(t *testing.T) {
	type forwardedCheck struct {
		Language string `json:"language"`
	}
	requestSeen := make(chan forwardedCheck, 1)
	upstream := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		var forwarded forwardedCheck
		require.NoError(t, json.NewDecoder(r.Body).Decode(&forwarded))
		requestSeen <- forwarded
		w.Header().Set("Content-Type", "text/event-stream")
		_, _ = io.WriteString(w, "event: done\ndata: {\"status\":0,\"message\":\"done\"}\n\n")
	}))
	defer upstream.Close()

	proxy := newConfiguredProxyServer(
		t,
		upstream.URL,
		"public_user",
		&database.Model{
			ModelID:   "system-default",
			Username:  "public_user",
			ModelName: "model-a",
			Token:     "stored-secret",
			BaseURL:   "https://stored.example.test/v1",
		},
	)
	defer proxy.Close()

	resp, err := http.Post(
		proxy.URL+RelayPrefix+"/check/stream",
		"application/json",
		strings.NewReader(
			`{"use_configured_model":true,"model_id":"system-default","algorithm":"quick","language":"en"}`,
		),
	)
	require.NoError(t, err)
	defer resp.Body.Close()

	require.Equal(t, http.StatusOK, resp.StatusCode)
	require.Equal(t, "en", (<-requestSeen).Language)
}

func TestConfiguredCheckRequiresModelID(t *testing.T) {
	upstreamCalled := false
	upstream := httptest.NewServer(http.HandlerFunc(func(http.ResponseWriter, *http.Request) {
		upstreamCalled = true
	}))
	defer upstream.Close()
	proxy := newConfiguredProxyServer(t, upstream.URL, "public_user")
	defer proxy.Close()

	resp, err := http.Post(
		proxy.URL+RelayPrefix+"/check/stream",
		"application/json",
		strings.NewReader(`{"use_configured_model":true,"algorithm":"quick"}`),
	)
	require.NoError(t, err)
	defer resp.Body.Close()
	body, err := io.ReadAll(resp.Body)
	require.NoError(t, err)

	require.Equal(t, http.StatusBadRequest, resp.StatusCode)
	require.Contains(t, string(body), "model_id")
	require.False(t, upstreamCalled)
}

func TestConfiguredCheckRejectsAnotherUsersModel(t *testing.T) {
	upstreamCalled := false
	upstream := httptest.NewServer(http.HandlerFunc(func(http.ResponseWriter, *http.Request) {
		upstreamCalled = true
	}))
	defer upstream.Close()

	proxy := newConfiguredProxyServer(
		t,
		upstream.URL,
		"alice",
		&database.Model{
			ModelID:   "bob-model",
			Username:  "bob",
			ModelName: "model-b",
			Token:     "bob-secret",
			BaseURL:   "https://bob.example.test/v1",
		},
	)
	defer proxy.Close()

	resp, err := http.Post(
		proxy.URL+RelayPrefix+"/check/stream",
		"application/json",
		strings.NewReader(`{"use_configured_model":true,"model_id":"bob-model","algorithm":"quick"}`),
	)
	require.NoError(t, err)
	defer resp.Body.Close()

	require.Equal(t, http.StatusNotFound, resp.StatusCode)
	require.False(t, upstreamCalled)
}

func newProxyServer(t *testing.T, upstream string) *httptest.Server {
	t.Helper()

	handler, err := New(upstream)
	require.NoError(t, err)

	gin.SetMode(gin.TestMode)
	router := gin.New()
	handler.Register(router)
	return httptest.NewServer(router)
}

func TestRelayModelsJSON(t *testing.T) {
	type requestDetails struct {
		path  string
		query string
	}
	requestSeen := make(chan requestDetails, 1)
	upstream := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		requestSeen <- requestDetails{path: r.URL.Path, query: r.URL.RawQuery}
		w.Header().Set("Content-Type", "application/json")
		_, _ = io.WriteString(w, `{"status":0,"data":{"models":["model-a"]}}`)
	}))
	defer upstream.Close()

	proxy := newProxyServer(t, upstream.URL)
	defer proxy.Close()

	resp, err := http.Get(proxy.URL + "/api/v1/relay/models?algorithm=full")
	require.NoError(t, err)
	defer resp.Body.Close()

	body, err := io.ReadAll(resp.Body)
	require.NoError(t, err)
	require.Equal(t, http.StatusOK, resp.StatusCode)
	require.Equal(t, "application/json", resp.Header.Get("Content-Type"))
	require.JSONEq(t, `{"status":0,"data":{"models":["model-a"]}}`, string(body))
	details := <-requestSeen
	require.Equal(t, "/api/v1/relay/models", details.path)
	require.Equal(t, "algorithm=full", details.query)
}

func TestManualCheckPayloadPassesThroughUnifiedEndpoint(t *testing.T) {
	requestSeen := make(chan map[string]interface{}, 1)
	upstream := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		var payload map[string]interface{}
		require.NoError(t, json.NewDecoder(r.Body).Decode(&payload))
		requestSeen <- payload
		w.WriteHeader(http.StatusNoContent)
	}))
	defer upstream.Close()

	proxy := newProxyServer(t, upstream.URL)
	defer proxy.Close()
	payload := `{
		"use_configured_model": false,
		"algorithm": "quick",
		"base_url": "https://manual.example.test/v1",
		"api_key": "manual-secret",
		"model": "model-a",
		"language": "en"
	}`
	resp, err := http.Post(
		proxy.URL+RelayPrefix+"/check/stream",
		"application/json",
		strings.NewReader(payload),
	)
	require.NoError(t, err)
	defer resp.Body.Close()

	require.Equal(t, http.StatusNoContent, resp.StatusCode)
	forwarded := <-requestSeen
	require.NotContains(t, forwarded, "use_configured_model")
	require.NotContains(t, forwarded, "model_id")
	require.Equal(t, "https://manual.example.test/v1", forwarded["base_url"])
	require.Equal(t, "manual-secret", forwarded["api_key"])
	require.Equal(t, "model-a", forwarded["model"])
	require.Equal(t, "en", forwarded["language"])
}

func TestRelaySSEFlushesImmediately(t *testing.T) {
	firstEventWritten := make(chan struct{})
	releaseUpstream := make(chan struct{})
	var releaseOnce sync.Once
	release := func() {
		releaseOnce.Do(func() {
			close(releaseUpstream)
		})
	}
	defer release()

	type requestDetails struct {
		path   string
		method string
	}
	requestSeen := make(chan requestDetails, 1)

	upstream := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		requestSeen <- requestDetails{path: r.URL.Path, method: r.Method}

		w.Header().Set("Content-Type", "text/event-stream")
		w.WriteHeader(http.StatusOK)
		_, _ = io.WriteString(w, "event: progress\ndata: {\"completed_rate\":0.5}\n\n")
		w.(http.Flusher).Flush()
		close(firstEventWritten)

		<-releaseUpstream
		_, _ = io.WriteString(w, "event: done\ndata: {}\n\n")
		w.(http.Flusher).Flush()
	}))
	defer upstream.Close()

	proxy := newProxyServer(t, upstream.URL)
	defer proxy.Close()

	req, err := http.NewRequest(
		http.MethodPost,
		proxy.URL+"/api/v1/relay/check/stream",
		strings.NewReader(`{"api_key":"must-not-be-logged","model":"model-a"}`),
	)
	require.NoError(t, err)
	req.Header.Set("Content-Type", "application/json")

	type responseResult struct {
		response *http.Response
		err      error
	}
	responseCh := make(chan responseResult, 1)
	go func() {
		resp, requestErr := http.DefaultClient.Do(req)
		responseCh <- responseResult{response: resp, err: requestErr}
	}()

	select {
	case <-firstEventWritten:
	case <-time.After(2 * time.Second):
		t.Fatal("upstream did not write the first SSE event")
	}
	details := <-requestSeen
	require.Equal(t, "/api/v1/relay/check/stream", details.path)
	require.Equal(t, http.MethodPost, details.method)

	var resp *http.Response
	select {
	case result := <-responseCh:
		require.NoError(t, result.err)
		resp = result.response
	case <-time.After(2 * time.Second):
		t.Fatal("proxy buffered the SSE response headers")
	}
	defer resp.Body.Close()
	require.Equal(t, "text/event-stream", resp.Header.Get("Content-Type"))

	firstLineCh := make(chan string, 1)
	reader := bufio.NewReader(resp.Body)
	go func() {
		line, _ := reader.ReadString('\n')
		firstLineCh <- line
	}()

	select {
	case line := <-firstLineCh:
		require.Equal(t, "event: progress\n", line)
	case <-time.After(2 * time.Second):
		t.Fatal("proxy did not flush the first SSE event immediately")
	}

	release()
	rest, err := io.ReadAll(reader)
	require.NoError(t, err)
	require.Contains(t, string(rest), "event: done")
}

func TestUIAndStaticPathsStripPrefix(t *testing.T) {
	upstream := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		_ = json.NewEncoder(w).Encode(map[string]string{
			"path":  r.URL.Path,
			"query": r.URL.RawQuery,
		})
	}))
	defer upstream.Close()

	proxy := newProxyServer(t, upstream.URL)
	defer proxy.Close()

	tests := []struct {
		name      string
		request   string
		wantPath  string
		wantQuery string
		finalPath string
	}{
		{
			name:     "UI root",
			request:  "/api-checker/",
			wantPath: "/",
		},
		{
			name:      "UI root without trailing slash",
			request:   "/api-checker?from=test",
			wantPath:  "/",
			wantQuery: "from=test",
			finalPath: "/api-checker/",
		},
		{
			name:      "static asset",
			request:   "/api-checker/static/app.js?v=17",
			wantPath:  "/static/app.js",
			wantQuery: "v=17",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			resp, err := http.Get(proxy.URL + tt.request)
			require.NoError(t, err)
			defer resp.Body.Close()

			var got map[string]string
			require.NoError(t, json.NewDecoder(resp.Body).Decode(&got))
			require.Equal(t, tt.wantPath, got["path"])
			require.Equal(t, tt.wantQuery, got["query"])
			if tt.finalPath != "" {
				require.Equal(t, tt.finalPath, resp.Request.URL.Path)
			}
		})
	}
}

func TestUIRootRedirectsBeforeProxying(t *testing.T) {
	upstreamCalled := false
	upstream := httptest.NewServer(http.HandlerFunc(func(http.ResponseWriter, *http.Request) {
		upstreamCalled = true
	}))
	defer upstream.Close()

	proxy := newProxyServer(t, upstream.URL)
	defer proxy.Close()

	client := &http.Client{
		CheckRedirect: func(*http.Request, []*http.Request) error {
			return http.ErrUseLastResponse
		},
	}
	resp, err := client.Get(proxy.URL + "/api-checker?from=test")
	require.NoError(t, err)
	defer resp.Body.Close()

	require.Equal(t, http.StatusPermanentRedirect, resp.StatusCode)
	require.Equal(t, "/api-checker/?from=test", resp.Header.Get("Location"))
	require.False(t, upstreamCalled)
}

func TestProxyDoesNotForwardAIGSessionHeaders(t *testing.T) {
	headersSeen := make(chan http.Header, 1)
	upstream := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		headersSeen <- r.Header.Clone()
		w.WriteHeader(http.StatusNoContent)
	}))
	defer upstream.Close()

	proxy := newProxyServer(t, upstream.URL)
	defer proxy.Close()

	req, err := http.NewRequest(http.MethodPost, proxy.URL+"/api/v1/relay/check/stream", strings.NewReader("{}"))
	require.NoError(t, err)
	req.Header.Set("Accept", "text/event-stream")
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("X-Request-ID", "trace-api-checker-123")
	req.Header.Set("Authorization", "Bearer aig-session")
	req.Header.Set("Cookie", "session=aig-session")
	req.Header.Set("X-APIKey", "aig-api-key")
	req.Header.Set("Staffname", "employee")

	resp, err := http.DefaultClient.Do(req)
	require.NoError(t, err)
	defer resp.Body.Close()
	require.Equal(t, http.StatusNoContent, resp.StatusCode)

	got := <-headersSeen
	require.Equal(t, "text/event-stream", got.Get("Accept"))
	require.Equal(t, "application/json", got.Get("Content-Type"))
	require.Equal(t, "trace-api-checker-123", got.Get("X-Request-ID"))
	require.Empty(t, got.Get("Authorization"))
	require.Empty(t, got.Get("Cookie"))
	require.Empty(t, got.Get("X-APIKey"))
	require.Empty(t, got.Get("Staffname"))
}

func TestUnavailableUpstreamReturnsSafeJSON(t *testing.T) {
	closedUpstream := httptest.NewServer(http.HandlerFunc(func(http.ResponseWriter, *http.Request) {}))
	upstreamURL := closedUpstream.URL
	closedUpstream.Close()

	proxy := newProxyServer(t, upstreamURL)
	defer proxy.Close()

	const secret = "sk-never-echo-this"
	req, err := http.NewRequest(
		http.MethodPost,
		proxy.URL+"/api/v1/relay/check/stream",
		strings.NewReader(`{"api_key":"`+secret+`"}`),
	)
	require.NoError(t, err)
	req.Header.Set("API-KEY", secret)

	resp, err := http.DefaultClient.Do(req)
	require.NoError(t, err)
	defer resp.Body.Close()

	body, err := io.ReadAll(resp.Body)
	require.NoError(t, err)
	require.Equal(t, http.StatusBadGateway, resp.StatusCode)
	require.Equal(t, "application/json; charset=utf-8", resp.Header.Get("Content-Type"))
	require.NotContains(t, string(body), secret)
	require.NotContains(t, string(body), upstreamURL)
	require.JSONEq(t, `{
		"status": 1,
		"message": "API checker upstream unavailable",
		"data": null
	}`, string(body))
}

func TestNewRejectsInvalidUpstream(t *testing.T) {
	for _, upstream := range []string{
		"",
		"api-checker:8000",
		"ftp://api-checker:8000",
		"http://user:secret@api-checker:8000",
		"http://api-checker:8000?secret=value",
	} {
		_, err := New(upstream)
		require.Error(t, err)
	}
}
