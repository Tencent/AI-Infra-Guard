package websocket

import (
	"net/http"

	"git.code.oa.com/trpc-go/trpc-go/log"
	_ "git.code.oa.com/trpc-go/trpc-log-zhiyan"
	"github.com/Tencent/AI-Infra-Guard/pkg/database"
	"github.com/gin-gonic/gin"
)

// ModelInfo 模型信息
type ModelInfo struct {
	Model   string `json:"model" binding:"required"`
	Token   string `json:"token" binding:"required"`
	BaseURL string `json:"base_url" binding:"required"`
	Note    string `json:"note"`
}

// CreateModelRequest 创建模型请求
type CreateModelRequest struct {
	ModelID string    `json:"model_id" binding:"required"`
	Model   ModelInfo `json:"model" binding:"required"`
}

// UpdateModelRequest 更新模型请求
type UpdateModelRequest struct {
	Model ModelInfo `json:"model" binding:"required"`
}

// DeleteModelRequest 删除模型请求
type DeleteModelRequest struct {
	ModelIDs []string `json:"model_ids" binding:"required"`
}

// ModelManager 模型管理器
type ModelManager struct {
	modelStore *database.ModelStore
}

// NewModelManager 创建新的ModelManager实例
func NewModelManager(modelStore *database.ModelStore) *ModelManager {
	return &ModelManager{
		modelStore: modelStore,
	}
}

// HandleGetModelList 获取模型列表接口
func HandleGetModelList(c *gin.Context, mm *ModelManager) {
	traceID := getTraceID(c)
	username := c.GetString("username")

	log.Infof("用户请求获取模型列表: trace_id=%s, username=%s", traceID, username)

	// 获取所有模型
	models, err := mm.modelStore.GetAllModels()
	if err != nil {
		log.Errorf("获取模型列表失败: trace_id=%s, username=%s, error=%v", traceID, username, err)
		c.JSON(http.StatusOK, gin.H{
			"status":  1,
			"message": "获取模型列表失败: " + err.Error(),
			"data":    nil,
		})
		return
	}

	log.Infof("获取模型列表成功: trace_id=%s, username=%s, count=%d", traceID, username, len(models))

	c.JSON(http.StatusOK, gin.H{
		"status":  0,
		"message": "获取模型列表成功",
		"data":    models,
	})
}

// HandleGetModelDetail 获取模型详情接口
func HandleGetModelDetail(c *gin.Context, mm *ModelManager) {
	traceID := getTraceID(c)
	modelID := c.Param("modelId")
	username := c.GetString("username")

	// 1. 字段校验
	if modelID == "" {
		log.Errorf("模型ID为空: trace_id=%s, username=%s", traceID, username)
		c.JSON(http.StatusOK, gin.H{
			"status":  1,
			"message": "模型ID不能为空",
			"data":    nil,
		})
		return
	}

	log.Infof("用户请求获取模型详情: trace_id=%s, modelID=%s, username=%s", traceID, modelID, username)

	// 2. 获取模型信息
	model, err := mm.modelStore.GetModel(modelID)
	if err != nil {
		log.Errorf("获取模型详情失败: trace_id=%s, modelID=%s, username=%s, error=%v", traceID, modelID, username, err)
		c.JSON(http.StatusOK, gin.H{
			"status":  1,
			"message": "模型不存在",
			"data":    nil,
		})
		return
	}

	// 3. 身份校验（只有创建者可以查看）
	if model.Username != username {
		log.Errorf("无权限查看模型: trace_id=%s, modelID=%s, username=%s, owner=%s", traceID, modelID, username, model.Username)
		c.JSON(http.StatusOK, gin.H{
			"status":  1,
			"message": "无权限查看此模型",
			"data":    nil,
		})
		return
	}

	log.Infof("获取模型详情成功: trace_id=%s, modelID=%s, username=%s", traceID, modelID, username)

	c.JSON(http.StatusOK, gin.H{
		"status":  0,
		"message": "获取模型详情成功",
		"data":    model,
	})
}

