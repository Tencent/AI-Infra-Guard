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
	"encoding/json"
	"fmt"
	"net/http"
	"net/http/httputil"
	"net/url"
	"strings"

	"github.com/gin-gonic/gin"
)

const (
	// RelayPrefix is forwarded to the checker without changing the path.
	RelayPrefix = "/api/v1/relay"
	// UIPrefix is removed before requests are forwarded to the checker.
	UIPrefix = "/api-checker"
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
	proxy *httputil.ReverseProxy
}

// New creates an API checker proxy. Upstream must be an absolute HTTP(S) URL,
// for example http://api-checker:8000.
func New(upstream string) (*Handler, error) {
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

	return &Handler{proxy: proxy}, nil
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
