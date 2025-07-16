package vulstruct

import (
	"github.com/stretchr/testify/assert"
	"testing"
)

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
	ad := NewAdvisoryEngine()
	assert.NotNil(t, ad)
	hostname := "xx"
	err := ad.LoadFromHost(hostname)
	assert.NoError(t, err)
	results, err := ad.GetAdvisories("mlflow", "2.13", true)
	assert.NoError(t, err)
	for _, result := range results {
		t.Log(result)
	}
}
