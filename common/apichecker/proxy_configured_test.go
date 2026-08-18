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
	"encoding/json"
	"io"
	"net/http"
	"net/http/httptest"
	"path/filepath"
	"strings"
	"testing"

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
