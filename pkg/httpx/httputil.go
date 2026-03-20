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

// Package httpx http相关
package httpx

import (
	"bufio"
	"bytes"
	"fmt"
	"io"
	"io/ioutil"
	"net/http"
	"net/http/httputil"
	"net/url"
	"strings"

	"github.com/projectdiscovery/rawhttp/client"

	"github.com/projectdiscovery/retryablehttp-go"
)

const (
	headerParts  = 2
	requestParts = 3
)
const (
	// HTTP defines the plain http scheme
	HTTP = "http"
	// HTTPS defines the secure http scheme
	HTTPS = "https"
	// HTTPorHTTPS defines the both http and https scheme
	HTTPorHTTPS = "http|https"
)

// DumpRequest to string
func DumpRequest(req *retryablehttp.Request) (string, error) {
	dump, err := httputil.DumpRequestOut(req.Request, true)

	return string(dump), err
}

// DumpResponse to string
func DumpResponse(resp *http.Response) (string, error) {
	// httputil.DumpResponse does not work with websockets
	if resp.StatusCode == http.StatusContinue {
		raw := resp.Status + "\n"
		for h, v := range resp.Header {
			raw += fmt.Sprintf("%s: %s\n", h, v)
		}
		return raw, nil
	}

	raw, err := httputil.DumpResponse(resp, true)
	return string(raw), err
}

// DumpRequestRaw 导出请求包原文
func DumpRequestRaw(req *retryablehttp.Request) string {
	b := strings.Builder{}

	b.WriteString(fmt.Sprintf("%s %s"+client.NewLine, req.Method, req.URL))

	for k, v := range req.Header {
		value := strings.Join(v, " ")
		if value != "" {
			b.WriteString(fmt.Sprintf("%s:%s"+client.NewLine, k, value))
		} else {
			b.WriteString(fmt.Sprintf("%s"+client.NewLine, k))
		}
	}

	b.WriteString(client.NewLine)
	body, err := req.BodyBytes()
	if err != nil {
		body = nil
	}
	if body != nil {
		var buf bytes.Buffer
		tee := io.TeeReader(req.Body, &buf)
		body, err := ioutil.ReadAll(tee)
		if err != nil {
			return b.String()
		}
		b.Write(body)

	}
	return b.String()
}

// ParseRequest from raw string
func ParseRequest(req string, unsafe bool) (method, path string, headers map[string]string, body string, err error) {
	headers = make(map[string]string)
	reader := bufio.NewReader(strings.NewReader(req))
	s, err := reader.ReadString('\n')
	if err != nil {
		err = fmt.Errorf("could not read request: %s", err)
		return
	}
	parts := strings.Split(s, " ")
	if len(parts) < requestParts {
		err = fmt.Errorf("malformed request supplied")
		return
	}
	method = parts[0]

	for {
		line, readErr := reader.ReadString('\n')
		line = strings.TrimSpace(line)

		if readErr != nil || line == "" {
			break
		}

		// Unsafe skips all checks
		p := strings.SplitN(line, ":", headerParts)
		key := p[0]
		value := ""
		if len(p) == headerParts {
			value = p[1]
		}

		if !unsafe {
			if len(p) != headerParts {
				continue
			}

			if strings.EqualFold(key, "content-length") {
				continue
			}

			key = strings.TrimSpace(key)
			value = strings.TrimSpace(value)
		}

		headers[key] = value
	}

	// Handle case with the full http url in path. In that case,
	// ignore any host header that we encounter and use the path as request URL
	if strings.HasPrefix(parts[1], "http") {
		var parsed *url.URL
		parsed, err = url.Parse(parts[1])
		if err != nil {
			err = fmt.Errorf("could not parse request URL: %s", err)
			return
		}
		path = parts[1]
		headers["Host"] = parsed.Host
	} else {
		path = parts[1]
	}

	// Set the request body
	b, err := ioutil.ReadAll(reader)
	if err != nil {
		err = fmt.Errorf("could not read request body: %s", err)
		return
	}
	body = string(b)

	return method, path, headers, body, nil
}
