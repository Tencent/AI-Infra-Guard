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

package websocket

import (
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/gin-gonic/gin"
	"github.com/stretchr/testify/require"
)

func TestStaticFallbackReturnsNotFoundForUnknownAPI(t *testing.T) {
	gin.SetMode(gin.TestMode)
	router := gin.New()
	router.NoRoute(serveStaticFallback)

	for _, path := range []string{
		"/api/v1/api-checker/configured-check/stream",
		"/api-checker",
		"/api-checker/",
		"/api-checker/ui",
		"/api-checker/static/app.js",
	} {
		t.Run(path, func(t *testing.T) {
			request := httptest.NewRequest(http.MethodGet, path, nil)
			response := httptest.NewRecorder()
			router.ServeHTTP(response, request)

			require.Equal(t, http.StatusNotFound, response.Code)
			require.JSONEq(
				t,
				`{"detail":"API endpoint not found"}`,
				response.Body.String(),
			)
		})
	}
}
