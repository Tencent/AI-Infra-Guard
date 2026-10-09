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

package runner

import (
	"encoding/json"
	"testing"

	"github.com/Tencent/AI-Infra-Guard/common/fingerprints/preload"
	"github.com/Tencent/AI-Infra-Guard/pkg/vulstruct"
	"github.com/stretchr/testify/require"
)

func TestResultsJSONUsesExistingScanResultSchema(t *testing.T) {
	results := []HttpResult{{
		URL:           "http://example.test",
		Title:         "Example",
		ContentLength: 12,
		StatusCode:    200,
		ResponseTime:  "1ms",
		Fingers: []preload.FpResult{{
			Name:    "demo",
			Version: "1.2.3",
			Type:    "app",
		}},
		Advisories: []vulstruct.VersionVul{{
			Info: vulstruct.Info{
				FingerPrintName: "demo",
				CVEName:         "CVE-2024-0001",
				Summary:         "example advisory",
				Severity:        "HIGH",
			},
			Rule: "version < 2.0.0",
		}},
		Resp: "response body stays in the current schema",
		s:    "human readable line is not part of the schema",
	}}

	payload := ResultsJSON(results)
	require.JSONEq(t, `[
		{
			"url": "http://example.test",
			"title": "Example",
			"content-length": 12,
			"status-code": 200,
			"response-time": "1ms",
			"fingerprints": [{"name": "demo", "version": "1.2.3", "type": "app"}],
			"advisories": [{
				"info": {
					"name": "demo",
					"cve": "CVE-2024-0001",
					"summary": "example advisory",
					"details": "",
					"cvss": "",
					"severity": "HIGH",
					"security_advise": "",
					"references": null
				},
				"rule": "version < 2.0.0",
				"references": null
			}],
			"Resp": "response body stays in the current schema"
		}
	]`, payload)

	var decoded []HttpResult
	require.NoError(t, json.Unmarshal([]byte(payload), &decoded))
	require.Equal(t, results[0].URL, decoded[0].URL)
	require.Equal(t, results[0].Advisories[0].Info.CVEName, decoded[0].Advisories[0].Info.CVEName)
	require.Equal(t, results[0].Resp, decoded[0].Resp)
	require.NotContains(t, payload, "human readable")
	require.Equal(t, payload, "["+results[0].JSON()+"]")
	require.Equal(t, "[]", ResultsJSON(nil))
}
