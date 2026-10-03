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

import "testing"

func TestMaskValuesKeepsKeysAndHidesValues(t *testing.T) {
	masked := maskValues(map[string]string{
		"Authorization": "Bearer super-secret",
		"X-Title":       "AI-Infra-Guard",
	})

	if len(masked) != 2 {
		t.Fatalf("masked has %d keys, want 2: %v", len(masked), masked)
	}
	for _, key := range []string{"Authorization", "X-Title"} {
		if masked[key] != maskedToken {
			t.Errorf("%s = %v, want it masked", key, masked[key])
		}
	}
}

func TestMaskValuesHandlesNilAndAnyValues(t *testing.T) {
	if maskValues[string](nil) != nil {
		t.Error("a nil map must stay nil, so JSON keeps omitting it")
	}

	masked := maskValues(map[string]any{"provider.order": []string{"anthropic"}})
	if masked["provider.order"] != maskedToken {
		t.Errorf("provider.order = %v, want it masked", masked["provider.order"])
	}
}
