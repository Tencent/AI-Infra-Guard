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

// Package apichecker exposes the API checker sidecar through the AIG HTTP
// server without inspecting or buffering sensitive request bodies.
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
	// UIPrefix is removed before requests are forwarded to the checker.
	UIPrefix = "/api-checker"
	// ConfigPrefix contains AIG-only authenticated credential selection APIs.
	ConfigPrefix = "/api/v1/api-checker"
)

var forwardedRequestHeaders = []string{
	"Accept",
	"Accept-Encoding",
	"Content-Type",
	"If-Modified-Since",
	"If-None-Match",
	"Range",
	"User-Agent",
}

// Handler proxies API checker requests to one configured upstream.
type Handler struct {
	proxy      *httputil.ReverseProxy
	modelStore *database.ModelStore
}

// New creates an API checker proxy. Upstream must be an absolute HTTP(S) URL,
// for example http://api-checker:8000.
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
		rewriteUIPath(req.URL)
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
	if c.Request.URL.Path == UIPrefix {
		location := UIPrefix + "/"
		if c.Request.URL.RawQuery != "" {
			location += "?" + c.Request.URL.RawQuery
		}
		c.Redirect(http.StatusPermanentRedirect, location)
		return
	}
	h.proxy.ServeHTTP(c.Writer, c.Request)
}

// Register mounts the relay API and prefixed checker UI routes.
func (h *Handler) Register(router gin.IRouter) {
	router.Any(RelayPrefix+"/*path", h.Serve)
	router.Any(UIPrefix, h.Serve)
	router.Any(UIPrefix+"/*path", h.Serve)
}

// RegisterConfigured mounts the authenticated endpoint for checking with
// credentials already saved in AIG. Model discovery reuses /api/v1/app/models.
// It must be called before Register.
func (h *Handler) RegisterConfigured(router gin.IRouter, auth gin.HandlerFunc) {
	if h.modelStore == nil {
		return
	}
	group := router.Group(ConfigPrefix)
	group.Use(auth)
	group.POST("/configured-check/stream", h.checkWithConfiguredModel)
}

type configuredCheckRequest struct {
	ConfiguredModelID string `json:"configured_model_id"`
	Algorithm         string `json:"algorithm"`
	Language          string `json:"language"`
	Iterations        int    `json:"iterations"`
	NoThink           bool   `json:"no_think"`
}

func (h *Handler) checkWithConfiguredModel(c *gin.Context) {
	var request configuredCheckRequest
	if err := c.ShouldBindJSON(&request); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"detail": "请求体字段校验失败"})
		return
	}
	if strings.TrimSpace(request.ConfiguredModelID) == "" {
		c.JSON(http.StatusBadRequest, gin.H{"detail": "configured_model_id 不能为空"})
		return
	}
	model, err := h.modelStore.GetModelByUser(request.ConfiguredModelID, c.GetString("username"))
	if err != nil {
		// Public/system and YAML models are visible through GetUserModels too.
		model, err = h.resolveVisibleModel(request.ConfiguredModelID, c.GetString("username"))
	}
	if err != nil || model == nil {
		c.JSON(http.StatusNotFound, gin.H{"detail": "模型配置不存在或无权使用"})
		return
	}
	language := strings.TrimSpace(request.Language)
	if language == "" {
		language = "zh"
	}
	body, err := json.Marshal(gin.H{
		"algorithm":  request.Algorithm,
		"base_url":   model.BaseURL,
		"api_key":    model.Token,
		"model":      model.ModelName,
		"language":   language,
		"iterations": request.Iterations,
		"no_think":   request.NoThink,
	})
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"detail": "创建检测请求失败"})
		return
	}
	c.Request.Body = io.NopCloser(bytes.NewReader(body))
	c.Request.ContentLength = int64(len(body))
	c.Request.URL.Path = RelayPrefix + "/check/stream"
	c.Request.URL.RawPath = ""
	h.Serve(c)
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

func rewriteUIPath(requestURL *url.URL) {
	requestURL.Path = stripUIPrefix(requestURL.Path)
	if requestURL.RawPath != "" {
		requestURL.RawPath = stripUIPrefix(requestURL.RawPath)
	}
}

func stripUIPrefix(path string) string {
	switch {
	case path == UIPrefix, path == UIPrefix+"/":
		return "/"
	case strings.HasPrefix(path, UIPrefix+"/"):
		return strings.TrimPrefix(path, UIPrefix)
	default:
		return path
	}
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
