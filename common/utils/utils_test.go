package utils

import (
	"github.com/Tencent/AI-Infra-Guard/pkg/httpx"
	"github.com/hashicorp/go-version"
	"github.com/projectdiscovery/fastdialer/fastdialer"
	"github.com/stretchr/testify/assert"
	"testing"
	"time"
)

func TestIsFileExists(t *testing.T) {
	assert.True(t, IsFileExists("/etc/passwd"))
	assert.True(t, IsFileExists("/etc/"))
	assert.False(t, IsDir("/etc/passwd"))
	assert.True(t, IsDir("/etc/"))
}

func TestCompareVersions(t *testing.T) {
	version1 := "1.0.0"
	version2 := "1.2"
	v := CompareVersions(version1, version2)
	t.Log(v)
}

func TestCompareVersions2(t *testing.T) {
	version1 := "2.13"
	version2 := "2.13.1"
	v1 := version.Must(version.NewVersion(version1))
	v2 := version.Must(version.NewVersion(version2))
	assert.True(t, v1.LessThan(v2))
}

func TestFaviconHash(t *testing.T) {
	url := "http://127.0.0.1:8265/favicon.ico"
	dialer, err := fastdialer.NewDialer(fastdialer.DefaultOptions)
	assert.NoError(t, err)
	httpOptions := &httpx.HTTPOptions{
		Timeout:          time.Duration(30) * time.Second,
		RetryMax:         3,
		FollowRedirects:  false,
		Unsafe:           false,
		DefaultUserAgent: httpx.GetRandomUserAgent(),
		Dialer:           dialer,
	}
	hp, err := httpx.NewHttpx(httpOptions)
	assert.NoError(t, err)
	resp, err := hp.Get(url, nil)
	assert.NoError(t, err)
	hash := FaviconHash(resp.Data)
	t.Log(hash)
}

func TestBodyHash(t *testing.T) {
	h := BodyHash([]byte("hello"))
	assert.Equal(t, "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824", h)
}

func TestGetLocalOpenPorts(t *testing.T) {
	op, err := GetLocalOpenPorts()
	assert.NoError(t, err)
	for _, item := range op {
		t.Log(item.Address, item.Port)
	}
}
