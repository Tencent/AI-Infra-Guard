// Package httpx http请求主体
package httpx

import (
	"crypto/tls"
	"io/ioutil"
	"net/http"
	"net/url"
	"regexp"
	"strings"
	"unicode/utf8"

	"github.com/projectdiscovery/rawhttp"
	retryablehttp "github.com/projectdiscovery/retryablehttp-go"
	"golang.org/x/net/http2"
)

// HTTPX represent an instance of the library client
type HTTPX struct {
	client        *retryablehttp.Client
	client2       *http.Client
	CustomHeaders map[string]string
	Options       *HTTPOptions
}

// NewHttpx instance
func NewHttpx(options *HTTPOptions) (*HTTPX, error) {
	httpx := &HTTPX{}
	httpx.Options = options

	var retryablehttpOptions = retryablehttp.DefaultOptionsSpraying
	retryablehttpOptions.Timeout = httpx.Options.Timeout
	retryablehttpOptions.RetryMax = httpx.Options.RetryMax

	var redirectFunc = func(req *http.Request, _ []*http.Request) error {

		return http.ErrUseLastResponse // Tell the http client to not follow redirect
	}

	if httpx.Options.FollowRedirects {
		// Follow redirects
		redirectFunc = nil
	}

	transport := &http.Transport{
		MaxIdleConnsPerHost: -1,
		TLSClientConfig: &tls.Config{
			InsecureSkipVerify: true,
		},
		DisableKeepAlives: true,
	}
	if httpx.Options.Dialer != nil {
		transport.DialContext = httpx.Options.Dialer.Dial
	}

	if httpx.Options.HTTPProxy != "" {
		proxyURL, parseErr := url.Parse(httpx.Options.HTTPProxy)
		if parseErr != nil {
			return nil, parseErr
		}
		transport.Proxy = http.ProxyURL(proxyURL)
	}

	httpx.client = retryablehttp.NewWithHTTPClient(&http.Client{
		Transport:     transport,
		Timeout:       httpx.Options.Timeout,
		CheckRedirect: redirectFunc,
	}, retryablehttpOptions)

	httpx.client2 = &http.Client{
		Transport: &http2.Transport{
			TLSClientConfig: &tls.Config{
				InsecureSkipVerify: true,
			},
			AllowHTTP: true,
		},
		Timeout: httpx.Options.Timeout,
	}

	httpx.CustomHeaders = make(map[string]string)
	for _, item := range options.CustomHeaders {
		splits := strings.SplitN(item, ":", 2)
		if splits != nil && len(splits) == 2 {
			httpx.CustomHeaders[splits[0]] = splits[1]
		}
	}
	return httpx, nil
}

// Do http request
func (h *HTTPX) do(req *retryablehttp.Request) (*Response, error) {
	httpresp, err := h.getResponse(req)
	if err != nil {
		return nil, err
	}

	var resp Response
	resp.Response = httpresp
	resp.Headers = httpresp.Header.Clone()

	var respbody []byte
	// websockets don't have a readable body
	if httpresp.StatusCode != http.StatusSwitchingProtocols {
		var err error
		respbody, err = ioutil.ReadAll(httpresp.Body)
		if err != nil {
			return nil, err
		}
	}

	closeErr := httpresp.Body.Close()
	if closeErr != nil {
		return nil, closeErr
	}

	respbodystr := string(respbody)
	// Non UTF-8
	if contentTypes, ok := resp.Headers["Content-Type"]; ok {
		contentType := strings.Join(contentTypes, ";")

		// special cases
		if strings.Contains(contentType, "charset=GB2312") {
			bodyUtf8, err := Decodegbk([]byte(respbodystr))
			if err == nil {
				respbodystr = string(bodyUtf8)
				goto EndCoding
			}
		}

		regx := regexp.MustCompile("(?i)<meta.*charset=['\"]?(gb2312|gbk)")
		if regx.MatchString(respbodystr) {
			titleUtf8, err := Decodegbk([]byte(respbodystr))
			if err == nil {
				respbodystr = string(titleUtf8)
				goto EndCoding
			}
		}
	}
EndCoding:
	resp.DataStr = respbodystr
	resp.Title = ExtractTitle(respbodystr)
	resp.ContentLength = utf8.RuneCountInString(respbodystr)
	resp.Data = respbody
	// fill metrics
	resp.StatusCode = httpresp.StatusCode
	return &resp, nil
}

// getResponse returns response from safe / unsafe request
func (h *HTTPX) getResponse(req *retryablehttp.Request) (*http.Response, error) {
	if h.Options.Unsafe {
		return h.doUnsafe(req)
	}

	return h.client.Do(req)
}

// doUnsafe does an unsafe http request
func (h *HTTPX) doUnsafe(req *retryablehttp.Request) (*http.Response, error) {
	method := req.Method
	headers := req.Header
	targetURL := req.URL.String()
	body := req.Body
	return rawhttp.DoRaw(method, targetURL, "", headers, body)
}

// NewRequest from url
func (h *HTTPX) newRequest(method, targetURL string, body interface{}) (req *retryablehttp.Request, err error) {
	req, err = retryablehttp.NewRequest(method, targetURL, body)
	if err != nil {
		return
	}

	// Skip if unsafe is used
	if !h.Options.Unsafe {
		// set default user agent
		req.Header.Set("User-Agent", h.Options.DefaultUserAgent)
		// set default encoding to accept utf8
		req.Header.Add("Accept-Charset", "utf-8")
		for k, v := range h.CustomHeaders {
			req.Header.Set(k, v)
		}
	}
	return
}

// SetCustomHeaders on the provided request
func (h *HTTPX) setCustomHeaders(r *retryablehttp.Request, headers map[string]string) {
	for name, value := range headers {
		r.Header.Set(name, value)
		// host header is particular
		if strings.EqualFold(name, "host") {
			r.Host = value
		}
	}
}

// Get on get request
func (h *HTTPX) Get(targetUrl string, headers map[string]string) (*Response, error) {
	req, err := h.newRequest("GET", targetUrl, nil)
	if err != nil {
		return nil, err
	}
	if headers != nil {
		h.setCustomHeaders(req, headers)
	}
	return h.do(req)
}

// POST on post request
func (h *HTTPX) POST(targetUrl string, data interface{}, headers map[string]string) (*Response, error) {
	req, err := h.newRequest("POST", targetUrl, data)
	if headers != nil {
		h.setCustomHeaders(req, headers)
	}
	if err != nil {
		return nil, err
	}
	return h.do(req)
}
