// Package utils 工具集合
package utils

import (
	"archive/tar"
	"archive/zip"
	"bufio"
	"bytes"
	"compress/gzip"
	"context"
	"crypto/sha256"
	"encoding/base64"
	"fmt"
	"github.com/Tencent/AI-Infra-Guard/internal/gologger"
	"io"
	"net"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"strconv"
	"strings"
	"time"

	"github.com/spaolacci/murmur3"
)

// Duration2String 将时间段转换为可读的字符串格式
// 如果时间超过60秒则返回分钟，否则返回秒
func Duration2String(t time.Duration) string {
	sceond := t.Seconds()
	if sceond >= 60 {
		return fmt.Sprintf("%.2f min", t.Minutes())
	} else {
		return fmt.Sprintf("%.2f s", sceond)
	}
}

// InsertInto 在字符串中每隔指定间隔插入分隔符
// s: 源字符串
// interval: 插入间隔
// sep: 分隔符
func InsertInto(s string, interval int, sep rune) string {
	var buffer bytes.Buffer
	before := interval - 1
	last := len(s) - 1
	for i, char := range s {
		buffer.WriteRune(char)
		if i%interval == before && i != last {
			buffer.WriteRune(sep)
		}
	}
	buffer.WriteRune(sep)
	return buffer.String()
}

// FaviconHash 计算网站图标的哈希值
// 将数据进行base64编码后使用murmur3哈希算法计算
func FaviconHash(data []byte) int32 {
	stdBase64 := base64.StdEncoding.EncodeToString(data)
	stdBase64 = InsertInto(stdBase64, 76, '\n')
	hasher := murmur3.New32WithSeed(0)
	hasher.Write([]byte(stdBase64))
	return int32(hasher.Sum32())
}

// BodyHash 计算响应内容的 SHA256 哈希值
func BodyHash(data []byte) string {
	sum := sha256.Sum256(data)
	return fmt.Sprintf("%x", sum)
}

// ScanDir 递归扫描目录，返回所有文件的完整路径
// path: 要扫描的目录路径
// 返回文件路径列表和可能的错误
func ScanDir(path string) ([]string, error) {
	files := make([]string, 0)
	dir, err := os.ReadDir(path)
	if err != nil {
		return nil, err
	}
	for _, fi := range dir {
		if fi.IsDir() {
			newDir, err := ScanDir(filepath.Join(path, fi.Name()))
			if err != nil {
				return files, err
			}
			files = append(files, newDir...)
		} else {
			files = append(files, filepath.Join(path, fi.Name()))
		}
	}
	return files, nil
}

// IsCIDR 检查给定的字符串是否为有效的CIDR格式
func IsCIDR(cidr string) bool {
	_, _, err := net.ParseCIDR(cidr)
	return err == nil
}

// IsFileExists 检查文件是否存在
// path: 文件路径
// 返回布尔值表示文件是否存在
func IsFileExists(path string) bool {
	_, err := os.Stat(path)
	if err != nil {
		if os.IsExist(err) {
			return true
		}
		return false
	}
	return true
}

// IsDir 判断给定路径是否为目录
// path: 待检查的路径
// 返回布尔值表示是否为目录
func IsDir(path string) bool {
	s, err := os.Stat(path)
	if err != nil {
		return false
	}
	return s.IsDir()
}

// TrimProtocol 移除URL中的HTTP/HTTPS协议前缀
// targetURL: 目标URL
// 返回去除协议前缀后的URL
func TrimProtocol(targetURL string) string {
	URL := strings.TrimSpace(targetURL)
	if strings.HasPrefix(strings.ToLower(URL), "http://") || strings.HasPrefix(strings.ToLower(URL), "https://") {
		URL = URL[strings.Index(URL, "//")+2:]
	}
	URL = strings.TrimRight(URL, "/")
	return URL
}

// CompareVersions 比较两个版本号字符串
// version1, version2: 待比较的版本号
// 返回值: 1 表示 version1 大于 version2
//
//	-1 表示 version1 小于 version2
//	 0 表示两个版本号相等
func CompareVersions(version1, version2 string) int {
	v1Parts := strings.Split(version1, ".")
	v2Parts := strings.Split(version2, ".")

	// Determine the max length to iterate over
	maxLen := len(v1Parts)
	if len(v2Parts) > maxLen {
		maxLen = len(v2Parts)
	}

	for i := 0; i < maxLen; i++ {
		var num1, num2 int

		if i < len(v1Parts) {
			num1, _ = strconv.Atoi(v1Parts[i])
		}

		if i < len(v2Parts) {
			num2, _ = strconv.Atoi(v2Parts[i])
		}

		if num1 > num2 {
			return 1
		} else if num1 < num2 {
			return -1
		}
	}

	return 0
}

