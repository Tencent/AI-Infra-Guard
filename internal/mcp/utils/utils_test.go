package utils

import (
	"github.com/stretchr/testify/assert"
	"testing"
)

func TestListDir(t *testing.T) {
	sb, err := ListDir("/mcp-server", -1, "")
	assert.NoError(t, err)
	t.Log(sb)
}

func TestGrepFile(t *testing.T) {
	sb, err := Grep("/mcp-server/src/mcp_server/server.py", "@mcp\\.tool.*\n.*def", 3)
	assert.NoError(t, err)
	t.Log(sb)
}

func TestGrepDirectory(t *testing.T) {
	sb, err := Grep("/mcp-server", "AppConfig", 3)
	assert.NoError(t, err)
	t.Log(sb)
	p := "SSE|streamable-http|EventSource"
	sb, err = Grep("/mcp-server", p, 3)
	assert.NoError(t, err)
	t.Log(sb)
}

func TestReadBigFile(t *testing.T) {
	sb, err := ReadFileChunk("/mcp-server/src/mcp_server/server.py", 0, 0, 10*1024)
	assert.NoError(t, err)
	t.Log(sb)

	sb, err = ReadFileChunk("/mcp-server/src/mcp_server/server.py", 0, 2, 10*1024)
	assert.NoError(t, err)
	t.Log(sb)
}

func TestReadSmallFile(t *testing.T) {
	sb, err := ReadFileChunk("/mcp-server/src/mcp_server/app_config.py", 0, 0, 10*1024)
	assert.NoError(t, err)
	t.Log(sb)
}
