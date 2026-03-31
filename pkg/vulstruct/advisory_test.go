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

package vulstruct

import (
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

// ---------------------------------------------------------------------------
// Original regression tests (kept)
// ---------------------------------------------------------------------------

func TestAdvisoryEngine(t *testing.T) {
	dir := "data/vuln"
	ad := NewAdvisoryEngine()
	err := ad.LoadFromDirectory(dir)
	assert.NoError(t, err)
	results, err := ad.GetAdvisories("mlflow", "2.13", true)
	assert.NoError(t, err)
	for _, result := range results {
		t.Log(result)
	}
}

func TestNewRemoteAdvisoryEngine(t *testing.T) {
	t.Skip("skipping remote advisory test: requires network access to a running AIG server")
}

// ---------------------------------------------------------------------------
// ReadVersionVul – unit tests against inline YAML
// ---------------------------------------------------------------------------

func TestReadVersionVul_ValidRule(t *testing.T) {
	yaml := []byte(`
info:
  name: testpkg
  cve: CVE-2024-0001
  summary: Test vulnerability
  details: |
    A test vulnerability.
  cvss: CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:N/A:N
  severity: HIGH
rule: version < "2.0.0"
references:
  - https://example.com
`)
	vv, err := ReadVersionVul(yaml)
	require.NoError(t, err)
	assert.Equal(t, "testpkg", vv.Info.FingerPrintName)
	assert.Equal(t, "CVE-2024-0001", vv.Info.CVEName)
	assert.Equal(t, `version < "2.0.0"`, vv.Rule)
	assert.NotNil(t, vv.RuleCompile)
}

func TestReadVersionVul_EmptyRule(t *testing.T) {
	yaml := []byte(`
info:
  name: testpkg2
  cve: CVE-2024-0002
  summary: s
  details: d
  cvss: ""
  severity: LOW
rule: ""
references: []
`)
	vv, err := ReadVersionVul(yaml)
	require.NoError(t, err)
	assert.Equal(t, "", vv.Rule)
	assert.Nil(t, vv.RuleCompile)
}

func TestReadVersionVul_MissingRule_Error(t *testing.T) {
	// No 'rule' field at all – should error
	yaml := []byte(`
info:
  name: testpkg3
  cve: CVE-2024-0003
  summary: s
  severity: LOW
references: []
`)
	_, err := ReadVersionVul(yaml)
	assert.Error(t, err)
}

func TestReadVersionVul_BadRule_Error(t *testing.T) {
	// Syntactically invalid rule expression
	yaml := []byte(`
info:
  name: testpkg4
  cve: CVE-2024-0004
  summary: s
  severity: LOW
rule: "version <<< bad <<<<<"
references: []
`)
	_, err := ReadVersionVul(yaml)
	assert.Error(t, err)
}

// ---------------------------------------------------------------------------
// AdvisoryEngine – new / count / getAll
// ---------------------------------------------------------------------------

func TestAdvisoryEngine_New(t *testing.T) {
	ae := NewAdvisoryEngine()
	assert.NotNil(t, ae)
	assert.Equal(t, 0, ae.GetCount())
	assert.Empty(t, ae.GetAll())
}

// ---------------------------------------------------------------------------
// LoadFromDirectory (using the real data files)
// ---------------------------------------------------------------------------

func TestAdvisoryEngine_LoadFromDirectory_Real(t *testing.T) {
	ae := NewAdvisoryEngine()
	err := ae.LoadFromDirectory("../../data/vuln")
	require.NoError(t, err)
	assert.Greater(t, ae.GetCount(), 0, "should have loaded at least one vuln")
}

func TestAdvisoryEngine_LoadFromDirectory_SingleFile(t *testing.T) {
	ae := NewAdvisoryEngine()
	// Load one specific well-known file
	err := ae.LoadFromDirectory("../../data/vuln/mlflow/CVE-2023-6977.yaml")
	require.NoError(t, err)
	assert.Equal(t, 1, ae.GetCount())
}

func TestAdvisoryEngine_LoadFromDirectory_NonExistent(t *testing.T) {
	ae := NewAdvisoryEngine()
	err := ae.LoadFromDirectory("/does/not/exist")
	// LoadFromDirectory treats a non-existent path as a single file attempt,
	// which silently skips unreadable entries and returns nil with 0 entries.
	// This documents the current behaviour; the engine loads nothing.
	assert.NoError(t, err)
	assert.Equal(t, 0, ae.GetCount())
}

// ---------------------------------------------------------------------------
// GetAdvisories – table-driven boundary tests
// ---------------------------------------------------------------------------

// We build a small in-memory engine from known YAML data for precise control.
func newEngineFromYAMLs(t *testing.T, yamls ...[]byte) *AdvisoryEngine {
	t.Helper()
	ae := NewAdvisoryEngine()
	for _, y := range yamls {
		vv, err := ReadVersionVul(y)
		require.NoError(t, err)
		ae.ads = append(ae.ads, *vv)
	}
	return ae
}

// mlflowCVE-2023-6977: rule = version < "2.9.2"
var mlflowVulnYAML = []byte(`
info:
  name: mlflow
  cve: CVE-2023-6977
  summary: MLflow local file disclosure
  severity: HIGH
rule: version < "2.9.2"
references: []
`)

// mlflowCVE-2024-1483: rule = version <= "2.9.2"
var mlflowVuln2YAML = []byte(`
info:
  name: mlflow
  cve: CVE-2024-1483
  summary: MLflow path traversal
  severity: HIGH
rule: version <= "2.9.2"
references: []
`)

func TestGetAdvisories_BoundaryVersionLessThan(t *testing.T) {
	ae := newEngineFromYAMLs(t, mlflowVulnYAML)

	cases := []struct {
		version  string
		wantHit  bool
		desc     string
	}{
		{"1.0.0", true, "well below boundary"},
		{"2.9.1", true, "one patch below boundary"},
		{"2.9.2", false, "exact boundary (< not <=)"},
		{"2.9.3", false, "one above boundary"},
		{"3.0.0", false, "well above boundary"},
		{"2.9.2-rc1", true, "pre-release of boundary version"},
	}

	for _, tc := range cases {
		t.Run(tc.desc, func(t *testing.T) {
			results, err := ae.GetAdvisories("mlflow", tc.version, true)
			require.NoError(t, err)
			if tc.wantHit {
				assert.NotEmpty(t, results, "expected vuln match for version %s", tc.version)
			} else {
				assert.Empty(t, results, "expected no vuln match for version %s", tc.version)
			}
		})
	}
}

func TestGetAdvisories_BoundaryVersionLessThanOrEqual(t *testing.T) {
	ae := newEngineFromYAMLs(t, mlflowVuln2YAML)

	cases := []struct {
		version string
		wantHit bool
		desc    string
	}{
		{"1.0.0", true, "well below boundary"},
		{"2.9.2", true, "exact boundary (<= includes it)"},
		{"2.9.3", false, "one above boundary"},
	}

	for _, tc := range cases {
		t.Run(tc.desc, func(t *testing.T) {
			results, err := ae.GetAdvisories("mlflow", tc.version, true)
			require.NoError(t, err)
			if tc.wantHit {
				assert.NotEmpty(t, results)
			} else {
				assert.Empty(t, results)
			}
		})
	}
}

func TestGetAdvisories_WrongPackageName(t *testing.T) {
	ae := newEngineFromYAMLs(t, mlflowVulnYAML)

	results, err := ae.GetAdvisories("notexist", "1.0.0", true)
	require.NoError(t, err)
	assert.Empty(t, results)
}

func TestGetAdvisories_EmptyVersion_ReturnsAll(t *testing.T) {
	ae := newEngineFromYAMLs(t, mlflowVulnYAML, mlflowVuln2YAML)

	// Empty version → skip rule evaluation, return all matching by name
	results, err := ae.GetAdvisories("mlflow", "", true)
	require.NoError(t, err)
	assert.Len(t, results, 2, "both entries should be returned when version is empty")
}

func TestGetAdvisories_MultipleVulnsForSamePackage(t *testing.T) {
	ae := newEngineFromYAMLs(t, mlflowVulnYAML, mlflowVuln2YAML)

	// Version 2.9.1: hits both (< 2.9.2 AND <= 2.9.2)
	results, err := ae.GetAdvisories("mlflow", "2.9.1", true)
	require.NoError(t, err)
	assert.Len(t, results, 2)

	// Version 2.9.2: only hits <= 2.9.2 (not < 2.9.2)
	results, err = ae.GetAdvisories("mlflow", "2.9.2", true)
	require.NoError(t, err)
	assert.Len(t, results, 1)
	assert.Equal(t, "CVE-2024-1483", results[0].Info.CVEName)
}

// ---------------------------------------------------------------------------
// GetAdvisories with real vuln directory – regression checks
// ---------------------------------------------------------------------------

func TestAdvisoryEngine_RealVulns_MLflow(t *testing.T) {
	ae := NewAdvisoryEngine()
	require.NoError(t, ae.LoadFromDirectory("../../data/vuln/mlflow"))

	// mlflow 2.8.0 should be vulnerable (multiple CVEs)
	results, err := ae.GetAdvisories("mlflow", "2.8.0", true)
	require.NoError(t, err)
	assert.NotEmpty(t, results, "mlflow 2.8.0 should match some vulnerabilities")

	// mlflow 2.13 was the version in the original test – record count
	results, err = ae.GetAdvisories("mlflow", "2.13", true)
	require.NoError(t, err)
	t.Logf("mlflow 2.13 matches %d advisories", len(results))
}

func TestAdvisoryEngine_GetAll_And_GetCount_Consistent(t *testing.T) {
	ae := NewAdvisoryEngine()
	require.NoError(t, ae.LoadFromDirectory("../../data/vuln/mlflow"))

	count := ae.GetCount()
	all := ae.GetAll()
	assert.Equal(t, count, len(all))
	assert.Greater(t, count, 0)
}

// ---------------------------------------------------------------------------
// isInternal flag behaviour
// ---------------------------------------------------------------------------

var internalOnlyVulnYAML = []byte(`
info:
  name: testpkg_int
  cve: CVE-2024-INT-1
  summary: Internal-only vuln
  severity: MEDIUM
rule: is_internal=="true" && version < "5.0.0"
references: []
`)

func TestGetAdvisories_IsInternal_Flag(t *testing.T) {
	ae := newEngineFromYAMLs(t, internalOnlyVulnYAML)

	// Internal scan: should match
	results, err := ae.GetAdvisories("testpkg_int", "4.0.0", true)
	require.NoError(t, err)
	assert.NotEmpty(t, results, "internal scan should match isInternal==true rule")

	// External scan: should not match
	results, err = ae.GetAdvisories("testpkg_int", "4.0.0", false)
	require.NoError(t, err)
	assert.Empty(t, results, "external scan should NOT match isInternal==true rule")
}