// HandleCreateModel 创建模型接口
func HandleCreateModel(c *gin.Context, mm *ModelManager) {
	traceID := getTraceID(c)
	username := c.GetString("username")

	// 1. 字段校验
	var req CreateModelRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		log.Errorf("请求参数解析失败: trace_id=%s, username=%s, error=%v", traceID, username, err)
		c.JSON(http.StatusOK, gin.H{
			"status":  1,
			"message": "请求参数错误: " + err.Error(),
			"data":    nil,
		})
		return
	}

	// 2. 验证必填字段
	if req.ModelID == "" {
		log.Errorf("模型ID为空: trace_id=%s, username=%s", traceID, username)
		c.JSON(http.StatusOK, gin.H{
			"status":  1,
			"message": "模型ID不能为空",
			"data":    nil,
		})
		return
	}

	if req.Model.Model == "" {
		log.Errorf("模型名称为空: trace_id=%s, username=%s", traceID, username)
		c.JSON(http.StatusOK, gin.H{
			"status":  1,
			"message": "模型名称不能为空",
			"data":    nil,
		})
		return
	}

	if req.Model.Token == "" {
		log.Errorf("API Token为空: trace_id=%s, username=%s", traceID, username)
		c.JSON(http.StatusOK, gin.H{
			"status":  1,
			"message": "API Token不能为空",
			"data":    nil,
		})
		return
	}

	if req.Model.BaseURL == "" {
		log.Errorf("基础URL为空: trace_id=%s, username=%s", traceID, username)
		c.JSON(http.StatusOK, gin.H{
			"status":  1,
			"message": "基础URL不能为空",
			"data":    nil,
		})
		return
	}

	log.Infof("用户请求创建模型: trace_id=%s, modelID=%s, modelName=%s, username=%s", traceID, req.ModelID, req.Model.Model, username)

	// 3. 检查模型是否已存在
	exists, err := mm.modelStore.CheckModelExists(req.ModelID)
	if err != nil {
		log.Errorf("检查模型是否存在失败: trace_id=%s, modelID=%s, username=%s, error=%v", traceID, req.ModelID, username, err)
		c.JSON(http.StatusOK, gin.H{
			"status":  1,
			"message": "检查模型失败: " + err.Error(),
			"data":    nil,
		})
		return
	}

	if exists {
		log.Errorf("模型已存在: trace_id=%s, modelID=%s, username=%s", traceID, req.ModelID, username)
		c.JSON(http.StatusOK, gin.H{
			"status":  1,
			"message": "模型ID已存在",
			"data":    nil,
		})
		return
	}

	// 4. 创建模型
	model := &database.Model{
		ModelID:   req.ModelID,
		Username:  username,
		ModelName: req.Model.Model,
		Token:     req.Model.Token,
		BaseURL:   req.Model.BaseURL,
		Note:      req.Model.Note,
	}

	err = mm.modelStore.CreateModel(model)
	if err != nil {
		log.Errorf("创建模型失败: trace_id=%s, modelID=%s, username=%s, error=%v", traceID, req.ModelID, username, err)
		c.JSON(http.StatusOK, gin.H{
			"status":  1,
			"message": "创建模型失败: " + err.Error(),
			"data":    nil,
		})
		return
	}

	log.Infof("创建模型成功: trace_id=%s, modelID=%s, modelName=%s, username=%s", traceID, req.ModelID, req.Model.Model, username)

	c.JSON(http.StatusOK, gin.H{
		"status":  0,
		"message": "模型创建成功",
		"data":    nil,
	})
}

