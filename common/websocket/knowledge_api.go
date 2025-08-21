package websocket

import (
	"encoding/json"
	"fmt"
	"net/http"
	"os"
	"path/filepath"
	"regexp"
	"sort"
	"strconv"
	"strings"
	"time"

	"trpc.group/trpc-go/trpc-go/log"

	"github.com/Tencent/AI-Infra-Guard/common/fingerprints/parser"
	"github.com/Tencent/AI-Infra-Guard/pkg/vulstruct"
	"github.com/gin-gonic/gin"
	"gopkg.in/yaml.v3"
)

// 合法性校验
var validName = regexp.MustCompile(`^[a-zA-Z0-9\\._ -]+$`)

func isValidName(name string) bool {
	if strings.Contains(name, "..") {
		return false
	}
	return validName.MatchString(name)
}

// FingerprintWithTime 包含指纹数据和文件修改时间的结构体
type FingerprintWithTime struct {
	FingerPrint parser.FingerPrint
	ModTime     time.Time
}

// 评测集数据结构定义
type EvaluationDataItem struct {
	Prompt string `json:"prompt"`
}

type EvaluationDataset struct {
	Name           string               `json:"name"`
	Description    string               `json:"description"`
	DescriptionZh  string               `json:"description_zh,omitempty"`
	Author         string               `json:"author,omitempty"`
	Source         []string             `json:"source,omitempty"`
	Count          int                  `json:"count"`
	Default        bool                 `json:"default,omitempty"`
	Tags           []string             `json:"tags,omitempty"`
	Recommendation int                  `json:"recommendation,omitempty"`
	Language       string               `json:"language,omitempty"`
	Data           []EvaluationDataItem `json:"data"`
}

