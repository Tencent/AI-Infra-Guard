package agent

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"math"
	"mime/multipart"
	"net/http"
	"os"
	"path/filepath"
	"strings"

	"github.com/Tencent/AI-Infra-Guard/internal/mcp"
)

// DownloadFile 下载文件
func DownloadFile(server, sessionId, uri, path string) error {
	// 创建 HTTP 客户端
	client := &http.Client{}

	data := map[string]string{
		"fileUrl": uri,
	}
	jsonData, err := json.Marshal(data)
	// 发送 POST 请求
	resp, err := client.Post(fmt.Sprintf("http://%s/api/v1/app/tasks/%s/downloadFile", server, sessionId), "application/json", io.NopCloser(bytes.NewBuffer(jsonData)))
	if err != nil {
		return err
	}
	defer resp.Body.Close()

	// 检查 HTTP 状态码
	if resp.StatusCode != http.StatusOK {
		dd, _ := io.ReadAll(resp.Body)
		return fmt.Errorf("下载失败，HTTP 状态码：%d content:%s", resp.StatusCode, string(dd))
	}

	// 创建文件
	file, err := os.Create(path)
	if err != nil {
		return err
	}
	defer file.Close()

	// 将响应体复制到文件
	_, err = io.Copy(file, resp.Body)
	if err != nil {
		return err
	}

	return nil
}

// UploadFileResponse 上传文件响应结构
type UploadFileResponse struct {
	Status  int    `json:"status"`
	Message string `json:"message"`
	Data    struct {
		FileUrl  string `json:"fileUrl"`
		Filename string `json:"filename"`
	} `json:"data"`
}

// UploadFile 上传文件到服务器
func UploadFile(server, filePath string) (*UploadFileResponse, error) {
	// 打开文件
	file, err := os.Open(filePath)
	if err != nil {
		return nil, fmt.Errorf("无法打开文件: %v", err)
	}
	defer file.Close()

	// 创建 multipart writer
	var requestBody bytes.Buffer
	writer := multipart.NewWriter(&requestBody)

	// 创建文件字段
	part, err := writer.CreateFormFile("file", filepath.Base(filePath))
	if err != nil {
		return nil, fmt.Errorf("创建文件字段失败: %v", err)
	}

	// 将文件内容复制到 part
	_, err = io.Copy(part, file)
	if err != nil {
		return nil, fmt.Errorf("复制文件内容失败: %v", err)
	}

	// 关闭 writer
	err = writer.Close()
	if err != nil {
		return nil, fmt.Errorf("关闭 writer 失败: %v", err)
	}

	// 创建 HTTP 请求
	req, err := http.NewRequest("POST", fmt.Sprintf("http://%s/api/v1/app/tasks/uploadFile", server), &requestBody)
	if err != nil {
		return nil, fmt.Errorf("创建请求失败: %v", err)
	}

	// 设置 Content-Type
	req.Header.Set("Content-Type", writer.FormDataContentType())

	// 发送请求
	client := &http.Client{}
	resp, err := client.Do(req)
	if err != nil {
		return nil, fmt.Errorf("发送请求失败: %v", err)
	}
	defer resp.Body.Close()

	// 读取响应体
	respBody, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, fmt.Errorf("读取响应失败: %v", err)
	}

	// 检查 HTTP 状态码
	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("上传失败，HTTP 状态码：%d content:%s", resp.StatusCode, string(respBody))
	}

	// 解析响应 JSON
	var uploadResp UploadFileResponse
	err = json.Unmarshal(respBody, &uploadResp)
	if err != nil {
		return nil, fmt.Errorf("解析响应 JSON 失败: %v", err)
	}

	return &uploadResp, nil
}

func GetEvaluationsDetail(server, name string) ([]byte, error) {
	path := "/api/v1/knowledge/evaluations/" + name
	// 创建 HTTP 请求
	req, err := http.NewRequest("GET", fmt.Sprintf("http://%s%s", server, path), nil)
	if err != nil {
		return nil, fmt.Errorf("创建请求失败: %v", err)
	}

	// 发送请求
	client := &http.Client{}
	resp, err := client.Do(req)
	if err != nil {
		return nil, fmt.Errorf("发送请求失败: %v", err)
	}
	defer resp.Body.Close()

	// 读取响应体
	respBody, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, fmt.Errorf("读取响应失败: %v", err)
	}

	// 检查 HTTP 状态码
	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("上传失败，HTTP 状态码：%d content:%s", resp.StatusCode, string(respBody))
	}

	var msg struct {
		Data json.RawMessage `json:"data"`
	}
	err = json.Unmarshal(respBody, &msg)
	if err != nil {
		return nil, fmt.Errorf("解析响应 JSON 失败: %v", err)
	}
	return msg.Data, nil
}

// CalcMcpScore 计算安全分数
func CalcMcpScore(issues []mcp.Issue) int {
	var total, high, middle, low int = 0, 0, 0, 0
	total = len(issues)
	for _, item := range issues {
		item.RiskType = strings.ToLower(item.RiskType)
		if item.RiskType == "high" || item.RiskType == "critical" || item.RiskType == "高危" || item.RiskType == "严重" {
			high++
		} else if item.RiskType == "medium" || item.RiskType == "中危" {
			middle++
		} else {
			low++
		}
	}
	if total == 0 {
		return 100
	}
	// 计算加权风险比例
	weightedRisk := (float64(high)/float64(total))*0.7 +
		(float64(middle)/float64(total))*0.5 +
		(float64(low)/float64(total))*0.3

	// 计算安全评分（百分制）
	safetyScore := 100 - weightedRisk*100

	// 确保评分在0-100范围内
	if safetyScore < 0 {
		safetyScore = 0
	}
	if safetyScore >= 100 {
		safetyScore = 100
	}
	return int(math.Round(safetyScore))
}
