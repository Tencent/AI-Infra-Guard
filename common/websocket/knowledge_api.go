package websocket

// 本文件用于实现知识库（指纹库、漏洞库）相关的API接口。
// 后续可在此文件中实现指纹库、漏洞库的增删改查、分页、条件查询等接口。

// TODO: 实现指纹库和漏洞库相关的API接口。

// 替换为实际指纹结构体路径

import (
	"fmt"
	"net/http"
	"os"
	"path/filepath"
	"regexp"
	"strconv"
	"strings"

	"github.com/Tencent/AI-Infra-Guard/common/fingerprints/parser"
	"github.com/Tencent/AI-Infra-Guard/common/runner"
	"github.com/Tencent/AI-Infra-Guard/internal/gologger"
	"github.com/Tencent/AI-Infra-Guard/internal/options"
	"github.com/Tencent/AI-Infra-Guard/pkg/vulstruct"
	"github.com/gin-gonic/gin"
	"gopkg.in/yaml.v3"
)

// 合法性校验
var validName = regexp.MustCompile(`^[a-zA-Z0-9_-]+$`)

func isValidName(name string) bool {
	return validName.MatchString(name)
}

// 获取指纹列表，支持分页和名字模糊
func HandleListFingerprints(c *gin.Context) {
	// 1. 解析分页参数
	pageStr := c.DefaultQuery("page", "1")
	sizeStr := c.DefaultQuery("size", "10")
	page, _ := strconv.Atoi(pageStr)
	size, _ := strconv.Atoi(sizeStr)
	if page < 1 {
		page = 1
	}
	if size < 1 {
		size = 10
	}

	// 2. 获取查询参数
	nameQuery := strings.ToLower(c.DefaultQuery("name", ""))
	// severityQuery := strings.ToLower(c.DefaultQuery("severity", ""))
	// categoryQuery := strings.ToLower(c.DefaultQuery("category", ""))

	// 3. 读取 data/fingerprints/ 下所有分类和YAML文件
	var allFingerprints []parser.FingerPrint
	root := "data/fingerprints"
	filepath.WalkDir(root, func(path string, d os.DirEntry, err error) error {
		if err != nil {
			return nil // 忽略错误
		}
		if !d.IsDir() && strings.HasSuffix(d.Name(), ".yaml") {
			content, _ := os.ReadFile(path)
			fp, err := parser.InitFingerPrintFromData(content)
			if err == nil && fp != nil {
				allFingerprints = append(allFingerprints, *fp)
			}
		}
		return nil
	})

	// 4. 条件过滤
	var filteredFingerprints []parser.FingerPrint
	for _, fp := range allFingerprints {
		// name模糊匹配
		if nameQuery != "" && !strings.Contains(strings.ToLower(fp.Info.Name), nameQuery) {
			continue
		}
		// severity等值匹配
		// if severityQuery != "" && strings.ToLower(fp.Info.Severity) != severityQuery {
		// 	continue
		// }
		// // category等值匹配（在metadata中查找）
		// if categoryQuery != "" {
		// 	cat, ok := fp.Info.Metadata["category"]
		// 	if !ok || strings.ToLower(cat) != categoryQuery {
		// 		continue
		// 	}
		// }
		filteredFingerprints = append(filteredFingerprints, fp)
	}

	// 5. 分页
	total := len(filteredFingerprints)
	start := (page - 1) * size
	end := start + size
	if start > total {
		start = total
	}
	if end > total {
		end = total
	}
	items := filteredFingerprints[start:end]

	// 6. 返回
	c.JSON(http.StatusOK, gin.H{
		"status":  0,
		"message": "success",
		"data": gin.H{
			"total": total,
			"page":  page,
			"size":  size,
			"items": items,
		},
	})
}