// HandleUpdateModel 更新模型接口
func HandleUpdateModel(c *gin.Context, mm *ModelManager) {
	traceID := getTraceID(c)
	modelID := c.Param("modelId")
	username := c.GetString("username")

	// 1. 字段校验
	if modelID == "" {
		log.Errorf("模型ID为空: trace_id=%s, username=%s", traceID, username)
		c.JSON(http.StatusOK, gin.H{
			"status":  1,
			"message": "模型ID不能为空",
			"data":    nil,
		})
		return
	}

	var req UpdateModelRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		log.Errorf("请求参数解析失败: trace_id=%s, modelID=%s, username=%s, error=%v", traceID, modelID, username, err)
		c.JSON(http.StatusOK, gin.H{
			"status":  1,
			"message": "请求参数错误: " + err.Error(),
			"data":    nil,
		})
		return
	}

	log.Infof("用户请求更新模型: trace_id=%s, modelID=%s, username=%s", traceID, modelID, username)

	// 2. 身份校验（检查模型是否存在且属于该用户）
	exists, err := mm.modelStore.CheckModelExistsByUser(modelID, username)
	if err != nil {
		log.Errorf("检查模型权限失败: trace_id=%s, modelID=%s, username=%s, error=%v", traceID, modelID, username, err)
		c.JSON(http.StatusOK, gin.H{
			"status":  1,
			"message": "检查模型权限失败: " + err.Error(),
			"data":    nil,
		})
		return
	}

	if !exists {
		log.Errorf("模型不存在或无权限: trace_id=%s, modelID=%s, username=%s", traceID, modelID, username)
		c.JSON(http.StatusOK, gin.H{
			"status":  1,
			"message": "模型不存在或无权限",
			"data":    nil,
		})
		return
	}

	// 3. 更新模型
	updates := map[string]interface{}{
		"model_name": req.Model.Model,
		"token":      req.Model.Token,
		"base_url":   req.Model.BaseURL,
		"note":       req.Model.Note,
	}

	err = mm.modelStore.UpdateModel(modelID, username, updates)
	if err != nil {
		log.Errorf("更新模型失败: trace_id=%s, modelID=%s, username=%s, error=%v", traceID, modelID, username, err)
		c.JSON(http.StatusOK, gin.H{
			"status":  1,
			"message": "更新模型失败: " + err.Error(),
			"data":    nil,
		})
		return
	}

	log.Infof("更新模型成功: trace_id=%s, modelID=%s, username=%s", traceID, modelID, username)

	c.JSON(http.StatusOK, gin.H{
		"status":  0,
		"message": "模型更新成功",
		"data":    nil,
	})
}

// HandleDeleteModel 删除模型接口（支持单个和批量）
func HandleDeleteModel(c *gin.Context, mm *ModelManager) {
	traceID := getTraceID(c)
	username := c.GetString("username")

	// 1. 字段校验
	var req DeleteModelRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		log.Errorf("请求参数解析失败: trace_id=%s, username=%s, error=%v", traceID, username, err)
		c.JSON(http.StatusOK, gin.H{
			"status":  1,
			"message": "请求参数错误: " + err.Error(),
			"data":    nil,
		})
		return
	}

	if len(req.ModelIDs) == 0 {
		log.Errorf("模型ID列表为空: trace_id=%s, username=%s", traceID, username)
		c.JSON(http.StatusOK, gin.H{
			"status":  1,
			"message": "模型ID列表不能为空",
			"data":    nil,
		})
		return
	}

	log.Infof("用户请求删除模型: trace_id=%s, modelIDs=%v, username=%s", traceID, req.ModelIDs, username)

	// 2. 身份校验（检查所有模型是否属于该用户）
	for _, modelID := range req.ModelIDs {
		exists, err := mm.modelStore.CheckModelExistsByUser(modelID, username)
		if err != nil {
			log.Errorf("检查模型权限失败: trace_id=%s, modelID=%s, username=%s, error=%v", traceID, modelID, username, err)
			c.JSON(http.StatusOK, gin.H{
				"status":  1,
				"message": "检查模型权限失败: " + err.Error(),
				"data":    nil,
			})
			return
		}

		if !exists {
			log.Errorf("模型不存在或无权限: trace_id=%s, modelID=%s, username=%s", traceID, modelID, username)
			c.JSON(http.StatusOK, gin.H{
				"status":  1,
				"message": "模型不存在或无权限",
				"data":    nil,
			})
			return
		}
	}

	// 3. 批量删除模型
	deletedCount, err := mm.modelStore.BatchDeleteModels(req.ModelIDs, username)
	if err != nil {
		log.Errorf("删除模型失败: trace_id=%s, modelIDs=%v, username=%s, error=%v", traceID, req.ModelIDs, username, err)
		c.JSON(http.StatusOK, gin.H{
			"status":  1,
			"message": "删除模型失败: " + err.Error(),
			"data":    nil,
		})
		return
	}

	log.Infof("删除模型成功: trace_id=%s, modelIDs=%v, username=%s, deletedCount=%d", traceID, req.ModelIDs, username, deletedCount)

	c.JSON(http.StatusOK, gin.H{
		"status":  0,
		"message": "删除成功",
		"data":    nil,
	})
}
