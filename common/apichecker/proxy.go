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

// Package apichecker exposes the API checker service through the AIG HTTP
// server. Detection bodies are bounded and kept only in memory when selecting
// credentials already stored in AIG.
package apichecker

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/http/httputil"
	"net/url"
	"strings"

	"github.com/Tencent/AI-Infra-Guard/pkg/database"
	"github.com/gin-gonic/gin"
)

const (
	// RelayPrefix is forwarded to the checker without changing the path.
	RelayPrefix = "/api/v1/relay"
	// ServicePrefix is removed for the API checker's documentation and health
	// endpoints. The checker frontend is deployed separately.
	ServicePrefix        = "/api-checker"
	maxCheckRequestBytes = 1 << 20
)

var servicePaths = []string{
	"/docs",
	"/redoc",
	"/openapi.json",
	"/healthz",
}

var forwardedRequestHeaders = []string{
	"Accept",
	"Accept-Encoding",
	"Content-Type",
	"If-Modified-Since",
	"If-None-Match",
	"Range",
	"User-Agent",
	"X-Request-ID",
}

// Handler proxies API checker requests to one configured upstream.
type Handler struct {
	proxy          *httputil.ReverseProxy
	modelStore     *database.ModelStore
	configuredAuth gin.HandlerFunc
}

// New creates an API checker proxy. Upstream must be an absolute HTTP(S) URL,
// for example http://agent:8000.
func New(upstream string) (*Handler, error) {
	return NewWithModelStore(upstream, nil)
}

// NewWithModelStore creates a proxy that can resolve AIG model credentials
// server-side. The stored token is never returned to the browser.
func NewWithModelStore(upstream string, modelStore *database.ModelStore) (*Handler, error) {
	target, err := url.Parse(strings.TrimSpace(upstream))
	if err != nil {
		return nil, fmt.Errorf("parse API checker upstream: %w", err)
	}
	if target.Scheme != "http" && target.Scheme != "https" {
		return nil, fmt.Errorf("API checker upstream must use http or https")
	}
	if target.Host == "" {
		return nil, fmt.Errorf("API checker upstream host is required")
	}
	if target.User != nil || target.RawQuery != "" || target.Fragment != "" {
		return nil, fmt.Errorf("API checker upstream must not contain credentials, query, or fragment")
	}

	proxy := httputil.NewSingleHostReverseProxy(target)
	director := proxy.Director
	proxy.Director = func(req *http.Request) {
		rewriteServicePath(req.URL)
		req.Header = checkerRequestHeaders(req.Header)
		director(req)
		req.Host = target.Host
	}

	// A negative interval flushes every write. This is required for the
	// checker's long-running text/event-stream response.
	proxy.FlushInterval = -1
	proxy.ErrorHandler = writeBadGateway

	return &Handler{proxy: proxy, modelStore: modelStore}, nil
}

// Serve forwards a Gin request to the API checker.
func (h *Handler) Serve(c *gin.Context) {
	if c.Request.Method == http.MethodPost &&
		c.Request.URL.Path == RelayPrefix+"/check/stream" {
		h.serveCheck(c)
		return
	}
	h.proxy.ServeHTTP(c.Writer, c.Request)
}

// Register mounts the relay API plus the checker's documentation and health
// endpoints. The checker frontend is deployed separately.
func (h *Handler) Register(router gin.IRouter) {
	router.Any(RelayPrefix+"/*path", h.Serve)
	for _, path := range servicePaths {
		router.Any(ServicePrefix+path, h.Serve)
	}
}

// EnableConfiguredModelResolution enables server-side credential resolution
// on POST /api/v1/relay/check/stream. Model discovery reuses
// GET /api/v1/app/models.
func (h *Handler) EnableConfiguredModelResolution(auth gin.HandlerFunc) {
	if h.modelStore != nil {
		h.configuredAuth = auth
	}
}

type checkSelector struct {
	UseConfiguredModel bool   `json:"use_configured_model"`
	ModelID            string `json:"model_id"`
}

