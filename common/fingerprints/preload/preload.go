// Package preload 漏洞指纹判断golang语言写法
package preload

import (
	"github.com/Tencent/AI-Infra-Guard/common/fingerprints/parser"
	"github.com/Tencent/AI-Infra-Guard/common/utils"
	"github.com/Tencent/AI-Infra-Guard/internal/gologger"
	"github.com/Tencent/AI-Infra-Guard/pkg/httpx"
	"regexp"
	"strconv"
	"strings"
	"sync"

	"github.com/remeh/sizedwaitgroup"
)

// FingerPrintFunc 指纹识别接口
// 实现此接口可以添加自定义的指纹识别逻辑
type FingerPrintFunc interface {
	Match(httpx *httpx.HTTPX, uri string) bool
	GetVersion(httpx *httpx.HTTPX, uri string) (string, error)
	Name() string
}

// CollectedFpReqs 返回所有已注册的指纹识别实现
func CollectedFpReqs() []FingerPrintFunc {
	return []FingerPrintFunc{
		Mlflow{},
	}
}

// FpResult 指纹结构体
type FpResult struct {
	Name    string `json:"name"`
	Version string `json:"version,omitempty"`
	Type    string `json:"type,omitempty"`
}

// Runner 指纹识别运行器
// 用于执行指纹识别任务
type Runner struct {
	hp  *httpx.HTTPX
	fps []parser.FingerPrint
}

// New 创建新的Runner实例
func New(hp *httpx.HTTPX, fps parser.FingerPrints) *Runner {
	r := &Runner{hp, fps}
	return r
}

// RunFpReqs 执行指纹识别
// uri: 目标URL
// concurrent: 并发数
// faviconHash: favicon图标的hash值
// 返回识别到的指纹结果列表
func (r *Runner) RunFpReqs(uri string, concurrent int, faviconHash int32) []FpResult {
	wg := sizedwaitgroup.New(concurrent)
	mux := sync.Mutex{}
	ret := make([]FpResult, 0)
	uri = strings.TrimRight(uri, "/")

	indexCache, _ := r.hp.Get(uri+"/", nil)

	for _, fp := range r.fps {
		wg.Add()
		go func(fp parser.FingerPrint) {
			defer wg.Done()
			var resp *httpx.Response
			var err error
			for _, req := range fp.Http {
				if req.Path == "/" && req.Method == "GET" {
					resp = indexCache
				} else {
					if req.Method == "POST" {
						resp, err = r.hp.POST(uri+req.Path, req.Data, nil)
					} else {
						resp, err = r.hp.Get(uri+req.Path, nil)
					}
					if err != nil {
						gologger.WithError(err).Debugln("请求失败")
						continue
					}
				}
				if resp == nil {
					continue
				}
				// 文件指纹
				fpConfig := parser.Config{
					Body:   resp.DataStr,
					Header: resp.GetHeaderRaw(),
					Icon:   faviconHash,
				}
				for _, dsl := range req.GetDsl() {
					if parser.Eval(&fpConfig, dsl) {
						name := fp.Info.Name
						version := ""
						version, err := EvalFpVersion(uri, r.hp, fp)
						if err != nil {
							gologger.WithError(err).Errorln("获取版本失败")
						}
						mux.Lock()
						type_, ok := fp.Info.Metadata["type"]
						if !ok {
							type_ = ""
						}
						ret = append(ret, FpResult{
							Name:    name,
							Version: version,
							Type:    type_,
						})
						mux.Unlock()
						break
					}
				}
			}
		}(fp)
	}
	for _, fpReq := range CollectedFpReqs() {
		wg.Add()
		go func(fpReq FingerPrintFunc) {
			defer wg.Done()
			if fpReq.Match(r.hp, uri) {
				fpresult := FpResult{
					Name:    fpReq.Name(),
					Version: "",
					Type:    "",
				}
				version, err := fpReq.GetVersion(r.hp, uri)
				if err == nil {
					fpresult.Version = version
				}
				mux.Lock()
				ret = append(ret, fpresult)
				mux.Unlock()
			}
		}(fpReq)
	}
	wg.Wait()
	ret = r.Deduplication(ret)
	return ret
}

// Deduplication 对指纹识别结果进行去重
// 如果存在相同名称的指纹，保留版本号不为空的结果
func (r *Runner) Deduplication(results []FpResult) []FpResult {
	var ret []FpResult
	var dup = make(map[string]string)
	for _, result := range results {
		_, ok := dup[result.Name]
		if !ok {
			dup[result.Name] = result.Version
			ret = append(ret, result)
		} else {
			if result.Version != "" && dup[result.Name] != result.Version {
				dup[result.Name] = result.Version
				// 删除原来
				for i, v := range ret {
					if v.Name == result.Name {
						ret = append(ret[:i], ret[i+1:]...)
						break
					}
				}
				ret = append(ret, result)
			}
		}
	}
	return ret
}

// GetFps 获取当前Runner中的所有指纹规则
func (r *Runner) GetFps() []parser.FingerPrint {
	return r.fps
}

// EvalFpVersion 获取指定指纹的版本信息
// 通过正则表达式从响应中提取版本号
func EvalFpVersion(uri string, hp *httpx.HTTPX, fp parser.FingerPrint) (string, error) {
	// 优先使用精确版本提取
	for _, req := range fp.Version {
		resp, err := hp.Get(uri+req.Path, nil)
		if err != nil {
			gologger.WithError(err).Errorln("请求失败")
			continue
		}
		fpConfig := &parser.Config{
			Body:   resp.DataStr,
			Header: resp.GetHeaderRaw(),
			Icon:   0,
		}
		version := ""
		if req.Extractor.Regex != "" {
			compileRegex, err := regexp.Compile("(?i)" + req.Extractor.Regex)
			if err != nil {
				gologger.WithError(err).Errorln("compile regex error", req.Extractor.Regex)
			} else {
				index, err := strconv.Atoi(req.Extractor.Group)
				if err != nil {
					gologger.WithError(err).Errorln("parse part error", req.Extractor.Part)
				} else {
					body := fpConfig.Body
					if req.Extractor.Part == "header" {
						body = fpConfig.Header
					}
					submatches := compileRegex.FindStringSubmatch(body)
					if submatches != nil {
						version = submatches[index]
					}
				}
			}
		}
		return version, nil
	}

	// 模糊版本信息
	for _, fv := range fp.FuzzVersion {
		resp, err := hp.Get(uri+fv.Path, nil)
		if err != nil {
			gologger.WithError(err).Debugln("请求失败")
			continue
		}
		bodyHash := utils.BodyHash(resp.Data)
		if fv.Hash != "" && fv.Hash != bodyHash {
			continue
		}
		if fv.Pattern != "" {
			reg, err := regexp.Compile(fv.Pattern)
			if err != nil {
				gologger.WithError(err).Debugln("compile regex error", fv.Pattern)
				continue
			}
			if !reg.MatchString(resp.DataStr) {
				continue
			}
		} else if fv.Hash == "" && resp.StatusCode != 200 {
			continue
		}
		return fv.VersionRange, nil
	}

	return "", nil
}
