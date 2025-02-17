package preload

import (
	"context"
	"github.com/Tencent/AI-Infra-Guard/common/fingerprints/parser"
	"github.com/Tencent/AI-Infra-Guard/internal/gologger"
	"github.com/Tencent/AI-Infra-Guard/pkg/httpx"
	"regexp"
	"strconv"
	"strings"
	"sync"
	"time"
)

// FingerPrintFunc 改进的指纹识别接口
type FingerPrintFunc interface {
	// 增加 context 支持异步取消
	Match(ctx context.Context, httpx *httpx.HTTPX, uri string) bool
	GetVersion(ctx context.Context, httpx *httpx.HTTPX, uri string) (string, error)
	Name() string
}

type FpResult struct {
	Name    string `json:"name"`
	Version string `json:"version,omitempty"`
	Type    string `json:"type,omitempty"`
}

type Runner struct {
	hp      *httpx.HTTPX
	fps     []parser.FingerPrint
	timeout time.Duration // 添加超时控制
}

// New 创建增强的Runner实例
func New(hp *httpx.HTTPX, fps parser.FingerPrints) *Runner {
	return &Runner{
		hp:      hp,
		fps:     fps,
		timeout: 30 * time.Second, // 默认30秒超时
	}
}

// safeHTTPGet 安全的HTTP请求封装
func (r *Runner) safeHTTPGet(ctx context.Context, uri string) (*httpx.Response, error) {
	resp, err := r.hp.Get(uri, nil)
	if err != nil {
		return nil, err
	}
	if resp == nil {
		return nil, fmt.Errorf("empty response received")
	}
	// 确保响应体会被关闭
	if resp.Body != nil {
		defer resp.Body.Close()
	}
	return resp, nil
}

// RunFpReqs 改进的指纹识别执行器
func (r *Runner) RunFpReqs(uri string, concurrent int, faviconHash int32) []FpResult {
	ctx, cancel := context.WithTimeout(context.Background(), r.timeout)
	defer cancel()

	var results struct {
		sync.Mutex
		items []FpResult
	}

	uri = strings.TrimRight(uri, "/")

	// 安全获取索引页面
	indexCache, err := r.safeHTTPGet(ctx, uri+"/")
	if err != nil {
		gologger.WithError(err).Debugln("获取索引页面失败")
		indexCache = nil // 显式置空
	}

	// 使用 errgroup 进行并发控制
	g, ctx := errgroup.WithContext(ctx)
	g.SetLimit(concurrent) // 限制并发数

	// 处理内置指纹
	for _, fp := range r.fps {
		fp := fp // 创建副本避免闭包问题
		g.Go(func() error {
			return r.processFingerprintWithRetry(ctx, &results, uri, fp, indexCache, faviconHash)
		})
	}

	// 处理自定义指纹
	for _, fpReq := range CollectedFpReqs() {
		fpReq := fpReq // 创建副本
		g.Go(func() error {
			return r.processCustomFingerprintWithRetry(ctx, &results, uri, fpReq)
		})
	}

	// 等待所有任务完成
	if err := g.Wait(); err != nil {
		gologger.WithError(err).Debugln("部分指纹识别任务失败")
	}

	// 线程安全的去重操作
	return r.SafeDeduplication(results.items)
}

// processFingerprintWithRetry 处理单个指纹（带重试）
func (r *Runner) processFingerprintWithRetry(ctx context.Context, results *struct {
	sync.Mutex
	items []FpResult
}, uri string, fp parser.FingerPrint, indexCache *httpx.Response, faviconHash int32) error {
	const maxRetries = 3
	var lastErr error

	for retry := 0; retry < maxRetries; retry++ {
		if err := r.processFingerprint(ctx, results, uri, fp, indexCache, faviconHash); err != nil {
			lastErr = err
			time.Sleep(time.Duration(retry+1) * time.Second)
			continue
		}
		return nil
	}
	return lastErr
}

// processFingerprint 处理单个指纹
func (r *Runner) processFingerprint(ctx context.Context, results *struct {
	sync.Mutex
	items []FpResult
}, uri string, fp parser.FingerPrint, indexCache *httpx.Response, faviconHash int32) error {
	for _, req := range fp.Http {
		select {
		case <-ctx.Done():
			return ctx.Err()
		default:
			var resp *httpx.Response
			var err error

			if req.Path == "/" && indexCache != nil {
				resp = indexCache
			} else {
				resp, err = r.safeHTTPGet(ctx, uri+req.Path)
				if err != nil {
					continue
				}
			}

			if resp == nil {
				continue
			}

			fpConfig := parser.Config{
				Body:   resp.DataStr,
				Header: resp.GetHeaderRaw(),
				Icon:   faviconHash,
			}

			for _, dsl := range req.GetDsl() {
				if parser.Eval(&fpConfig, dsl) {
					version, _ := r.GetVersionSafely(ctx, uri, fp)
					
					results.Lock()
					results.items = append(results.items, FpResult{
						Name:    fp.Info.Name,
						Version: version,
						Type:    fp.Info.Metadata["type"],
					})
					results.Unlock()
					
					return nil
				}
			}
		}
	}
	return nil
}

// GetVersionSafely 安全的版本获取
func (r *Runner) GetVersionSafely(ctx context.Context, uri string, fp parser.FingerPrint) (string, error) {
	for _, req := range fp.Version {
		select {
		case <-ctx.Done():
			return "", ctx.Err()
		default:
			resp, err := r.safeHTTPGet(ctx, uri+req.Path)
			if err != nil {
				continue
			}

			if resp == nil {
				continue
			}

			if req.Extractor.Regex == "" {
				continue
			}

			compileRegex, err := regexp.Compile(req.Extractor.Regex)
			if err != nil {
				continue
			}

			index, err := strconv.Atoi(req.Extractor.Group)
			if err != nil || index < 0 {
				continue
			}

			body := resp.DataStr
			if req.Extractor.Part == "header" {
				body = resp.GetHeaderRaw()
			}

			submatches := compileRegex.FindStringSubmatch(body)
			if submatches != nil && index < len(submatches) {
				return submatches[index], nil
			}
		}
	}
	return "", nil
}

// SafeDeduplication 线程安全的去重操作
func (r *Runner) SafeDeduplication(results []FpResult) []FpResult {
	if len(results) == 0 {
		return results
	}

	seen := make(map[string]FpResult)
	var ret []FpResult

	// 使用 map 进行去重
	for _, result := range results {
		existing, exists := seen[result.Name]
		if !exists {
			seen[result.Name] = result
			ret = append(ret, result)
			continue
		}

		// 只有在新版本号不为空且与现有版本不同时才更新
		if result.Version != "" && result.Version != existing.Version {
			seen[result.Name] = result
			// 找到并替换现有条目
			for i := range ret {
				if ret[i].Name == result.Name {
					ret[i] = result
					break
				}
			}
		}
	}

	return ret
}