// 获取指纹列表，支持分页和名字模糊
func HandleListFingerprints(c *gin.Context) {
	// 1. 解析分页参数
	pageStr := c.DefaultQuery("page", "1")
	sizeStr := c.DefaultQuery("size", "20")
	page, _ := strconv.Atoi(pageStr)
	size, _ := strconv.Atoi(sizeStr)
	if page < 1 {
		page = 1
	}
	if size < 1 {
		size = 10
	}

	// 2. 获取查询参数
	nameQuery := strings.ToLower(c.DefaultQuery("q", ""))

	// 3. 读取 data/fingerprints/ 下所有分类和YAML文件
	var allFingerprintsWithTime []FingerprintWithTime
	root := "data/fingerprints"
	filepath.WalkDir(root, func(path string, d os.DirEntry, err error) error {
		if err != nil {
			return nil // 忽略错误
		}
		if !d.IsDir() && strings.HasSuffix(d.Name(), ".yaml") {
			content, _ := os.ReadFile(path)
			fp, err := parser.InitFingerPrintFromData(content)
			if err == nil && fp != nil {
				// 获取文件修改时间
				fileInfo, _ := d.Info()
				modTime := time.Time{}
				if fileInfo != nil {
					modTime = fileInfo.ModTime()
				}
				allFingerprintsWithTime = append(allFingerprintsWithTime, FingerprintWithTime{
					FingerPrint: *fp,
					ModTime:     modTime,
				})
			}
		}
		return nil
	})

	// 4. 条件过滤
	var filteredFingerprintsWithTime []FingerprintWithTime
	if nameQuery == "" {
		filteredFingerprintsWithTime = allFingerprintsWithTime
	} else {
		for _, fpWithTime := range allFingerprintsWithTime {
			fp := fpWithTime.FingerPrint
			if strings.Contains(strings.ToLower(fp.Info.Name), nameQuery) {
				filteredFingerprintsWithTime = append(filteredFingerprintsWithTime, fpWithTime)
				continue
			}
			if strings.Contains(strings.ToLower(fp.Info.Desc), nameQuery) {
				filteredFingerprintsWithTime = append(filteredFingerprintsWithTime, fpWithTime)
				continue
			}
			if strings.Contains(strings.ToLower(fp.Info.Author), nameQuery) {
				filteredFingerprintsWithTime = append(filteredFingerprintsWithTime, fpWithTime)
				continue
			}
		}
	}

	// 5. 复合排序：如果有Recommendation，先按Recommendation降序；否则按文件修改时间降序
	sort.Slice(filteredFingerprintsWithTime, func(i, j int) bool {
		fpI := filteredFingerprintsWithTime[i].FingerPrint
		fpJ := filteredFingerprintsWithTime[j].FingerPrint

		// 如果两个都有Recommendation（>0），按Recommendation降序
		if fpI.Info.Recommendation > 0 && fpJ.Info.Recommendation > 0 {
			if fpI.Info.Recommendation != fpJ.Info.Recommendation {
				return fpI.Info.Recommendation > fpJ.Info.Recommendation
			}
			// Recommendation相同时，按文件修改时间降序
			return filteredFingerprintsWithTime[i].ModTime.After(filteredFingerprintsWithTime[j].ModTime)
		}

		// 如果只有一个有Recommendation，有Recommendation的排前面
		if fpI.Info.Recommendation > 0 && fpJ.Info.Recommendation <= 0 {
			return true
		}
		if fpI.Info.Recommendation <= 0 && fpJ.Info.Recommendation > 0 {
			return false
		}

		// 如果两个都没有Recommendation，按文件修改时间降序
		return filteredFingerprintsWithTime[i].ModTime.After(filteredFingerprintsWithTime[j].ModTime)
	})

	// 提取指纹数据用于分页和返回
	var filteredFingerprints []parser.FingerPrint
	for _, fpWithTime := range filteredFingerprintsWithTime {
		filteredFingerprints = append(filteredFingerprints, fpWithTime.FingerPrint)
	}

	// 6. 分页
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

	// 7. 返回
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

	if _, err := parser.InitFingerPrintFromData([]byte(req.FileContent)); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"status": 1, "message": "指纹内容校验失败: " + err.Error()})
		return
	}

	if !isValidName(fp.Info.Name) {
		c.JSON(http.StatusBadRequest, gin.H{"status": 1, "message": "指纹名称非法"})
		return
	}
	yamlPath := filepath.Join("data/fingerprints", fp.Info.Name+".yaml")
	if _, err := os.Stat(yamlPath); err == nil {
		c.JSON(http.StatusConflict, gin.H{"status": 1, "message": "指纹已存在"})
		return
	}

	if err := os.WriteFile(yamlPath, []byte(req.FileContent), 0644); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"status": 1, "message": "文件写入失败: " + err.Error()})
		return
	}

	c.JSON(http.StatusOK, gin.H{"status": 0, "message": "创建指纹成功"})
}

// 批量删除指纹处理函数
type BatchDeleteRequest struct {
	Name []string `json:"name"`
}

