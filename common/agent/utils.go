package agent

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os"
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
	contentType := resp.Header.Get("Content-Type")

	if contentType == "application/json" {
		return fmt.Errorf("下载失败，文件类型错误：%s", contentType)
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
