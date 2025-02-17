package preload

import (
	"context"
	"fmt"
	"github.com/Tencent/AI-Infra-Guard/common/fingerprints/parser"
	"github.com/Tencent/AI-Infra-Guard/internal/gologger"
	"github.com/Tencent/AI-Infra-Guard/pkg/httpx"
	"golang.org/x/sync/errgroup"
	"regexp"
	"strconv"
	"strings"
	"sync"
	"time"
)

// ResponseCache 缓存结构体
type ResponseCache struct {
	response *httpx.Response
	created  time.Time
	mutex    sync.RWMutex
}

// Runner 增强的运行器结构
type Runner struct {
	hp          *httpx.HTTPX
	fps         []parser.FingerPrint
	timeout     time.Duration
	cache       map[string]*ResponseCache
	cacheMutex  sync.RWMutex
	cacheExpiry time.Duration
}

// New 创建增强的Runner实例
func New(hp *httpx.HTTPX, fps parser.FingerPrints) *Runner {
	return &Runner{
		hp:          hp,
		fps:         fps,
		timeout:     30 * time.Second,
		cache:       make(map[string]*ResponseCache),
		cacheExpiry: 5 * time.Minute,
	}
}

// cleanup 定期清理过期缓存
func (r *Runner) cleanup(ctx context.Context) {
	ticker := time.NewTicker(r.cacheExpiry / 2)
	defer ticker.Stop()

	for {
		select {
		case <-ctx.Done():
			return
		case <-ticker.C:
			r.cleanExpiredCache()
		}
	}
}

// cleanExpiredCache 清理过期缓存
func (r *Runner) cleanExpiredCache() {
	r.cacheMutex.Lock()
	defer r.cacheMutex.Unlock()

	now := time.Now()
	for key, cache := range r.cache {
		cache.mutex.RLock()
		if now.Sub(cache.created) > r.cacheExpiry {
			cache.mutex.RUnlock()
			cache.mutex.Lock()
			if cache.response != nil && cache.response.Body != nil {
				cache.response.Body.Close()
			}
			cache.mutex.Unlock()
			delete(r.cache, key)
			continue
		}
		cache.mutex.RUnlock()
	}
}

// getFromCache 从缓存获取响应
func (r *Runner) getFromCache(key string) *httpx.Response {
	r.cacheMutex.RLock()
	cache, exists := r.cache[key]
	r.cacheMutex.RUnlock()

	if !exists {
		return nil
	}

	cache.mutex.RLock()
	defer cache.mutex.RUnlock()

	if time.Since(cache.created) > r.cacheExpiry {
		return nil
	}

	return cache.response
}

// setCache 设置缓存
func (r *Runner) setCache(key string, resp *httpx.Response) {
	r.cacheMutex.Lock()
	defer r.cacheMutex.Unlock()

	cache := &ResponseCache{
		response: resp,
		created:  time.Now(),
	}
	r.cache[key] = cache
}

// safeHTTPGet 增强的安全HTTP请求
func (r *Runner) safeHTTPGet(ctx context.Context, uri string) (*httpx.Response, error) {
	if r.hp == nil {
		return nil, fmt.Errorf("http client is nil")
	}

	// 先检查缓存
	if cachedResp := r.getFromCache(uri); cachedResp != nil {
		return cachedResp, nil
	}

	resp, err := r.hp.Get(uri, nil)
	if err != nil {
		return nil, fmt.Errorf("http get error: %w", err)
	}
	if resp == nil {
		return nil, fmt.Errorf("empty response received")
	}

	// 缓存响应
	r.setCache(uri, resp)
	return resp, nil
}

// RunFpReqs 增强的指纹识别执行器
func (r *Runner) RunFpReqs(uri string, concurrent int, faviconHash int32) ([]FpResult, error) {
	ctx, cancel := context.WithTimeout(context.Background(), r.timeout)
	defer cancel()

	// 启动缓存清理协程
	go r.cleanup(ctx)

	var results struct {
		sync.Mutex
		items []FpResult
		errs  []error
	}

	uri = strings.TrimRight(uri, "/")

	// 获取索引页面
	indexCache, err := r.safeHTTPGet(ctx, uri+"/")
	if err != nil {
		gologger.WithError(err).Debugln("获取索引页面失败")
	}

	g, ctx := errgroup.WithContext(ctx)
	g.SetLimit(concurrent)

	// 处理指纹
	for _, fp := range r.fps {
		fp := fp
		g.Go(func() error {
			err := r.processFingerprintWithRetry(ctx, &results, uri, fp, indexCache, faviconHash)
			if err != nil {
				results.Lock()
				results.errs = append(results.errs, err)
				results.Unlock()
			}
			return err
		})
	}

	// 等待所有任务完成
	if err := g.Wait(); err != nil {
		return nil, fmt.Errorf("fingerprint processing failed: %w", err)
	}

	// 检查是否有错误发生
	if len(results.errs) > 0 {
		return r.SafeDeduplication(results.items), fmt.Errorf("some fingerprint tasks failed: %v", results.errs)
	}

	return r.SafeDeduplication(results.items), nil
}

// processFingerprintWithRetry 增强的重试机制
func (r *Runner) processFingerprintWithRetry(ctx context.Context, results *struct {
	sync.Mutex
	items []FpResult
	errs  []error
}, uri string, fp parser.FingerPrint, indexCache *httpx.Response, faviconHash int32) error {
	var lastErr error
	backoff := time.Second

	for retry := 0; retry < 3; retry++ {
		select {
		case <-ctx.Done():
			return ctx.Err()
		default:
			if err := r.processFingerprint(ctx, results, uri, fp, indexCache, faviconHash); err != nil {
				lastErr = err
				time.Sleep(backoff)
				backoff *= 2 // 指数退避
				continue
			}
			return nil
		}
	}
	return fmt.Errorf("max retries exceeded: %w", lastErr)
}

// processFingerprint 改进的指纹处理
func (r *Runner) processFingerprint(ctx context.Context, results *struct {
	sync.Mutex
	items []FpResult
	errs  []error
}, uri string, fp parser.FingerPrint, indexCache *httpx.Response, faviconHash int32) error {
	for _, req := range fp.Http {
		select {
		case <-ctx.Done():
			return ctx.Err()
		default:
			resp, err := func() (*httpx.Response, error) {
				if req.Path == "/" && indexCache != nil {
					return indexCache, nil
				}
				return r.safeHTTPGet(ctx, uri+req.Path)
			}()

			if err != nil {
				continue
			}

			if resp == nil {
				continue
			}

			headerRaw := resp.GetHeaderRaw()
			fpConfig := parser.Config{
				Body:   resp.DataStr,
				Header: headerRaw,
				Icon:   faviconHash,
			}

			for _, dsl := range req.GetDsl() {
				if parser.Eval(&fpConfig, dsl) {
					version, err := r.GetVersionSafely(ctx, uri, fp)
					if err != nil {
						gologger.WithError(err).Debugln("版本获取失败")
					}

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

// Close 资源清理
func (r *Runner) Close() error {
	r.cacheMutex.Lock()
	defer r.cacheMutex.Unlock()

	var errs []error
	for _, cache := range r.cache {
		cache.mutex.Lock()
		if cache.response != nil && cache.response.Body != nil {
			if err := cache.response.Body.Close(); err != nil {
				errs = append(errs, err)
			}
		}
		cache.mutex.Unlock()
	}

	if len(errs) > 0 {
		return fmt.Errorf("errors closing resources: %v", errs)
	}
	return nil
}
