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

// Package httpx http response
package httpx

import (
	"fmt"
	"net/http"
	"strings"

	"github.com/projectdiscovery/rawhttp/client"
)

// Response contains the response to a server
type Response struct {
	*http.Response
	StatusCode    int
	Headers       map[string][]string
	Data          []byte
	DataStr       string
	ContentLength int
	Title         string
}

// GetHeaderRaw 获得header文本
func (r *Response) GetHeaderRaw() string {
	HeaderStr := ""
	for h, v := range r.Headers {
		HeaderStr += fmt.Sprintf("%s: %s\n", h, strings.Join(v, " "))
	}
	return HeaderStr
}

// GetHeader value
func (r *Response) GetHeader(name string) string {
	v, ok := r.Headers[name]
	if ok {
		return strings.Join(v, " ")
	}
	return ""
}

// GetHeaderPart with offset
func (r *Response) GetHeaderPart(name, sep string) string {
	v, ok := r.Headers[name]
	if ok && len(v) > 0 {
		tokens := strings.Split(strings.Join(v, " "), sep)
		return tokens[0]
	}
	return ""
}

// DumpResponse 导出返回包
func (r *Response) DumpResponse() string {
	firstLine := r.Response.Proto + " " + r.Response.Status
	return firstLine + client.NewLine + r.GetHeaderRaw() + client.NewLine + r.DataStr
}