// 创建指纹
func HandleCreateFingerprint(c *gin.Context) {
	// 1. 解析请求体，获取file_content字段
	type FingerprintUploadRequest struct {
		FileContent string `json:"file_content" binding:"required"`
	}
	var req FingerprintUploadRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"status": 1, "message": "参数解析失败"})
		return
	}

	// 2. 解析YAML为parser.FingerPrint结构体
	var fp parser.FingerPrint
	if err := yaml.Unmarshal([]byte(req.FileContent), &fp); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"status": 1, "message": "YAML解析失败: " + err.Error()})
		return
	}
	if fp.Info.Name == "" {
		c.JSON(http.StatusBadRequest, gin.H{"status": 1, "message": "指纹名称不能为空"})
		return
	}

	// 新增：用和读取时一致的解析逻辑做一次完整校验
	if _, err := parser.InitFingerPrintFromData([]byte(req.FileContent)); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"status": 1, "message": "指纹内容校验失败: " + err.Error()})
		return
	}

	// 3. 检查指纹名称是否已存在
	if !isValidName(fp.Info.Name) {
		c.JSON(http.StatusBadRequest, gin.H{"status": 1, "message": "指纹名称非法"})
		return
	}
	yamlPath := filepath.Join("data/fingerprints", fp.Info.Name+".yaml")
	if _, err := os.Stat(yamlPath); err == nil {
		c.JSON(http.StatusConflict, gin.H{"status": 1, "message": "指纹已存在"})
		return
	}

	// 4. 写入YAML文件
	if err := os.WriteFile(yamlPath, []byte(req.FileContent), 0644); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"status": 1, "message": "文件写入失败: " + err.Error()})
		return
	}

	// 5. 返回精简响应
	c.JSON(http.StatusOK, gin.H{"status": 0, "message": "创建指纹成功"})
}

// 批量删除指纹处理函数
type BatchDeleteRequest struct {
	Names []string `json:"names"`
}

func HandleDeleteFingerprint(c *gin.Context) {
	var req BatchDeleteRequest
	if err := c.ShouldBindJSON(&req); err != nil || len(req.Names) == 0 {
		c.JSON(http.StatusBadRequest, gin.H{"status": 1, "message": "参数错误", "data": nil})
		return
	}

	var deleted []string
	var notFound []string

	for _, name := range req.Names {
		if !isValidName(name) {
			notFound = append(notFound, name)
			continue
		}
		yamlPath := filepath.Join("data/fingerprints", name+".yaml")
		if _, err := os.Stat(yamlPath); os.IsNotExist(err) {
			notFound = append(notFound, name)
			continue
		}
		if err := os.Remove(yamlPath); err == nil {
			deleted = append(deleted, name)
		}
	}

	msg := "删除完成"
	if len(notFound) > 0 {
		msg += "，部分指纹未找到: " + strings.Join(notFound, ", ")
	}

	c.JSON(http.StatusOK, gin.H{
		"status":  0,
		"message": msg,
		"data": gin.H{
			"deleted":  deleted,
			"notFound": notFound,
		},
	})
}

// 编辑指纹处理函数
func HandleEditFingerprint(c *gin.Context) {
	// 1. 获取原指纹名称
	oldName := c.Param("name")
	if oldName == "" {
		c.JSON(http.StatusBadRequest, gin.H{"status": 1, "message": "指纹名称不能为空"})
		return
	}

	type FingerprintUploadRequest struct {
		FileContent string `json:"file_content" binding:"required"`
	}
	var req FingerprintUploadRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"status": 1, "message": "参数解析失败"})
		return
	}
	// 2. 解析YAML为parser.FingerPrint结构体
	var fp parser.FingerPrint
	if err := yaml.Unmarshal([]byte(req.FileContent), &fp); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"status": 1, "message": "YAML解析失败: " + err.Error()})
		return
	}
	if fp.Info.Name == "" {
		c.JSON(http.StatusBadRequest, gin.H{"status": 1, "message": "指纹名称不能为空"})
		return
	}

	// 新增：用和读取时一致的解析逻辑做一次完整校验
	if _, err := parser.InitFingerPrintFromData([]byte(req.FileContent)); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"status": 1, "message": "指纹内容校验失败: " + err.Error()})
		return
	}

	// 3. 校验原文件是否存在
	if !isValidName(oldName) || !isValidName(fp.Info.Name) {
		c.JSON(http.StatusBadRequest, gin.H{"status": 1, "message": "指纹名称非法"})
		return
	}
	oldPath := filepath.Join("data/fingerprints", oldName+".yaml")
	if _, err := os.Stat(oldPath); os.IsNotExist(err) {
		c.JSON(http.StatusNotFound, gin.H{"status": 1, "message": "原指纹不存在"})
		return
	}
	newPath := filepath.Join("data/fingerprints", fp.Info.Name+".yaml")

	// 4. 校验新文件名是否已存在（且不是原文件）
	if newPath != oldPath {
		if _, err := os.Stat(newPath); err == nil {
			c.JSON(http.StatusConflict, gin.H{"status": 1, "message": "新指纹名称已存在"})
			return
		}
	}

	// 5. 如果新旧文件名不同，删除原文件
	if oldName != fp.Info.Name {
		_ = os.Remove(oldPath) // 删除老文件
	}

	// 6. 写入新内容（新文件名）
	if err := os.WriteFile(newPath, []byte(req.FileContent), 0644); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"status": 1, "message": "文件写入失败: " + err.Error()})
		return
	}

	c.JSON(http.StatusOK, gin.H{"status": 0, "message": "修改指纹成功"})
}

