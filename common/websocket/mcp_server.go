package websocket

import (
	"github.com/Tencent/AI-Infra-Guard/internal/mcp"
	"github.com/gin-gonic/gin"
)

func GetMcpPluginList(c *gin.Context) {
	scanner := mcp.NewScanner(nil, nil)
	names, err := scanner.GetAllPluginNames()
	if err != nil {
		c.JSON(500, gin.H{
			"code": 1,
			"msg":  err.Error(),
			"data": nil,
		})
		return
	}
	c.JSON(200, gin.H{
		"code": 0,
		"msg":  "",
		"data": names,
	})
}
