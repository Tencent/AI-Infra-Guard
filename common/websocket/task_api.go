package websocket

import (
	"fmt"
	"mime/multipart"
	"net/http"
	"path/filepath"
	"regexp"
	"strings"

	"github.com/gin-gonic/gin"
)

// 参数校验函数

// isValidSessionID 验证会话ID格式
func isValidSessionID(sessionId string) bool {
	// 只允许字母、数字、下划线、连字符
	matched, _ := regexp.MatchString(`^[a-zA-Z0-9_-]+$`, sessionId)
	return matched && len(sessionId) > 0 && len(sessionId) <= 50
}

// validateFileUpload 验证文件上传
func validateFileUpload(header *multipart.FileHeader) error {
	// 1. 文件名安全验证
	originalName := header.Filename
	if originalName == "" {
		return fmt.Errorf("文件名不能为空")
	}

	// 防止路径遍历攻击
	if strings.Contains(originalName, "..") || strings.Contains(originalName, "/") || strings.Contains(originalName, "\\") {
		return fmt.Errorf("文件名包含非法字符")
	}

	// 2. 文件扩展名验证
	ext := strings.ToLower(filepath.Ext(originalName))
	allowedExtensions := map[string]bool{
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
	if !allowedExtensions[ext] {
		return fmt.Errorf("不支持的文件类型: %s", ext)
	}

	// 3. 文件内容类型验证
	contentType := header.Header.Get("Content-Type")
	allowedMimeTypes := map[string]bool{
		"text/plain":         true,
		"application/pdf":    true,
		"application/msword": true,
		"application/vnd.openxmlformats-officedocument.wordprocessingml.document": true,
		"image/jpeg":                   true,
		"image/png":                    true,
		"image/gif":                    true,
		"application/zip":              true,
		"application/x-rar-compressed": true,
	}
	if !allowedMimeTypes[contentType] {
		return fmt.Errorf("不支持的文件内容类型: %s", contentType)
	}

	return nil
}

// validateTaskUpdateRequest 验证任务更新请求
func validateTaskUpdateRequest(req *TaskUpdateRequest) error {
	if req.Title != "" {
		// 清理和验证标题
		req.Title = strings.TrimSpace(req.Title)
		if len(req.Title) > 100 {
			return fmt.Errorf("标题长度超过限制")
		}
	}
	return nil
}

// SSE接口（实时事件推送）
func HandleTaskSSE(c *gin.Context, tm *TaskManager) {
	sessionId := c.Param("sessionId")
	if sessionId == "" {
		c.JSON(http.StatusBadRequest, gin.H{
			"status":  1,
			"message": "sessionId不能为空",
			"data":    nil,
		})
		return
	}

	// 验证sessionId格式
	if !isValidSessionID(sessionId) {
		c.JSON(http.StatusBadRequest, gin.H{
			"status":  1,
			"message": "无效的sessionId格式",
			"data":    nil,
		})
		return
	}

	// 验证任务是否存在
	session, err := tm.taskStore.GetSession(sessionId)
	if err != nil {
		c.JSON(http.StatusNotFound, gin.H{
			"status":  1,
			"message": "任务不存在",
			"data":    nil,
		})
		return
	}

	// 验证用户权限（只有任务创建者才能查看）
	username := c.GetString("username")
	if session.Username != username {
		c.JSON(http.StatusForbidden, gin.H{
			"status":  1,
			"message": "无权限查看此任务",
			"data":    nil,
		})
		return
	}

	// 建立SSE连接
	err = tm.EstablishSSEConnection(c.Writer, sessionId, username)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{
			"status":  1,
			"message": "建立SSE连接失败: " + err.Error(),
			"data":    nil,
		})
		return
	}

	// 保持连接活跃，等待客户端断开
	<-c.Request.Context().Done()

	// 客户端断开连接时，清理SSE连接
	tm.CloseSSESession(sessionId)
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

	// 验证sessionId格式
	if !isValidSessionID(req.SessionID) {
		c.JSON(http.StatusOK, gin.H{
			"status":  1,
			"message": "无效的会话ID格式",
			"data":    nil,
		})
		return
	}

	// 从中间件获取用户名
	username := c.GetString("username")

	// 设置用户名到请求中
	req.Username = username

	// 调用TaskManager
	err := tm.AddTask(&req)
	if err != nil {
		c.JSON(http.StatusOK, gin.H{
			"status":  1,
			"message": "任务创建失败: " + err.Error(),
			"data":    nil,
		})
		return
	}

	c.JSON(http.StatusOK, gin.H{
		"status":  0,
		"message": "任务创建成功",
		"data": gin.H{
			"sessionId": req.SessionID,
		},
	})
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

	// 验证sessionId格式
	if !isValidSessionID(sessionId) {
		c.JSON(http.StatusOK, gin.H{
			"status":  1,
			"message": "无效的会话ID格式",
			"data":    nil,
		})
		return
	}

	// 从中间件获取用户名
	username := c.GetString("username")

	// 调用TaskManager（包含权限验证）
	err := tm.TerminateTask(sessionId, username)
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

	// 验证sessionId格式
	if !isValidSessionID(sessionId) {
		c.JSON(http.StatusOK, gin.H{
			"status":  1,
			"message": "无效的会话ID格式",
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

	// 验证任务更新请求
	if err := validateTaskUpdateRequest(&req); err != nil {
		c.JSON(http.StatusOK, gin.H{
			"status":  1,
			"message": "请求参数验证失败: " + err.Error(),
			"data":    nil,
		})
		return
	}

	// 从中间件获取用户名
	username := c.GetString("username")

	// 执行任务信息更新（包含权限验证）
	err := tm.UpdateTask(sessionId, &req, username)
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

	// 验证sessionId格式
	if !isValidSessionID(sessionId) {
		c.JSON(http.StatusOK, gin.H{
			"status":  1,
			"message": "无效的会话ID格式",
			"data":    nil,
		})
		return
	}

	// 从中间件获取用户名
	username := c.GetString("username")

	// 执行任务删除（包含权限验证）
	err := tm.DeleteTask(sessionId, username)
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
	// 获取上传的文件
	file, err := c.FormFile("file")
	if err != nil {
		c.JSON(http.StatusOK, gin.H{
			"status":  1,
			"message": "获取上传文件失败: " + err.Error(),
			"data":    nil,
		})
		return
	}

	// 验证文件
	if err := validateFileUpload(file); err != nil {
		c.JSON(http.StatusOK, gin.H{
			"status":  1,
			"message": "文件验证失败: " + err.Error(),
			"data":    nil,
		})
		return
	}

	// 执行文件上传
	uploadResult, err := tm.UploadFile(file)
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
		"message": "文件上传成功",
		"data": gin.H{
			"originalName": uploadResult.OriginalName,
			"fileUrl":      uploadResult.FileURL,
		},
	})
}