// 漏洞库分页+条件查询接口
func HandleListVulnerabilities(options *options.Options) gin.HandlerFunc {
	return func(c *gin.Context) {
		// 1. 解析分页和查询参数
		pageStr := c.DefaultQuery("page", "1")
		sizeStr := c.DefaultQuery("size", "10")
		cveQuery := strings.ToLower(c.DefaultQuery("cve", ""))
		// severityQuery := strings.ToLower(c.DefaultQuery("severity", ""))
		categoryQuery := c.DefaultQuery("category", "")
		page, _ := strconv.Atoi(pageStr)
		size, _ := strconv.Atoi(sizeStr)
		if page < 1 {
			page = 1
		}
		if size < 1 {
			size = 10
		}

		// 2. 创建 runner 实例
		r, err := runner.New(options)
		if err != nil {
			gologger.Errorf("创建runner失败: %v", err)
			c.JSON(500, gin.H{
				"status":  1,
				"message": err.Error(),
				"data":    nil,
			})
			return
		}
		defer r.Close()

		// 3. 获取所有指纹及其漏洞，拉平成一个大vul列表
		allFpInfos := r.GetFpAndVulList()
		allVuls := make([]vulstruct.VersionVul, 0)
		for _, fp := range allFpInfos {
			if categoryQuery != "" && fp.FpName != categoryQuery {
				continue
			}
			allVuls = append(allVuls, fp.Vuls...)
		}

		// 4. 条件过滤
		filteredVuls := make([]vulstruct.VersionVul, 0)
		for _, vul := range allVuls {
			if cveQuery != "" && !strings.Contains(strings.ToLower(vul.Info.CVEName), cveQuery) {
				continue
			}
			if categoryQuery != "" && !strings.Contains(strings.ToLower(vul.Info.FingerPrintName), categoryQuery) {
				continue
			}
			filteredVuls = append(filteredVuls, vul)
		}

		// 5. 分页
		total := len(filteredVuls)
		start := (page - 1) * size
		end := start + size
		if start > total {
			start = total
		}
		if end > total {
			end = total
		}
		items := filteredVuls[start:end]

		// 6. 返回
		c.JSON(http.StatusOK, gin.H{
			"status":  0,
			"message": "success",
			"data": gin.H{
				"page":  page,
				"size":  size,
				"total": total,
				"items": items,
			},
		})
	}
}

// createTempFileWithContent 创建一个临时文件并写入内容
// 返回临时文件路径和一个清理函数
func createTempFileWithContent(prefix string, content []byte) (string, func(), error) {
	// 创建临时文件
	tmpFile, err := os.CreateTemp("", prefix)
	if err != nil {
		return "", nil, fmt.Errorf("创建临时文件失败: %w", err)
	}

	// 写入内容
	if err := os.WriteFile(tmpFile.Name(), content, 0600); err != nil {
		os.Remove(tmpFile.Name())
		return "", nil, fmt.Errorf("写入临时文件失败: %w", err)
	}

	// 返回清理函数
	cleanup := func() {
		os.Remove(tmpFile.Name())
	}

	return tmpFile.Name(), cleanup, nil
}

