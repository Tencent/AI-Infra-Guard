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

// Package httpx provides HTTP client tests
package httpx

import (
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
	"time"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

// defaultOpts returns a safe set of options suitable for testing.
func defaultOpts() *HTTPOptions {
	return &HTTPOptions{
		Timeout:          10 * time.Second,
		RetryMax:         0,
		FollowRedirects:  true,
		DefaultUserAgent: "test-agent/1.0",
	}
}

// ---------------------------------------------------------------------------
// Constructor
// ---------------------------------------------------------------------------

func TestNewHttpx_Success(t *testing.T) {
	h, err := NewHttpx(defaultOpts())
	require.NoError(t, err)
	assert.NotNil(t, h)
	assert.NotNil(t, h.client)
	assert.NotNil(t, h.client2)
}

func TestNewHttpx_InvalidProxy(t *testing.T) {
	opts := defaultOpts()
	opts.HTTPProxy = "://bad-proxy"
	_, err := NewHttpx(opts)
	assert.Error(t, err)
}

func TestNewHttpx_CustomHeaders(t *testing.T) {
	opts := defaultOpts()
	opts.CustomHeaders = []string{"X-Custom: hello", "X-Another: world"}
	h, err := NewHttpx(opts)
	require.NoError(t, err)
	assert.Equal(t, " hello", h.CustomHeaders["X-Custom"])
	assert.Equal(t, " world", h.CustomHeaders["X-Another"])
}

func TestNewHttpx_MalformedCustomHeaders(t *testing.T) {
	opts := defaultOpts()
	// No colon – should be silently ignored
	opts.CustomHeaders = []string{"BadHeaderNoColon"}
	h, err := NewHttpx(opts)
	require.NoError(t, err)
	assert.Empty(t, h.CustomHeaders)
}

// ---------------------------------------------------------------------------
// GET request
// ---------------------------------------------------------------------------

func TestHTTPX_Get_Success(t *testing.T) {
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		assert.Equal(t, "test-agent/1.0", r.Header.Get("User-Agent"))
		w.WriteHeader(http.StatusOK)
		w.Write([]byte("<html><head><title>Hello Test</title></head></html>"))
	}))
	defer srv.Close()

	h, err := NewHttpx(defaultOpts())
	require.NoError(t, err)

	resp, err := h.Get(srv.URL, nil)
	require.NoError(t, err)
	assert.Equal(t, http.StatusOK, resp.StatusCode)
	assert.Equal(t, "Hello Test", resp.Title)
	assert.Contains(t, resp.DataStr, "Hello Test")
}

func TestHTTPX_Get_WithCustomHeaders(t *testing.T) {
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		assert.Equal(t, "myvalue", r.Header.Get("X-Test-Header"))
		w.WriteHeader(http.StatusOK)
	}))
	defer srv.Close()

	h, err := NewHttpx(defaultOpts())
	require.NoError(t, err)

	resp, err := h.Get(srv.URL, map[string]string{"X-Test-Header": "myvalue"})
	require.NoError(t, err)
	assert.Equal(t, http.StatusOK, resp.StatusCode)
}

func TestHTTPX_Get_NonOKStatus(t *testing.T) {
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusNotFound)
		w.Write([]byte("not found"))
	}))
	defer srv.Close()

	h, err := NewHttpx(defaultOpts())
	require.NoError(t, err)

	resp, err := h.Get(srv.URL, nil)
	require.NoError(t, err)
	assert.Equal(t, http.StatusNotFound, resp.StatusCode)
}

func TestHTTPX_Get_Redirect_Followed(t *testing.T) {
	finalHandler := http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
		w.Write([]byte("final destination"))
	})
	redirectHandler := http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path == "/" {
			http.Redirect(w, r, "/final", http.StatusFound)
			return
		}
		finalHandler.ServeHTTP(w, r)
	})
	srv := httptest.NewServer(redirectHandler)
	defer srv.Close()

	opts := defaultOpts()
	opts.FollowRedirects = true
	h, err := NewHttpx(opts)
	require.NoError(t, err)

	resp, err := h.Get(srv.URL, nil)
	require.NoError(t, err)
	assert.Equal(t, http.StatusOK, resp.StatusCode)
}