// GetMiddleText 获取两个字符串之间的文本内容
// left: 左边界字符串
// right: 右边界字符串
// html: 源文本
// 返回左右边界之间的文本，如果未找到则返回空字符串
func GetMiddleText(left, right, html string) string {
	start := strings.Index(html, left)
	if start == -1 {
		return "" // 如果找不到 left，返回空字符串
	}
	start += len(left)

	end := strings.Index(html[start:], right)
	if end == -1 {
		return "" // 如果找不到 right，返回空字符串
	}
	end += start

	return html[start:end]
}

// PortInfo 存储端口和地址信息
type PortInfo struct {
	Port    int
	Address string
}

// GetLocalOpenPorts 获取本地开放的端口及其地址信息
func GetLocalOpenPorts() ([]PortInfo, error) {
	var portInfos []PortInfo
	switch runtime.GOOS {
	case "windows":
		cmd := exec.Command("netstat", "-an")
		output, err := cmd.Output()
		if err != nil {
			return nil, fmt.Errorf("执行netstat命令失败: %v", err)
		}

		scanner := bufio.NewScanner(strings.NewReader(string(output)))
		for scanner.Scan() {
			line := scanner.Text()
			if strings.Contains(line, "LISTENING") {
				parts := strings.Fields(line)
				if len(parts) >= 2 {
					addrPort := strings.Split(parts[1], ":")
					if len(addrPort) == 2 {
						port, err := strconv.Atoi(addrPort[1])
						if err == nil {
							addr := addrPort[0]
							portInfos = append(portInfos, PortInfo{
								Port:    port,
								Address: addr,
							})
						}
					}
				}
			}
		}

	case "darwin", "linux":
		cmd := exec.Command("lsof", "-i", "-P", "-n")
		output, err := cmd.Output()
		if err != nil {
			return nil, fmt.Errorf("执行lsof命令失败: %v", err)
		}

		scanner := bufio.NewScanner(strings.NewReader(string(output)))
		for scanner.Scan() {
			line := scanner.Text()
			if strings.Contains(line, "LISTEN") {
				parts := strings.Fields(line)
				for _, part := range parts {
					if strings.Contains(part, ":") {
						addrPort := strings.Split(part, ":")
						if len(addrPort) == 2 {
							port, err := strconv.Atoi(addrPort[1])
							if err == nil {
								addr := addrPort[0]
								if addr == "*" || addr == "0.0.0.0" {
									addr = "0.0.0.0"
								} else if addr == "127.0.0.1" || addr == "localhost" {
									addr = "127.0.0.1"
								}
								portInfos = append(portInfos, PortInfo{
									Port:    port,
									Address: addr,
								})
							}
						}
					}
				}
			}
		}

	default:
		return nil, fmt.Errorf("不支持的操作系统: %s", runtime.GOOS)
	}

	// 去重
	seen := make(map[string]bool)
	var result []PortInfo
	for _, info := range portInfos {
		key := fmt.Sprintf("%s:%d", info.Address, info.Port)
		if !seen[key] {
			seen[key] = true
			result = append(result, info)
		}
	}

	return result, nil
}

// ExtractZipFile 解压ZIP文件
func ExtractZipFile(zipFile string, destPath string) error {
	// 打开ZIP文件
	reader, err := zip.OpenReader(zipFile)
	if err != nil {
		return fmt.Errorf("打开ZIP文件失败: %v", err)
	}
	defer reader.Close()

	// 确保目标目录存在
	if err := os.MkdirAll(destPath, 0755); err != nil {
		return fmt.Errorf("创建目标目录失败: %v", err)
	}

	// 解压文件
	for _, file := range reader.File {
		// 检查文件路径是否安全
		filePath := filepath.Join(destPath, file.Name)
		if !strings.HasPrefix(filePath, filepath.Clean(destPath)+string(os.PathSeparator)) {
			gologger.Errorln(fmt.Sprintf("不安全的路径: %s", file.Name))
			continue
		}

		// 创建目录
		if file.FileInfo().IsDir() {
			if err := os.MkdirAll(filePath, 0755); err != nil {
				return fmt.Errorf("创建目录失败: %v", err)
			}
			continue
		}

		// 确保文件的父目录存在
		if err := os.MkdirAll(filepath.Dir(filePath), 0755); err != nil {
			return fmt.Errorf("创建父目录失败: %v", err)
		}

		// 创建文件
		outFile, err := os.Create(filePath)
		if err != nil {
			return fmt.Errorf("创建文件失败: %v", err)
		}
		defer outFile.Close()

		// 打开文件内容
		rc, err := file.Open()
		if err != nil {
			return fmt.Errorf("打开压缩文件内容失败: %v", err)
		}
		defer rc.Close()

		// 复制内容
		if _, err := io.Copy(outFile, rc); err != nil {
			return fmt.Errorf("复制文件内容失败: %v", err)
		}
	}

	return nil
}

