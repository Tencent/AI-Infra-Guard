package preload

import (
	"github.com/Tencent/AI-Infra-Guard/common/fingerprints/parser"
	"github.com/Tencent/AI-Infra-Guard/pkg/httpx"
	"github.com/projectdiscovery/fastdialer/fastdialer"
	"github.com/stretchr/testify/assert"
	"os"
	"testing"
	"time"
)

func TestFingerPrint(t *testing.T) {
	dialer, err := fastdialer.NewDialer(fastdialer.DefaultOptions)
	assert.NoError(t, err)
	httpOptions := &httpx.HTTPOptions{
		Timeout:          time.Duration(30) * time.Second,
		RetryMax:         3,
		FollowRedirects:  false,
		HTTPProxy:        "",
		Unsafe:           false,
		DefaultUserAgent: httpx.GetRandomUserAgent(),
		Dialer:           dialer,
	}
	hp, err := httpx.NewHttpx(httpOptions)
	assert.NoError(t, err)
	// mlflow
	m := Mlflow{}
	t.Log(m.Match(hp, "http://127.0.0.1:5000/"))
	t.Log(m.GetVersion(hp, "http://127.0.0.1:5000/"))
}

func TestRunner_RunFpReqs(t *testing.T) {
	dialer, err := fastdialer.NewDialer(fastdialer.DefaultOptions)
	assert.NoError(t, err)
	httpOptions := &httpx.HTTPOptions{
		Timeout:          time.Duration(3) * time.Second,
		RetryMax:         1,
		FollowRedirects:  false,
		HTTPProxy:        "",
		Unsafe:           false,
		DefaultUserAgent: httpx.GetRandomUserAgent(),
		Dialer:           dialer,
	}
	hp, err := httpx.NewHttpx(httpOptions)
	assert.NoError(t, err)

	data, err := os.ReadFile("data/fingerprints/anythingllm.yaml")
	assert.NoError(t, err)
	fp, err := parser.InitFingerPrintFromData(data)
	assert.NoError(t, err)
	instance := New(hp, []parser.FingerPrint{*fp})
	fps := instance.RunFpReqs("http://localhost:8888/", 10, 0)
	for _, fp := range fps {
		t.Logf("%+v", fp)
	}
}
