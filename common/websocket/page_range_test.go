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
	"math"
	"testing"
)

// TestPageRangeNoPanic: page/size come from the query string, so
// (page-1)*size can overflow to a negative start and panic list[start:end].
// pageRange must always return a valid [0,total] window.
func TestPageRangeNoPanic(t *testing.T) {
	cases := []struct{ page, size, total int }{
		{1, 10, 5},
		{2, 10, 25},
		{math.MaxInt, 20, 10},
		{math.MaxInt, math.MaxInt, 10},
		{-5, 10, 10},
		{1, -3, 10},
		{0, 10, 10},
	}
	for _, tc := range cases {
		start, end := pageRange(tc.page, tc.size, tc.total)
		if start < 0 || end < 0 || start > end || end > tc.total {
			t.Fatalf("unsafe range for %+v: [%d,%d]", tc, start, end)
		}
	}
}

func TestPageRangeWindows(t *testing.T) {
	if s, e := pageRange(2, 10, 25); s != 10 || e != 20 {
		t.Fatalf("page 2 size 10 total 25 => [%d,%d], want [10,20]", s, e)
	}
	if s, e := pageRange(1, 10, 5); s != 0 || e != 5 {
		t.Fatalf("first page clamps end to total: [%d,%d], want [0,5]", s, e)
	}
	if s, e := pageRange(1, 10, 0); s != 0 || e != 0 {
		t.Fatalf("empty dataset: [%d,%d], want [0,0]", s, e)
	}
}