// ExtractTGZ 文件解压
func ExtractTGZ(src, dest string) error {
	// 打开 .tgz 文件
	file, err := os.Open(src)
	if err != nil {
		return err
	}
	defer file.Close()

	// 创建 gzip Reader
	gzr, err := gzip.NewReader(file)
	if err != nil {
		return err
	}
	defer gzr.Close()

	// 创建 tar Reader
	tr := tar.NewReader(gzr)

	// 遍历 tar 文件中的每个条目
	for {
		header, err := tr.Next()
		if err == io.EOF {
			break // 读取完毕
		}
		if err != nil {
			return err
		}

		// 安全处理目标路径，防止路径穿越攻击
		targetPath, err := safePath(dest, header.Name)
		if err != nil {
			return err
		}

		// 根据文件类型处理
		switch header.Typeflag {
		case tar.TypeDir: // 目录
			if err := os.MkdirAll(targetPath, 0755); err != nil {
				return err
			}
		case tar.TypeReg: // 普通文件
			if err := writeFile(targetPath, tr, header.Mode); err != nil {
				return err
			}
		// 可选：处理符号链接等其他类型
		default:
			fmt.Printf("未处理类型: %v in %s\n", header.Typeflag, header.Name)
		}
	}
	return nil
}

// 安全路径检查，防止路径穿越
func safePath(dest, name string) (string, error) {
	targetPath := filepath.Join(dest, name)
	cleanedPath := filepath.Clean(targetPath)
	dest = filepath.Clean(dest)

	// 检查目标路径是否在目标目录下
	if !strings.HasPrefix(cleanedPath, dest+string(os.PathSeparator)) && cleanedPath != dest {
		return "", fmt.Errorf("非法路径: %s", name)
	}
	return targetPath, nil
}

// 写入文件内容
func writeFile(path string, r io.Reader, mode int64) error {
	// 确保目录存在
	if err := os.MkdirAll(filepath.Dir(path), 0755); err != nil {
		return err
	}

	// 创建文件并设置权限
	file, err := os.OpenFile(path, os.O_CREATE|os.O_TRUNC|os.O_WRONLY, os.FileMode(mode))
	if err != nil {
		return err
	}
	defer file.Close()

	// 复制内容
	if _, err := io.Copy(file, r); err != nil {
		return err
	}
	return nil
}

// GitClone 克隆Git仓库
func GitClone(repoURL, targetDir string, timeout time.Duration) error {
	var err error
	for i := 0; i < 3; i++ {
		err = func() error {
			ctx := context.Background()
			ctx, cancel := context.WithTimeout(ctx, timeout)
			defer cancel()
			cmd := exec.CommandContext(ctx, "git", "clone", "--", repoURL, targetDir)
			done := make(chan error)
			go func() {
				_, err := cmd.CombinedOutput()
				done <- err
			}()

			select {
			case <-ctx.Done():
				_ = cmd.Process.Kill()
				return fmt.Errorf("操作超时")
			case err = <-done:
				return err
			}
		}()
		if err == nil {
			return nil
		}
	}
	return err
}

func RunCmd(dir, name string, arg []string, callback func(line string)) error {
	// 命令行执行,stdio读取
	cmd := exec.Command(name, arg...)
	cmd.Dir = dir
	cmd.Env = os.Environ()
	// 获取命令行
	cmdStr := name + " " + strings.Join(arg, " ")
	gologger.Infof("开始执行命令: %s", cmdStr)
	// 使用管道获取标准输出
	stdout, err := cmd.StdoutPipe()
	if err != nil {
		return err
	}
	cmd.Stderr = cmd.Stdout // 将错误输出合并到标准输出
	// 启动扫描器goroutine
	scanner := bufio.NewScanner(stdout)
	done := make(chan struct{}) // 用于等待读取完成
	go func() {
		defer close(done)
		for scanner.Scan() {
			line := scanner.Text()
			callback(line)
		}
	}()
	// 启动命令
	if err = cmd.Start(); err != nil {
		return err
	}
	// 等待命令执行完成
	if err = cmd.Wait(); err != nil {
		return err
	}
	// 确保读取完所有输出
	<-done
	return nil
}

func IsHostname(hostname string) bool {
	ips := strings.Split(hostname, ":")
	if len(ips) != 2 {
		return false
	}
	p := net.ParseIP(strings.TrimSpace(ips[0]))
	if p == nil {
		return false
	}
	return true
}
