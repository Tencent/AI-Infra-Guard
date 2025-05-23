package utils

import (
	"github.com/stretchr/testify/assert"
	"testing"
)

func TestListDir(t *testing.T) {
	sb, err := ListDir("/Users/python/workspace/AI-Infra-Guard", 1)
	assert.NoError(t, err)
	t.Log(sb)
}
