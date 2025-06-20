package websocket

import (
	"encoding/json"
	"fmt"
	"net/http"
	"path/filepath"
	"strings"
	"time"

	"github.com/gin-gonic/gin"
)

// 预留任务相关接口实现

// SSE接口（心跳推送）
func HandleTaskSSE(c *gin.Context, tm *TaskManager) {
	c.Writer.Header().Set("Content-Type", "text/event-stream")
	c.Writer.Header().Set("Cache-Control", "no-cache")
	c.Writer.Header().Set("Connection", "keep-alive")
	c.Writer.Flush()

	sessionId := c.Query("sessionId")
	ticker := time.NewTicker(time.Second)
	defer ticker.Stop()

	for {
		select {
		case <-c.Request.Context().Done():
			return
		case t := <-ticker.C:
			msg := TaskEventMessage{
				ID:        fmt.Sprintf("%d", t.UnixNano()),
				Type:      "event",
				SessionID: sessionId,
				Timestamp: t.UnixMilli(),
				Event: LiveStatusEvent{
					ID:        fmt.Sprintf("%d", t.UnixNano()),
					Type:      "liveStatus",
					Timestamp: t.UnixMilli(),
					Text:      "存活中",
				},
			}
			// SSE格式：data: <json>\n\n
			jsonStr, _ := json.Marshal(msg)
			c.Writer.Write([]byte("data: "))
			c.Writer.Write(jsonStr)
			c.Writer.Write([]byte("\n\n"))
			c.Writer.Flush()
		}
	}
}

// 新建任务接口
func HandleTaskCreate(c *gin.Context, tm *TaskManager) {
	var req TaskCreateRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusOK, gin.H{
			"status":  1,
			"message": "参数错误",
			"data":    nil,
		})
		return
	}
	tm.AddTask(&req)
	// c.JSON(http.StatusOK, gin.H{
	// 	"status":  0,
	// 	"message": "任务创建成功",
	// 	"data": gin.H{
	// 		"sessionId": req.SessionID,
	// 	},
	// })
}

// 终止任务接口
func HandleTerminateTask(c *gin.Context, tm *TaskManager) {
	sessionId := c.Param("sessionId")
	if sessionId == "" {
		c.JSON(http.StatusOK, gin.H{
			"status":  1,
			"message": "会话ID不能为空",
			"data":    nil,
		})
		return
	}

	// 执行任务终止
	err := tm.TerminateTask(sessionId)
	if err != nil {
		c.JSON(http.StatusOK, gin.H{
			"status":  1,
			"message": "任务终止失败: " + err.Error(),
			"data":    nil,
		})
		return
	}

	c.JSON(http.StatusOK, gin.H{
		"status":  0,
		"message": "任务终止成功",
		"data":    nil,
	})
}

// 更新任务信息接口
func HandleUpdateTask(c *gin.Context, tm *TaskManager) {
	sessionId := c.Param("sessionId")
	if sessionId == "" {
		c.JSON(http.StatusOK, gin.H{
			"status":  1,
			"message": "会话ID不能为空",
			"data":    nil,
		})
		return
	}

	var req TaskUpdateRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusOK, gin.H{
			"status":  1,
			"message": "参数错误: " + err.Error(),
			"data":    nil,
		})
		return
	}

	// 执行任务信息更新
	err := tm.UpdateTask(sessionId, &req)
	if err != nil {
		c.JSON(http.StatusOK, gin.H{
			"status":  1,
			"message": "任务信息更新失败: " + err.Error(),
			"data":    nil,
		})
		return
	}

	c.JSON(http.StatusOK, gin.H{
		"status":  0,
		"message": "任务信息更新成功",
		"data":    nil,
	})
}

// 删除任务接口
func HandleDeleteTask(c *gin.Context, tm *TaskManager) {
	sessionId := c.Param("sessionId")
	if sessionId == "" {
		c.JSON(http.StatusOK, gin.H{
			"status":  1,
			"message": "会话ID不能为空",
			"data":    nil,
		})
		return
	}

	// 执行任务删除
	err := tm.DeleteTask(sessionId)
	if err != nil {
		c.JSON(http.StatusOK, gin.H{
			"status":  1,
			"message": "任务删除失败: " + err.Error(),
			"data":    nil,
		})
		return
	}

	c.JSON(http.StatusOK, gin.H{
		"status":  0,
		"message": "任务删除成功",
		"data":    nil,
	})
}

// 文件上传接口
func HandleUploadFile(c *gin.Context, tm *TaskManager) {
	// 1. 获取上传的文件
	file, header, err := c.Request.FormFile("file")
	if err != nil {
		c.JSON(http.StatusOK, gin.H{
			"status":  1,
			"message": "获取文件失败: " + err.Error(),
			"data":    nil,
		})
		return
	}
	defer file.Close()

	// 2. 验证文件大小
	if header.Size > 50*1024*1024 { // 50MB 限制
		c.JSON(http.StatusOK, gin.H{
			"status":  1,
			"message": "文件大小超过限制（最大50MB）",
			"data":    nil,
		})
		return
	}

	// 3. 验证文件类型
	allowedTypes := map[string]bool{
		".txt":  true,
		".pdf":  true,
		".doc":  true,
		".docx": true,
		".jpg":  true,
		".jpeg": true,
		".png":  true,
		".gif":  true,
		".zip":  true,
		".rar":  true,
	}

	ext := strings.ToLower(filepath.Ext(header.Filename))
	if !allowedTypes[ext] {
		c.JSON(http.StatusOK, gin.H{
			"status":  1,
			"message": "不支持的文件类型",
			"data":    nil,
		})
		return
	}

	// 4. 执行文件上传
	fileUrl, err := tm.UploadFile(header)
	if err != nil {
		c.JSON(http.StatusOK, gin.H{
			"status":  1,
			"message": "文件上传失败: " + err.Error(),
			"data":    nil,
		})
		return
	}

	c.JSON(http.StatusOK, gin.H{
		"status":  0,
		"message": "上传成功",
		"data": gin.H{
			"fileUrl": fileUrl,
		},
	})
}
