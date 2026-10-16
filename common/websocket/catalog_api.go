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

	"github.com/Tencent/AI-Infra-Guard/common/catalog"
	"github.com/Tencent/AI-Infra-Guard/common/redteam"
	"github.com/Tencent/AI-Infra-Guard/common/scenario"
	"github.com/gin-gonic/gin"
)

// HandleGetScanCatalog returns plugins, presets, and scenarios for the scan wizard.
func HandleGetScanCatalog(c *gin.Context) {
	cat, err := catalog.Load(catalog.ResolveRoot())
	if err != nil {
		c.JSON(http.StatusOK, gin.H{
			"status":  1,
			"message": err.Error(),
			"data":    nil,
		})
		return
	}
	scenes, err := scenario.Load(scenario.ResolveRoot())
	if err != nil {
		c.JSON(http.StatusOK, gin.H{
			"status":  1,
			"message": err.Error(),
			"data":    nil,
		})
		return
	}
	checks, strategies, err := redteam.Load(redteam.ResolveRoot())
	if err != nil {
		c.JSON(http.StatusOK, gin.H{
			"status":  1,
			"message": err.Error(),
			"data":    nil,
		})
		return
	}
	c.JSON(http.StatusOK, gin.H{
		"status":  0,
		"message": "ok",
		"data": gin.H{
			"plugins":    cat.Plugins,
			"presets":    cat.Presets,
			"scenarios":  scenes,
			"checks":     checks,
			"strategies": strategies,
		},
	})
}
