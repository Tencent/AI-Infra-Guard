package websocket

import (
	"embed"
	"mime"
	"path/filepath"

	"github.com/Tencent/AI-Infra-Guard/common/middleware"
	"github.com/Tencent/AI-Infra-Guard/common/trpc"
	"github.com/Tencent/AI-Infra-Guard/internal/options"
	"github.com/Tencent/AI-Infra-Guard/pkg/database"
	"github.com/gin-gonic/gin"
	"trpc.group/trpc-go/trpc-go/log"
)

//go:embed static/*
var staticFS embed.FS

func RunWebServer(options *options.Options) {
	// 1. 初始化trpc-go
	if err := trpc.InitTrpc("./trpc_go.yaml"); err != nil {
		log.Fatalf("Trpc-go初始化失败: %v", err)
	}
	log.Infof("Trpc-go initialized successfully: trace_id=system_startup")

	r := gin.Default()
	wsServer := NewWSServer(options)

	// 2. 添加中间件
	r.Use(middleware.TrpcMiddleware())
	r.Use(middleware.RequestLoggerMiddleware()) // 添加请求参数日志中间件
	// r.Use(middleware.MetricsMiddleware()) // 移除HTTP监控中间件，依赖TRPC自动监控

	// 3. 初始化数据库和Agentmanager
	dbConfig := database.LoadConfigFromEnv() // 从环境变量加载数据库配置
	db, err := database.InitDB(dbConfig)
	if err != nil {
		log.Errorf("数据库初始化失败: trace_id=system_startup, error=%v", err)

	}
	taskStore := database.NewTaskStore(db)
	if err := taskStore.Init(); err != nil {
		log.Errorf("初始化tasks表失败: trace_id=system_startup, error=%v", err)
		log.Fatalf("初始化tasks表失败: %v", err)
	}

	// 初始化模型存储
	modelStore := database.NewModelStore(db)
	if err := modelStore.Init(); err != nil {
		log.Errorf("初始化models表失败: trace_id=system_startup, error=%v", err)

	}

	// 初始化AgentManager
	agentManager := NewAgentManager()

	// 初始化ModelManager
	modelManager := NewModelManager(modelStore)

	// 初始化文件上传配置（支持环境变量）
	fileConfig := LoadFileUploadConfigFromEnv()

	// 验证文件上传配置
	if err := fileConfig.ValidateConfig(); err != nil {
		log.Errorf("文件上传配置验证失败: trace_id=system_startup, error=%v", err)

	}

	// 初始化SSE管理器
	sseManager := NewSSEManager()

	taskManager := NewTaskManager(agentManager, taskStore, modelStore, fileConfig, sseManager)

	// 将 TaskManager 注入到 AgentManager
	agentManager.SetTaskManager(taskManager)

	// API 版本分组
	v1 := r.Group("/api/v1")
	{
		// 1. 知识库模块
		knowledge := v1.Group("/knowledge")
		{
			// 对抗样本库
			knowledge.Group("/samples")

			// AI应用指纹
			fingerprints := knowledge.Group("/fingerprints")
			{
				// 管理功能
				fingerprints.GET("", HandleListFingerprints)
				fingerprints.POST("", HandleCreateFingerprint)
				fingerprints.PUT("/:name", HandleEditFingerprint)
				fingerprints.DELETE("", HandleDeleteFingerprint)
			}

			// 漏洞库
			vulnerabilities := knowledge.Group("/vulnerabilities")
			{
				// 管理功能
				vulnerabilities.GET("", HandleListVulnerabilities(options))
				vulnerabilities.POST("", HandleCreateVulnerability(options))
				vulnerabilities.PUT("/:cve", HandleEditVulnerability)
				vulnerabilities.DELETE("", HandleBatchDeleteVulnerabilities)
			}
		}

		// 2. 模型安全中心
		modelSecurity := v1.Group("/model-security")
		{
			// 任务管理
			modelSecurity.Group("/tasks")

			// WebSocket 连接 (原有 /ws 接口迁移)
			modelSecurity.GET("/ws", func(c *gin.Context) {
				wsServer.HandleAIInfraWS(c.Writer, c.Request)
			})
		}

		// 3. AI应用安全中心
		appSecurity := v1.Group("/app")
		{
			// 应用IOA中间件
			appSecurity.Use(setupIdentityMiddleware())

			// 任务管理
			tasks := appSecurity.Group("/tasks")
			{
				// 获取任务列表接口
				tasks.GET("", func(c *gin.Context) {
					HandleGetTaskList(c, taskManager)
				})
				// 获取任务详情接口
				tasks.GET("/:sessionId", func(c *gin.Context) {
					HandleGetTaskDetail(c, taskManager)
				})
				// SSE接口
				tasks.GET("/sse/:sessionId", func(c *gin.Context) {
					HandleTaskSSE(c, taskManager)
				})
				// 新建任务接口
				tasks.POST("", func(c *gin.Context) {
					HandleTaskCreate(c, taskManager)
				})
				// 文件上传接口
				tasks.POST("/uploadFile", func(c *gin.Context) {
					HandleUploadFile(c, taskManager)
				})
				// 文件下载接口
				tasks.POST("/:sessionId/downloadFile", func(c *gin.Context) {
					HandleDownloadFile(c, taskManager)
				})
				// 编辑任务接口
				tasks.PUT("/:sessionId", func(c *gin.Context) {
					HandleUpdateTask(c, taskManager)
				})
				// 删除任务接口
				tasks.DELETE("/:sessionId", func(c *gin.Context) {
					HandleDeleteTask(c, taskManager)
				})
				// 终止任务接口
				tasks.POST("/:sessionId/terminate", func(c *gin.Context) {
					HandleTerminateTask(c, taskManager)
				})
			}

			// 模型管理
			models := appSecurity.Group("/models")
			{
				// 获取模型列表接口
				models.GET("", func(c *gin.Context) {
					HandleGetModelList(c, modelManager)
				})
				// 获取模型详情接口
				models.GET("/:modelId", func(c *gin.Context) {
					HandleGetModelDetail(c, modelManager)
				})
				// 创建模型接口
				models.POST("", func(c *gin.Context) {
					HandleCreateModel(c, modelManager)
				})
				// 更新模型接口
				models.PUT("/:modelId", func(c *gin.Context) {
					HandleUpdateModel(c, modelManager)
				})
				// 删除模型接口（支持单个和批量）
				models.DELETE("", func(c *gin.Context) {
					HandleDeleteModel(c, modelManager)
				})
			}
		}

		// 4. Agent 管理
		agents := v1.Group("/agents")
		{
			// 只需要WebSocket入口
			agents.GET("/ws", agentManager.HandleAgentWebSocket())
		}
	}

	// 静态文件处理
	r.NoRoute(func(c *gin.Context) {
		assetPath := "static" + c.Request.URL.Path
		if c.Request.URL.Path == "/" {
			assetPath = "static/index.html"
		}

		assetData, err := staticFS.ReadFile(assetPath)
		if err != nil {
			assetData, err = staticFS.ReadFile("static/index.html")
			if err != nil {
				c.String(500, "Internal Server Error")
				return
			}
		}

		mimeType := mime.TypeByExtension(filepath.Ext(assetPath))
		if mimeType == "" {
			mimeType = "text/plain"
		}
		c.Header("Content-Type", mimeType)
		c.Data(200, mimeType, assetData)
	})

	// 添加文件访问路由 - 确保上传的文件可以被访问
	// 注释掉静态文件映射，因为我们已经有了专门的下载接口
	// if fileConfig.BaseURL != "" {
	// 	// 设置静态文件服务，将URL路径映射到实际存储目录
	// 	r.Static(fileConfig.BaseURL, fileConfig.UploadDir)
	// 	gologger.Infof("文件访问路由已配置: %s -> %s", fileConfig.BaseURL, fileConfig.UploadDir)
	// }

	// 启动服务器
	log.Infof("Starting WebServer: trace_id=system_startup, addr=%s", options.WebServerAddr)
	if err := r.Run(options.WebServerAddr); err != nil {
		log.Errorf("Could not start WebSocket server: trace_id=system_startup, error=%s", err)
	}
}

// 配置身份认证中间件
func setupIdentityMiddleware() gin.HandlerFunc {
	return func(c *gin.Context) {
		// 优先从请求头获取username字段
		username := c.GetHeader("username")

		// 如果都没有，使用默认的公共用户
		if username == "" {
			username = "public_user"
		}

		// 存储到gin上下文
		c.Set("username", username)

		c.Next()
	}
}