func TestHTTPX_Get_Redirect_NotFollowed(t *testing.T) {
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		http.Redirect(w, r, "/other", http.StatusFound)
	}))
	defer srv.Close()

	opts := defaultOpts()
	opts.FollowRedirects = false
	h, err := NewHttpx(opts)
	require.NoError(t, err)

	resp, err := h.Get(srv.URL, nil)
	require.NoError(t, err)
	assert.Equal(t, http.StatusFound, resp.StatusCode)
}

// ---------------------------------------------------------------------------
// POST request
// ---------------------------------------------------------------------------

func TestHTTPX_POST_Success(t *testing.T) {
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		assert.Equal(t, http.MethodPost, r.Method)
		w.WriteHeader(http.StatusCreated)
		w.Write([]byte(`{"ok":true}`))
	}))
	defer srv.Close()

	h, err := NewHttpx(defaultOpts())
	require.NoError(t, err)

	resp, err := h.POST(srv.URL, strings.NewReader(`{"key":"val"}`), nil)
	require.NoError(t, err)
	assert.Equal(t, http.StatusCreated, resp.StatusCode)
	assert.Contains(t, resp.DataStr, `"ok"`)
}

func TestHTTPX_POST_WithHeaders(t *testing.T) {
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		assert.Equal(t, "application/json", r.Header.Get("Content-Type"))
		w.WriteHeader(http.StatusOK)
	}))
	defer srv.Close()

	h, err := NewHttpx(defaultOpts())
	require.NoError(t, err)

	resp, err := h.POST(srv.URL, nil, map[string]string{"Content-Type": "application/json"})
	require.NoError(t, err)
	assert.Equal(t, http.StatusOK, resp.StatusCode)
}

// ---------------------------------------------------------------------------
// Timeout / error handling
// ---------------------------------------------------------------------------

func TestHTTPX_Get_InvalidURL(t *testing.T) {
	h, err := NewHttpx(defaultOpts())
	require.NoError(t, err)

	_, err = h.Get("://bad url", nil)
	assert.Error(t, err)
}

func TestHTTPX_Get_ConnectionRefused(t *testing.T) {
	opts := &HTTPOptions{
		Timeout:          2 * time.Second,
		RetryMax:         0,
		DefaultUserAgent: "test",
	}
	h, err := NewHttpx(opts)
	require.NoError(t, err)

	// Unlikely to have anything listening on this port
	_, err = h.Get("http://127.0.0.1:19999", nil)
	assert.Error(t, err)
}

// ---------------------------------------------------------------------------
// Response helpers
// ---------------------------------------------------------------------------

func TestHTTPX_Response_ContentLength(t *testing.T) {
	body := "hello world"
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Write([]byte(body))
	}))
	defer srv.Close()

	h, err := NewHttpx(defaultOpts())
	require.NoError(t, err)

	resp, err := h.Get(srv.URL, nil)
	require.NoError(t, err)
	// ContentLength should match rune count of the body
	assert.Equal(t, len([]rune(body)), resp.ContentLength)
}

func TestHTTPX_Response_Headers(t *testing.T) {
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("X-Custom-Header", "customval")
		w.WriteHeader(http.StatusOK)
	}))
	defer srv.Close()

	h, err := NewHttpx(defaultOpts())
	require.NoError(t, err)

	resp, err := h.Get(srv.URL, nil)
	require.NoError(t, err)
	assert.Equal(t, "customval", resp.GetHeader("X-Custom-Header"))
}

func TestHTTPX_Response_Title_Empty(t *testing.T) {
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Write([]byte(`plain text, no html`))
	}))
	defer srv.Close()

	h, err := NewHttpx(defaultOpts())
	require.NoError(t, err)

	resp, err := h.Get(srv.URL, nil)
	require.NoError(t, err)
	assert.Empty(t, resp.Title)
}

// ---------------------------------------------------------------------------
// Options
// ---------------------------------------------------------------------------

func TestHTTPOptions_Defaults(t *testing.T) {
	opts := &HTTPOptions{
		Timeout:         30 * time.Second,
		RetryMax:        3,
		FollowRedirects: true,
	}
	h, err := NewHttpx(opts)
	require.NoError(t, err)
	assert.Equal(t, 30*time.Second, h.Options.Timeout)
	assert.Equal(t, 3, h.Options.RetryMax)
	assert.True(t, h.Options.FollowRedirects)
}
