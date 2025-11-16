package preload

import (
	"net/http"
	"net/http/httptest"
	"testing"
	"time"

	"github.com/Tencent/AI-Infra-Guard/common/fingerprints/parser"
	"github.com/Tencent/AI-Infra-Guard/pkg/httpx"
	"github.com/stretchr/testify/assert"
)

func newHTTPXForTest(t *testing.T) *httpx.HTTPX {
	t.Helper()
	httpOptions := &httpx.HTTPOptions{
		Timeout:          5 * time.Second,
		RetryMax:         1,
		FollowRedirects:  false,
		HTTPProxy:        "",
		Unsafe:           false,
		DefaultUserAgent: httpx.GetRandomUserAgent(),
		Dialer:           nil,
	}
	hp, err := httpx.NewHttpx(httpOptions)
	assert.NoError(t, err)
	return hp
}

func TestEvalFpVersionExact(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path == "/exact" {
			w.Header().Set("X-Version", "1.2.3")
			_, _ = w.Write([]byte("ok"))
			return
		}
		http.NotFound(w, r)
	}))
	defer server.Close()

	data := `info:
  name: test
  author: test
  severity: info
  metadata:
    product: test
    vendor: test
version:
  - method: GET
    path: '/exact'
    extractor:
      part: header
      group: '1'
      regex: 'X-Version:\s*([0-9.]+)'
`
	fp, err := parser.InitFingerPrintFromData([]byte(data))
	assert.NoError(t, err)

	hp := newHTTPXForTest(t)
	version, err := EvalFpVersion(server.URL, hp, *fp)
	assert.NoError(t, err)
	assert.Equal(t, "1.2.3", version)
}

func TestEvalFpVersionFuzzyIntersection(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		switch r.URL.Path {
		case "/fuzzy1":
			_, _ = w.Write([]byte("range-one"))
		case "/fuzzy2":
			_, _ = w.Write([]byte("range-two"))
		default:
			http.NotFound(w, r)
		}
	}))
	defer server.Close()

	data := `info:
  name: test
  author: test
  severity: info
  metadata:
    product: test
    vendor: test
version:
  - method: GET
    path: '/fuzzy1'
    matchers:
      - body="range-one"
    versionrange: '>=1.0.0,<2.0.0'
  - method: GET
    path: '/fuzzy2'
    matchers:
      - body="range-two"
    versionrange: '>=1.5.0,<3.0.0'
`
	fp, err := parser.InitFingerPrintFromData([]byte(data))
	assert.NoError(t, err)

	hp := newHTTPXForTest(t)
	version, err := EvalFpVersion(server.URL, hp, *fp)
	assert.NoError(t, err)
	assert.Equal(t, ">=1.5.0,<2.0.0", version)
}

func TestEvalFpVersionFuzzyHashIntersection(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		switch r.URL.Path {
		case "/fuzzy1":
			_, _ = w.Write([]byte("range-one"))
		case "/fuzzy2":
			_, _ = w.Write([]byte("range-two"))
		default:
			http.NotFound(w, r)
		}
	}))
	defer server.Close()

	data := `info:
    name: test
    author: test
    severity: info
    metadata:
      product: test
      vendor: test
  version:
    - method: GET
      path: '/fuzzy1'
      matchers:
        - hash=="012c14d354f49d6e682efaa1e8d3f1433ff7da7093b2b5964aac1302303f52b4"
      versionrange: '>=1.0.0,<2.0.0'
    - method: GET
      path: '/fuzzy2'
      matchers:
        - hash=="1773f6ec9285e9d638a94a19375353fa9c8c891c732d80a996724ed8017fe196"
      versionrange: '>=1.5.0,<3.0.0'
`
	fp, err := parser.InitFingerPrintFromData([]byte(data))
	assert.NoError(t, err)

	hp := newHTTPXForTest(t)
	version, err := EvalFpVersion(server.URL, hp, *fp)
	assert.NoError(t, err)
	assert.Equal(t, ">=1.5.0,<2.0.0", version)
}

func TestEvalFpVersionFuzzyNoMatch(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		_, _ = w.Write([]byte("no-match"))
	}))
	defer server.Close()

	data := `info:
  name: test
  author: test
  severity: info
  metadata:
    product: test
    vendor: test
version:
  - method: GET
    path: '/fuzzy'
    matchers:
      - body="another"
    versionrange: '>=1.0.0,<2.0.0'
`
	fp, err := parser.InitFingerPrintFromData([]byte(data))
	assert.NoError(t, err)

	hp := newHTTPXForTest(t)
	version, err := EvalFpVersion(server.URL, hp, *fp)
	assert.NoError(t, err)
	assert.Equal(t, "", version)
}