// 添加漏洞信息（带严格校验）
func HandleCreateVulnerability(options *options.Options) gin.HandlerFunc {
	return func(c *gin.Context) {
		// 1. 解析请求体，获取file_content
		type VulnUploadRequest struct {
			FileContent string `json:"file_content" binding:"required"`
		}
		var req VulnUploadRequest
		if err := c.ShouldBindJSON(&req); err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"status": 1, "message": "参数解析失败"})
			return
		}

		// 2. 反序列化为vulstruct.VersionVul，校验CVE编号等必填字段
		var vul vulstruct.VersionVul
		if err := yaml.Unmarshal([]byte(req.FileContent), &vul); err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"status": 1, "message": "YAML解析失败: " + err.Error()})
			return
		}
		if vul.Info.CVEName == "" {
			c.JSON(http.StatusBadRequest, gin.H{"status": 1, "message": "CVE编号不能为空"})
			return
		}
		if !isValidName(vul.Info.CVEName) {
			c.JSON(http.StatusBadRequest, gin.H{"status": 1, "message": "CVE编号非法"})
			return
		}
		if vul.Info.FingerPrintName != "" && !isValidName(vul.Info.FingerPrintName) {
			c.JSON(http.StatusBadRequest, gin.H{"status": 1, "message": "指纹分类名称非法"})
			return
		}

		// 3. 临时写入到校验用的临时文件
		tmpFile, cleanup, err := createTempFileWithContent("vuln-check-*", []byte(req.FileContent))
		if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"status": 1, "message": err.Error()})
			return
		}
		defer cleanup()

		// 4. 用vulstruct.NewAdvisoryEngine加载临时文件做完整业务校验
		_, err = vulstruct.ReadVersionVulSingFile(tmpFile)
		if err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"status": 1, "message": "漏洞内容校验失败: " + err.Error()})
			return
		}

		// 5. 校验通过后，正式写入到目标目录（如已存在则报冲突）
		dir := "data/vuln"
		if vul.Info.FingerPrintName != "" {
			dir = filepath.Join(dir, vul.Info.FingerPrintName)
		}
		if err := os.MkdirAll(dir, 0755); err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"status": 1, "message": "创建目录失败: " + err.Error()})
			return
		}
		fileName := strings.ToUpper(vul.Info.CVEName) + ".yaml"
		filePath := filepath.Join(dir, fileName)
		if _, err := os.Stat(filePath); err == nil {
			c.JSON(http.StatusConflict, gin.H{"status": 1, "message": "该CVE编号的漏洞已存在"})
			return
		}
		data, err := yaml.Marshal(&vul)
		if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"status": 1, "message": "YAML序列化失败: " + err.Error()})
			return
		}
		if err := os.WriteFile(filePath, data, 0644); err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"status": 1, "message": "文件写入失败: " + err.Error()})
			return
		}

		// 6. 返回结果
		c.JSON(http.StatusOK, gin.H{"status": 0, "message": "创建漏洞库成功"})
	}
}