func HandleDeleteFingerprint(c *gin.Context) {
	var req BatchDeleteRequest
	if err := c.ShouldBindJSON(&req); err != nil || len(req.Name) == 0 {
		c.JSON(http.StatusBadRequest, gin.H{"status": 1, "message": "参数错误", "data": nil})
		return
	}

	var deleted []string
	var notFound []string
	var invalid []string

	for _, name := range req.Name {
		// 使用已存在的合法性校验函数防止路径遍历攻击
		if !isValidName(name) {
			invalid = append(invalid, name)
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
	if len(invalid) > 0 {
		msg += "，部分指纹名称非法: " + strings.Join(invalid, ", ")
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
func HandleListVulnerabilities() gin.HandlerFunc {
	return func(c *gin.Context) {
		// 1. 解析分页和查询参数
		pageStr := c.DefaultQuery("page", "1")
		sizeStr := c.DefaultQuery("size", "20")
		query := strings.ToLower(c.DefaultQuery("q", ""))
		page, _ := strconv.Atoi(pageStr)
		size, _ := strconv.Atoi(sizeStr)
		if page < 1 {
			page = 1
		}
		if size < 1 {
			size = 10
		}

		engine := vulstruct.NewAdvisoryEngine()
		// load from directory
		dir := "data/vuln"
		err := engine.LoadFromDirectory(dir)
		if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"status": 1, "message": "加载漏洞库失败: " + err.Error()})
			return
		}
		filteredVuls := make([]vulstruct.VersionVul, 0)
		if query == "" {
			filteredVuls = engine.GetAll()
		} else {
			for _, vul := range engine.GetAll() {
				if strings.Contains(strings.ToLower(vul.Info.CVEName), query) {
					filteredVuls = append(filteredVuls, vul)
					continue
				}
				if strings.Contains(strings.ToLower(vul.Info.Summary), query) {
					filteredVuls = append(filteredVuls, vul)
					continue
				}
				if strings.Contains(strings.ToLower(vul.Info.FingerPrintName), query) {
					filteredVuls = append(filteredVuls, vul)
					continue
				}
				if strings.Contains(strings.ToLower(vul.Info.Details), query) {
					filteredVuls = append(filteredVuls, vul)
					continue
				}
				for _, ref := range vul.References {
					if strings.Contains(strings.ToLower(ref), query) {
						filteredVuls = append(filteredVuls, vul)
						break
					}
				}
			}
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

// 添加漏洞信息（带严格校验）
func HandleCreateVulnerability() gin.HandlerFunc {
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

		// 4. 用vulstruct.NewAdvisoryEngine加载临时文件做完整业务校验
		_, err := vulstruct.ReadVersionVul([]byte(req.FileContent))
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
	// 4. 用vulstruct.NewAdvisoryEngine加载临时文件做完整业务校验
	_, err := vulstruct.ReadVersionVul([]byte(req.FileContent))
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

// ================== 评测集管理接口 ==================

// 获取评测集列表，支持分页和名字模糊搜索
func HandleListEvaluations(c *gin.Context) {
	// 1. 解析分页参数
	pageStr := c.DefaultQuery("page", "1")
	sizeStr := c.DefaultQuery("size", "20")
	detail := c.DefaultQuery("detail", "false")
	page, _ := strconv.Atoi(pageStr)
	size, _ := strconv.Atoi(sizeStr)
	if page < 1 {
		page = 1
	}
	if size < 1 {
		size = 10
	}

	// 2. 获取查询参数
	nameQuery := strings.ToLower(c.DefaultQuery("q", ""))

	// 3. 读取 data/eval/ 下所有JSON文件
	var allEvaluations []EvaluationDataset
	root := "data/eval"
	filepath.WalkDir(root, func(path string, d os.DirEntry, err error) error {
		if err != nil {
			return nil // 忽略错误
		}
		if !d.IsDir() && strings.HasSuffix(d.Name(), ".json") {
			content, readErr := os.ReadFile(path)
			if readErr == nil {
				var eval EvaluationDataset
				err = json.Unmarshal(content, &eval)
				if err != nil {
					log.Error(path, err.Error())
					return err
				}
				// 转换为摘要格式（不包含data字段）
				if detail != "true" {
					eval.Data = nil
				}
				allEvaluations = append(allEvaluations, eval)
			}
		}
		return nil
	})

	// 4. 条件过滤
	var filteredEvaluations []EvaluationDataset
	if nameQuery == "" {
		filteredEvaluations = allEvaluations
	} else {
		for _, eval := range allEvaluations {
			if strings.Contains(strings.ToLower(eval.Name), nameQuery) {
				filteredEvaluations = append(filteredEvaluations, eval)
				continue
			}
			if strings.Contains(strings.ToLower(eval.Description), nameQuery) {
				filteredEvaluations = append(filteredEvaluations, eval)
				continue
			}
			if strings.Contains(strings.ToLower(eval.Author), nameQuery) {
				filteredEvaluations = append(filteredEvaluations, eval)
				continue
			}
			// 搜索标签
			for _, tag := range eval.Tags {
				if strings.Contains(strings.ToLower(tag), nameQuery) {
					filteredEvaluations = append(filteredEvaluations, eval)
					break
				}
			}
		}
	}

	// 5. 默认排序：按照Recommendation降序排列
	sort.Slice(filteredEvaluations, func(i, j int) bool {
		return filteredEvaluations[i].Recommendation > filteredEvaluations[j].Recommendation
	})

	// 6. 分页
	total := len(filteredEvaluations)
	start := (page - 1) * size
	end := start + size
	if start > total {
		start = total
	}
	if end > total {
		end = total
	}
	items := filteredEvaluations[start:end]

	// 7. 返回
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

// 获取评测集详情，返回包含data的完整信息
func HandleGetEvaluationDetail(c *gin.Context) {
	// 1. 获取评测集名称
	name := c.Param("name")
	if name == "" {
		c.JSON(http.StatusBadRequest, gin.H{"status": 1, "message": "评测集名称不能为空"})
		return
	}

	// 2. 验证名称合法性
	if !isValidName(name) {
		c.JSON(http.StatusBadRequest, gin.H{"status": 1, "message": "评测集名称非法"})
		return
	}

	// 3. 读取评测集文件
	var allEvaluations []EvaluationDataset
	root := "data/eval"
	filepath.WalkDir(root, func(path string, d os.DirEntry, err error) error {
		if err != nil {
			return nil // 忽略错误
		}
		if !d.IsDir() && strings.HasSuffix(d.Name(), ".json") {
			content, readErr := os.ReadFile(path)
			if readErr == nil {
				var eval EvaluationDataset
				if parseErr := json.Unmarshal(content, &eval); parseErr == nil {
					allEvaluations = append(allEvaluations, eval)
				}
			}
		}
		return nil
	})

	for _, eval := range allEvaluations {
		if eval.Name == name {
			c.JSON(http.StatusOK, gin.H{
				"status":  0,
				"message": "success",
				"data":    eval,
			})
			return
		}
	}

	// 5. 返回完整的评测集信息（包含data字段）
	c.JSON(http.StatusOK, gin.H{
		"status":  0,
		"message": "success",
		"data":    nil,
	})
}

// 创建评测集
func HandleCreateEvaluation(c *gin.Context) {
	// 1. 解析请求体，获取file_content字段
	type EvaluationUploadRequest struct {
		FileContent string `json:"file_content" binding:"required"`
	}
	var req EvaluationUploadRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"status": 1, "message": "参数解析失败"})
		return
	}

	// 2. 解析JSON为EvaluationDataset结构体
	var eval EvaluationDataset
	if err := json.Unmarshal([]byte(req.FileContent), &eval); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"status": 1, "message": "JSON解析失败: " + err.Error()})
		return
	}
	if eval.Name == "" {
		c.JSON(http.StatusBadRequest, gin.H{"status": 1, "message": "评测集名称不能为空"})
		return
	}

	// 3. 验证数据完整性
	if len(eval.Data) == 0 {
		c.JSON(http.StatusBadRequest, gin.H{"status": 1, "message": "评测数据不能为空"})
		return
	}

	// 更新count字段为实际数据条数
	eval.Count = len(eval.Data)

	// 验证数据项
	for i, item := range eval.Data {
		if item.Prompt == "" {
			c.JSON(http.StatusBadRequest, gin.H{"status": 1, "message": fmt.Sprintf("第%d条数据的prompt不能为空", i+1)})
			return
		}
	}

	// 4. 检查评测集名称是否已存在
	if !isValidName(eval.Name) {
		c.JSON(http.StatusBadRequest, gin.H{"status": 1, "message": "评测集名称非法，只允许字母、数字、下划线和横线"})
		return
	}
	jsonPath := filepath.Join("data/eval", eval.Name+".json")
	if _, err := os.Stat(jsonPath); err == nil {
		c.JSON(http.StatusConflict, gin.H{"status": 1, "message": "评测集已存在"})
		return
	}

	// 5. 序列化并写入JSON文件
	updatedContent, err := json.MarshalIndent(eval, "", "  ")
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"status": 1, "message": "JSON序列化失败: " + err.Error()})
		return
	}

	if err := os.WriteFile(jsonPath, updatedContent, 0644); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"status": 1, "message": "文件写入失败: " + err.Error()})
		return
	}

	// 6. 返回精简响应
	c.JSON(http.StatusOK, gin.H{"status": 0, "message": "创建评测集成功"})
}

