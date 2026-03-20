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

package preload

import (
	"testing"

	"github.com/stretchr/testify/assert"
)

func TestParseVersionRangeComparators(t *testing.T) {
	vr, err := parseVersionRange(">=1.0.0,<2.0.0")
	assert.NoError(t, err)
	assert.Equal(t, ">=1.0.0,<2.0.0", vr.String())
}

func TestParseVersionRangeBracketNotation(t *testing.T) {
	vr, err := parseVersionRange("[1.2.0,2.3.0)")
	assert.NoError(t, err)
	assert.Equal(t, ">=1.2.0,<2.3.0", vr.String())
}

func TestParseVersionRangeEquality(t *testing.T) {
	vr, err := parseVersionRange("1.5.1")
	assert.NoError(t, err)
	assert.Equal(t, "=1.5.1", vr.String())
}

func TestIntersectVersionRanges(t *testing.T) {
	r1, err := parseVersionRange(">=1.0.0,<2.0.0")
	assert.NoError(t, err)
	r2, err := parseVersionRange(">=1.5.0,<3.0.0")
	assert.NoError(t, err)

	result, ok := intersectVersionRanges([]versionRange{r1, r2})
	assert.True(t, ok)
	assert.Equal(t, ">=1.5.0,<2.0.0", result.String())
}

func TestIntersectVersionRangesEquality(t *testing.T) {
	r1, err := parseVersionRange(">=1.0.0")
	assert.NoError(t, err)
	r2, err := parseVersionRange("=1.5.0")
	assert.NoError(t, err)

	result, ok := intersectVersionRanges([]versionRange{r1, r2})
	assert.True(t, ok)
	assert.Equal(t, "=1.5.0", result.String())
}

func TestIntersectVersionRangesEmpty(t *testing.T) {
	r1, err := parseVersionRange(">=2.0.0")
	assert.NoError(t, err)
	r2, err := parseVersionRange("<1.0.0")
	assert.NoError(t, err)

	_, ok := intersectVersionRanges([]versionRange{r1, r2})
	assert.False(t, ok)
}
