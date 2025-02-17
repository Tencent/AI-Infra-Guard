// Package httpx http response  
package httpx  

import (  
	"fmt"  
	"net/http"  
	"strings"  

	"github.com/projectdiscovery/rawhttp/client"  
)  

// Response contains the response to a server  
type Response struct {  
	*http.Response  
	StatusCode    int  
	Headers       map[string][]string  
	Data          []byte  
	DataStr       string  
	ContentLength int  
	Title         string  
	// Uncomment the following line if you need to handle concurrency  
	// mu            sync.RWMutex  
}  

// NewResponse 创建并初始化一个新的 Response 对象  
func NewResponse(httpResp *http.Response, data []byte) *Response {  
	if httpResp == nil {  
		return nil  
	}  

	// 深拷贝 Headers  
	headersCopy := make(map[string][]string)  
	for k, v := range httpResp.Header {  
		headersCopy[k] = append([]string(nil), v...)  
	}  

	// 将 data 转换为字符串  
	dataStr := string(data)  

	// 提取标题（如果需要）  
	title := extractTitle(dataStr)  

	return &Response{  
		Response:      httpResp,  
		StatusCode:    httpResp.StatusCode,  
		Headers:       headersCopy,  
		Data:          data,  
		DataStr:       dataStr,  
		ContentLength: int(httpResp.ContentLength),  
		Title:         title,  
	}  
}  

// extractTitle 从响应数据中提取标题（示例实现，可以根据实际情况调整）  
func extractTitle(data string) string {  
	start := strings.Index(data, "<title>")  
	end := strings.Index(data, "</title>")  
	if start != -1 && end != -1 && start < end {  
		return data[start+7 : end]  
	}  
	return ""  
}  

// GetHeaderRaw 获取 header 的原始文本表示  
func (r *Response) GetHeaderRaw() string {  
	if r == nil || r.Headers == nil {  
		return ""  
	}  

	var headerStr strings.Builder  
	for h, v := range r.Headers {  
		headerStr.WriteString(fmt.Sprintf("%s: %s\n", h, strings.Join(v, " ")))  
	}  
	return headerStr.String()  
}  

// GetHeader 获取指定名称的 header 值，多个值以空格分隔  
func (r *Response) GetHeader(name string) string {  
	if r == nil || r.Headers == nil {  
		return ""  
	}  
	v, ok := r.Headers[name]  
	if ok {  
		return strings.Join(v, " ")  
	}  
	return ""  
}  

// GetHeaderPart 获取指定 header 的部分值，通过分隔符分割后返回第一个部分  
func (r *Response) GetHeaderPart(name, sep string) string {  
	if r == nil || r.Headers == nil {  
		return ""  
	}  
	v, ok := r.Headers[name]  
	if ok && len(v) > 0 {  
		tokens := strings.Split(strings.Join(v, " "), sep)  
		if len(tokens) > 0 {  
			return tokens[0]  
		}  
	}  
	return ""  
}  

// DumpResponse 导出完整的响应内容，包括状态行、头部和主体  
func (r *Response) DumpResponse() string {  
	if r == nil {  
		return ""  
	}  

	statusLine := fmt.Sprintf("%s %s", r.Proto, r.Status)  
	headers := r.GetHeaderRaw()  
	body := r.DataStr  

	return statusLine + client.NewLine + headers + client.NewLine + body  
}
