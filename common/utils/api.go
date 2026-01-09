package utils

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"mime/multipart"
	"net/http"
	"os"
	"path/filepath"

	"github.com/Tencent/AI-Infra-Guard/common/fingerprints/parser"
	"github.com/Tencent/AI-Infra-Guard/internal/gologger"
)

// DownloadFile 下载文件
func DownloadFile(server, sessionId, uri, path string) error {
	// 创建 HTTP 客户端
	client := &http.Client{}

	data := map[string]string{
		"fileUrl": uri,
	}
	jsonData, err := json.Marshal(data)
	// 创建请求并添加 header
	req, err := http.NewRequest("POST", fmt.Sprintf("http://%s/api/v1/app/tasks/%s/downloadFile", server, sessionId), io.NopCloser(bytes.NewBuffer(jsonData)))
	if err != nil {
		return err
	}
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("X-APIKey", "zhuque")

	// 发送 POST 请求
	resp, err := client.Do(req)
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
	req.Header.Set("X-APIKey", "zhuque")

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
	req.Header.Set("X-APIKey", "zhuque")

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

func LoadRemoteFingerPrints(hostname string) ([]parser.FingerPrint, error) {
	type msg struct {
		Data struct {
			FingerPrints []json.RawMessage `json:"items"`
			Total        int               `json:"total"`
		} `json:"data"`
		Message string `json:"message"`
	}
	// 创建请求并添加 header
	req, err := http.NewRequest("GET", fmt.Sprintf("http://%s/api/v1/knowledge/fingerprints?page=1&size=9999", hostname), nil)
	if err != nil {
		return nil, err
	}
	req.Header.Set("X-APIKey", "zhuque")

	// 发送请求
	client := &http.Client{}
	resp, err := client.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("http status code: %d", resp.StatusCode)
	}
	data, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, err
	}
	var m msg
	if err := json.Unmarshal(data, &m); err != nil {
		return nil, err
	}
	fps := make([]parser.FingerPrint, 0)
	for _, raw := range m.Data.FingerPrints {
		fp, err := parser.InitFingerPrintFromData(raw)
		if err != nil {
			gologger.WithError(err).Fatalf("无法解析指纹模板:%s", string(raw))
			continue
		}
		fps = append(fps, *fp)
	}
	return fps, nil
}

func LoadRemoteVulStruct(api string) ([]json.RawMessage, error) {
	type msg struct {
		Data struct {
			Vuls  []json.RawMessage `json:"items"`
			Total int               `json:"total"`
		} `json:"data"`
		Message string `json:"message"`
	}
	// 创建请求并添加 header
	req, err := http.NewRequest("GET", api, nil)
	if err != nil {
		return nil, err
	}
	req.Header.Set("X-APIKey", "zhuque")

	// 发送请求
	client := &http.Client{}
	resp, err := client.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("http status code: %d", resp.StatusCode)
	}
	data, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, err
	}
	var m msg
	if err := json.Unmarshal(data, &m); err != nil {
		return nil, err
	}
	return m.Data.Vuls, nil
}