// 编辑评测集处理函数
func HandleEditEvaluation(c *gin.Context) {
	// 1. 获取原评测集名称
	oldName := c.Param("name")
	if oldName == "" {
		c.JSON(http.StatusBadRequest, gin.H{"status": 1, "message": "评测集名称不能为空"})
		return
	}

	type EvaluationUploadRequest struct {
		FileContent string `json:"file_content" binding:"required"`
	}
	var req EvaluationUploadRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"status": 1, "message": "参数解析失败"})
		return
	}

	// 2. 解析JSON为EvaluationDataset结构体
	var eval EvaluationDataset
	if err := json.Unmarshal([]byte(req.FileContent), &eval); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"status": 1, "message": "JSON解析失败: " + err.Error()})
		return
	}
	if eval.Name == "" {
		c.JSON(http.StatusBadRequest, gin.H{"status": 1, "message": "评测集名称不能为空"})
		return
	}

	// 验证数据完整性
	if len(eval.Data) == 0 {
		c.JSON(http.StatusBadRequest, gin.H{"status": 1, "message": "评测数据不能为空"})
		return
	}

	// 更新count字段为实际数据条数
	eval.Count = len(eval.Data)

	// 验证数据项
	for i, item := range eval.Data {
		if item.Prompt == "" {
			c.JSON(http.StatusBadRequest, gin.H{"status": 1, "message": fmt.Sprintf("第%d条数据的prompt不能为空", i+1)})
			return
		}
	}

	// 3. 校验原文件是否存在
	if !isValidName(oldName) || !isValidName(eval.Name) {
		c.JSON(http.StatusBadRequest, gin.H{"status": 1, "message": "评测集名称非法，只允许字母、数字、下划线和横线"})
		return
	}
	oldPath := filepath.Join("data/eval", oldName+".json")
	if _, err := os.Stat(oldPath); os.IsNotExist(err) {
		c.JSON(http.StatusNotFound, gin.H{"status": 1, "message": "原评测集不存在"})
		return
	}
	newPath := filepath.Join("data/eval", eval.Name+".json")

	// 4. 校验新文件名是否已存在（且不是原文件）
	if newPath != oldPath {
		if _, err := os.Stat(newPath); err == nil {
			c.JSON(http.StatusConflict, gin.H{"status": 1, "message": "新评测集名称已存在"})
			return
		}
	}

	// 5. 如果新旧文件名不同，删除原文件
	if oldName != eval.Name {
		_ = os.Remove(oldPath) // 删除老文件
	}

	// 6. 序列化并写入新内容（新文件名）
	updatedContent, err := json.MarshalIndent(eval, "", "  ")
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"status": 1, "message": "JSON序列化失败: " + err.Error()})
		return
	}

	if err := os.WriteFile(newPath, updatedContent, 0644); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"status": 1, "message": "文件写入失败: " + err.Error()})
		return
	}

	c.JSON(http.StatusOK, gin.H{"status": 0, "message": "修改评测集成功"})
}

// 批量删除评测集处理函数
type BatchDeleteEvaluationRequest struct {
	Names []string `json:"names"`
}

func HandleDeleteEvaluation(c *gin.Context) {
	var req BatchDeleteEvaluationRequest
	if err := c.ShouldBindJSON(&req); err != nil || len(req.Names) == 0 {
		c.JSON(http.StatusBadRequest, gin.H{"status": 1, "message": "参数错误", "data": nil})
		return
	}

	for _, name := range req.Names {
		// 使用已存在的合法性校验函数防止路径遍历攻击
		if !isValidName(name) {
			c.JSON(http.StatusBadRequest, gin.H{"status": 1, "message": "评测集名称非法，只允许字母、数字、下划线和横线"})
			return
		}
		jsonPath := filepath.Join("data/eval", name+".json")
		if _, err := os.Stat(jsonPath); os.IsNotExist(err) {
			c.JSON(http.StatusBadRequest, gin.H{"status": 1, "message": "评测集不存在"})
			return
		}
		if err := os.Remove(jsonPath); err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"status": 1, "message": "删除失败: " + err.Error()})
			return
		}
	}
	c.JSON(http.StatusOK, gin.H{
		"status":  0,
		"message": "ok",
	})
}