func (h *Handler) serveCheck(c *gin.Context) {
	body, err := io.ReadAll(io.LimitReader(c.Request.Body, maxCheckRequestBytes+1))
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"detail": "读取检测请求失败"})
		return
	}
	if len(body) > maxCheckRequestBytes {
		c.JSON(http.StatusRequestEntityTooLarge, gin.H{"detail": "检测请求体过大"})
		return
	}
	c.Request.Body = io.NopCloser(bytes.NewReader(body))
	c.Request.ContentLength = int64(len(body))

	var selector checkSelector
	if json.Unmarshal(body, &selector) != nil {
		h.proxy.ServeHTTP(c.Writer, c.Request)
		return
	}
	if !selector.UseConfiguredModel {
		var payload map[string]interface{}
		if err := json.Unmarshal(body, &payload); err == nil {
			delete(payload, "use_configured_model")
			delete(payload, "model_id")
			if body, err = json.Marshal(payload); err != nil {
				c.JSON(http.StatusInternalServerError, gin.H{"detail": "创建检测请求失败"})
				return
			}
			c.Request.Body = io.NopCloser(bytes.NewReader(body))
			c.Request.ContentLength = int64(len(body))
		}
		h.proxy.ServeHTTP(c.Writer, c.Request)
		return
	}
	if h.modelStore == nil || h.configuredAuth == nil {
		c.JSON(http.StatusServiceUnavailable, gin.H{"detail": "AIG 模型配置不可用"})
		return
	}
	if strings.TrimSpace(selector.ModelID) == "" {
		c.JSON(http.StatusBadRequest, gin.H{"detail": "model_id 不能为空"})
		return
	}
	h.configuredAuth(c)
	if c.IsAborted() {
		return
	}

	model, err := h.modelStore.GetModelByUser(selector.ModelID, c.GetString("username"))
	if err != nil {
		// Public/system and YAML models are visible through GetUserModels too.
		model, err = h.resolveVisibleModel(selector.ModelID, c.GetString("username"))
	}
	if err != nil || model == nil {
		c.JSON(http.StatusNotFound, gin.H{"detail": "模型配置不存在或无权使用"})
		return
	}

	var payload map[string]interface{}
	if err := json.Unmarshal(body, &payload); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"detail": "请求体字段校验失败"})
		return
	}
	delete(payload, "use_configured_model")
	delete(payload, "model_id")
	payload["base_url"] = model.BaseURL
	payload["api_key"] = model.Token
	payload["model"] = model.ModelName
	language, _ := payload["language"].(string)
	if strings.TrimSpace(language) == "" {
		payload["language"] = "zh"
	}

	body, err = json.Marshal(payload)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"detail": "创建检测请求失败"})
		return
	}
	c.Request.Body = io.NopCloser(bytes.NewReader(body))
	c.Request.ContentLength = int64(len(body))
	c.Request.URL.Path = RelayPrefix + "/check/stream"
	c.Request.URL.RawPath = ""
	h.proxy.ServeHTTP(c.Writer, c.Request)
}

func (h *Handler) resolveVisibleModel(modelID, username string) (*database.Model, error) {
	models, err := h.modelStore.GetUserModels(username)
	if err != nil {
		return nil, err
	}
	for _, model := range models {
		if model.ModelID == modelID {
			return model, nil
		}
	}
	return nil, fmt.Errorf("model not found")
}

func rewriteServicePath(requestURL *url.URL) {
	requestURL.Path = stripServicePrefix(requestURL.Path)
	if requestURL.RawPath != "" {
		requestURL.RawPath = stripServicePrefix(requestURL.RawPath)
	}
}

func stripServicePrefix(path string) string {
	for _, servicePath := range servicePaths {
		if path == ServicePrefix+servicePath {
			return servicePath
		}
	}
	return path
}

func checkerRequestHeaders(source http.Header) http.Header {
	headers := make(http.Header, len(forwardedRequestHeaders))
	for _, name := range forwardedRequestHeaders {
		for _, value := range source.Values(name) {
			headers.Add(name, value)
		}
	}
	return headers
}

func writeBadGateway(w http.ResponseWriter, _ *http.Request, _ error) {
	w.Header().Set("Content-Type", "application/json; charset=utf-8")
	w.Header().Set("Cache-Control", "no-store")
	w.WriteHeader(http.StatusBadGateway)
	_ = json.NewEncoder(w).Encode(map[string]interface{}{
		"status":  1,
		"message": "API checker upstream unavailable",
		"data":    nil,
	})
}