// 编辑漏洞处理函数
func HandleEditVulnerability(c *gin.Context) {
	// 1. 获取原CVE编号
	oldCVE := c.Param("cve")
	if oldCVE == "" {
		c.JSON(http.StatusBadRequest, gin.H{"status": 1, "message": "CVE编号不能为空"})
		return
	}
	if !isValidName(oldCVE) {
		c.JSON(http.StatusBadRequest, gin.H{"status": 1, "message": "原CVE编号非法"})
		return
	}

	type VulnUploadRequest struct {
		FileContent string `json:"file_content" binding:"required"`
	}
	var req VulnUploadRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"status": 1, "message": "参数解析失败"})
		return
	}
	// 2. 反序列化为vulstruct.VersionVul，校验CVE编号等必填字段
	var vul vulstruct.VersionVul
	if err := yaml.Unmarshal([]byte(req.FileContent), &vul); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"status": 1, "message": "YAML解析失败: " + err.Error()})
		return
	}
	if vul.Info.CVEName == "" {
		c.JSON(http.StatusBadRequest, gin.H{"status": 1, "message": "CVE编号不能为空"})
		return
	}
	if !isValidName(vul.Info.CVEName) {
		c.JSON(http.StatusBadRequest, gin.H{"status": 1, "message": "CVE编号非法"})
		return
	}
	if vul.Info.FingerPrintName != "" && !isValidName(vul.Info.FingerPrintName) {
		c.JSON(http.StatusBadRequest, gin.H{"status": 1, "message": "指纹分类名称非法"})
		return
	}

	// 3. 临时写入到校验用的临时文件
	tmpFile, cleanup, err := createTempFileWithContent("vuln-check-*", []byte(req.FileContent))
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"status": 1, "message": err.Error()})
		return
	}
	defer cleanup()

	// 4. 用vulstruct.NewAdvisoryEngine加载临时文件做完整业务校验
	_, err = vulstruct.ReadVersionVulSingFile(tmpFile)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"status": 1, "message": "漏洞内容校验失败: " + err.Error()})
		return
	}

	// 5. 在所有分类目录下查找原文件
	var oldPath string
	found := false
	baseDir := "data/vuln"
	_ = filepath.Walk(baseDir, func(path string, info os.FileInfo, err error) error {
		if err == nil && !info.IsDir() && strings.EqualFold(info.Name(), strings.ToUpper(oldCVE)+".yaml") {
			oldPath = path
			found = true
			return filepath.SkipDir // 找到就停止遍历
		}
		return nil
	})
	if !found {
		c.JSON(http.StatusNotFound, gin.H{"status": 1, "message": "原漏洞不存在"})
		return
	}

	// 6. 生成新文件路径
	newDir := "data/vuln"
	if vul.Info.FingerPrintName != "" {
		newDir = filepath.Join(newDir, vul.Info.FingerPrintName)
	}
	if err := os.MkdirAll(newDir, 0755); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"status": 1, "message": "创建目录失败: " + err.Error()})
		return
	}
	newPath := filepath.Join(newDir, strings.ToUpper(vul.Info.CVEName)+".yaml")

	// 7. 校验新文件名是否已存在（且不是原文件）
	if newPath != oldPath {
		if _, err := os.Stat(newPath); err == nil {
			c.JSON(http.StatusConflict, gin.H{"status": 1, "message": "新CVE编号的漏洞已存在"})
			return
		}
	}

	// 8. 删除原文件
	if err := os.Remove(oldPath); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"status": 1, "message": "删除原文件失败: " + err.Error()})
		return
	}

	// 9. 写入新内容（新文件名/新目录）
	data, err := yaml.Marshal(&vul)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"status": 1, "message": "YAML序列化失败: " + err.Error()})
		return
	}
	if err := os.WriteFile(newPath, data, 0644); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"status": 1, "message": "文件写入失败: " + err.Error()})
		return
	}

	c.JSON(http.StatusOK, gin.H{"status": 0, "message": "修改漏洞成功"})
}

// 批量删除漏洞处理函数
type BatchDeleteVulnRequest struct {
	CVEs []string `json:"cves"`
}

func HandleBatchDeleteVulnerabilities(c *gin.Context) {
	var req BatchDeleteVulnRequest
	if err := c.ShouldBindJSON(&req); err != nil || len(req.CVEs) == 0 {
		c.JSON(http.StatusBadRequest, gin.H{"status": 1, "message": "参数解析失败或CVE列表为空"})
		return
	}

	baseDir := "data/vuln"
	var notFound []string
	var failed []string

	for _, cve := range req.CVEs {
		if !isValidName(cve) {
			notFound = append(notFound, cve)
			continue
		}
		found := false
		_ = filepath.Walk(baseDir, func(path string, info os.FileInfo, err error) error {
			if err == nil && !info.IsDir() && strings.EqualFold(info.Name(), strings.ToUpper(cve)+".yaml") {
				// 找到就删除
				if err := os.Remove(path); err != nil {
					failed = append(failed, cve)
				}
				found = true
				return filepath.SkipDir
			}
			return nil
		})
		if !found {
			notFound = append(notFound, cve)
		}
	}

	if len(failed) > 0 {
		c.JSON(500, gin.H{"status": 1, "message": "部分删除失败", "failed": failed})
		return
	}
	if len(notFound) > 0 {
		c.JSON(404, gin.H{"status": 1, "message": "部分CVE未找到", "not_found": notFound})
		return
	}

	c.JSON(http.StatusOK, gin.H{"status": 0, "message": "批量删除成功"})
}