// 获取任务列表接口
func HandleGetTaskList(c *gin.Context, tm *TaskManager) {
	// 从中间件获取用户名
	username := c.GetString("username")

	// 获取用户的任务列表
	tasks, err := tm.GetUserTasks(username)
	if err != nil {
		c.JSON(http.StatusOK, gin.H{
			"status":  1,
			"message": "获取任务列表失败: " + err.Error(),
			"data":    nil,
		})
		return
	}

	c.JSON(http.StatusOK, gin.H{
		"status":  0,
		"message": "获取任务列表成功",
		"data": gin.H{
			"tasks": tasks,
		},
	})
}

// HandleGetTaskDetail 获取任务详情
func HandleGetTaskDetail(c *gin.Context, tm *TaskManager) {
	sessionId := c.Param("sessionId")
	if sessionId == "" {
		c.JSON(http.StatusBadRequest, gin.H{
			"status":  1,
			"message": "sessionId不能为空",
			"data":    nil,
		})
		return
	}

	// 验证sessionId格式
	if !isValidSessionID(sessionId) {
		c.JSON(http.StatusBadRequest, gin.H{
			"status":  1,
			"message": "无效的sessionId格式",
			"data":    nil,
		})
		return
	}

	// 获取用户信息
	username := c.GetString("username")

	// 获取任务详情
	detail, err := tm.GetTaskDetail(sessionId, username)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{
			"status":  1,
			"message": "获取任务详情失败: " + err.Error(),
			"data":    nil,
		})
		return
	}

	c.JSON(http.StatusOK, gin.H{
		"status":  0,
		"message": "获取任务详情成功",
		"data":    detail,
	})
}

// HandleDownloadFile 文件下载接口
func HandleDownloadFile(c *gin.Context, tm *TaskManager) {
	sessionId := c.Param("sessionId")
	if sessionId == "" {
		c.JSON(http.StatusBadRequest, gin.H{
			"status":  1,
			"message": "sessionId不能为空",
			"data":    nil,
		})
		return
	}

	// 验证sessionId格式
	if !isValidSessionID(sessionId) {
		c.JSON(http.StatusBadRequest, gin.H{
			"status":  1,
			"message": "无效的会话ID格式",
			"data":    nil,
		})
		return
	}

	// 解析请求体
	var req struct {
		FileURL string `json:"fileUrl" binding:"required"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{
			"status":  1,
			"message": "参数错误: " + err.Error(),
			"data":    nil,
		})
		return
	}

	// 验证fileUrl格式
	if req.FileURL == "" {
		c.JSON(http.StatusBadRequest, gin.H{
			"status":  1,
			"message": "文件URL不能为空",
			"data":    nil,
		})
		return
	}

	// 获取用户信息
	username := c.GetString("username")

	// 执行文件下载
	err := tm.DownloadFile(sessionId, req.FileURL, username, c)
	if err != nil {
		// 根据错误类型返回不同的状态码
		switch err.Error() {
		case "任务不存在":
			c.JSON(http.StatusNotFound, gin.H{
				"status":  1,
				"message": "任务不存在",
				"data":    nil,
			})
		case "无权限访问此任务":
			c.JSON(http.StatusForbidden, gin.H{
				"status":  1,
				"message": "无权限访问此任务",
				"data":    nil,
			})
		case "文件不存在于此任务中":
			c.JSON(http.StatusNotFound, gin.H{
				"status":  1,
				"message": "文件不存在于此任务中",
				"data":    nil,
			})
		case "文件不存在":
			c.JSON(http.StatusNotFound, gin.H{
				"status":  1,
				"message": "文件不存在",
				"data":    nil,
			})
		default:
			c.JSON(http.StatusInternalServerError, gin.H{
				"status":  1,
				"message": "文件下载失败: " + err.Error(),
				"data":    nil,
			})
		}
		return
	}

	// 文件下载成功，响应头已在DownloadFile方法中设置
}
