package chromium

import (
	"context"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"runtime"
	"time"

	"github.com/Tencent/AI-Infra-Guard/internal/gologger"

	"github.com/go-rod/rod"
	"github.com/go-rod/rod/lib/launcher"
	"github.com/go-rod/rod/lib/proto"
	"golang.org/x/sys/execabs"
)

const (
	MaxWidth       = 1280
	MinHeight      = 1024
	DefaultTimeout = 30 * time.Second
	StableWait     = 2 * time.Second
	Quality        = 90
)

// WebScreenShot 网页截图器
type WebScreenShot struct {
	browser  *rod.Browser
	pid      int
	launcher *launcher.Launcher
}

func NewWebScreenShotWithOptions() (*WebScreenShot, error) {
	if runtime.GOOS != "windows" && os.Geteuid() == 0 {
		return nil, errors.New("running as root is not supported when sandbox is enabled, please use a non-root user")
	}
	chromePath := FindExecPath()
	if chromePath == "" {
		return nil, errors.New("未找到Chrome/Chromium浏览器")
	}
	chromeLauncher := launcher.New().
		Leakless(true).
		Set("disable-gpu", "true").
		Set("ignore-certificate-errors", "true").
		Set("disable-crash-reporter", "true").
		Set("disable-notifications", "true").
		Set("hide-scrollbars", "true").
		Set("window-size", fmt.Sprintf("%d,%d", MaxWidth, MinHeight)).
		Set("mute-audio", "true").
		Delete("use-mock-keychain").
		NoSandbox(false).
		Headless(true)

	chromeLauncher.Bin(chromePath)

	launcherURL, err := chromeLauncher.Launch()
	if err != nil {
		return nil, fmt.Errorf("启动Chrome失败: %v", err)
	}

	browser := rod.New().ControlURL(launcherURL)
	err = browser.Connect()
	if err != nil {
		return nil, fmt.Errorf("连接Chrome失败: %v", err)
	}
	return &WebScreenShot{
		browser:  browser,
		pid:      chromeLauncher.PID(),
		launcher: chromeLauncher,
	}, nil
}

// Close 关闭截图器
func (w *WebScreenShot) Close() {
	defer func() {
		if r := recover(); r != nil {
			gologger.Errorf("截图器关闭panic: %v", r)
		}
	}()

	if w.browser != nil {
		err := w.browser.Close()
		if err != nil {
			gologger.Debugf("关闭浏览器失败: %v", err)
		}
	}

	if w.pid != 0 {
		if p, err := os.FindProcess(w.pid); err == nil {
			_ = p.Kill()
		}
	}
}

// Screen 截图网页
func (w *WebScreenShot) Screen(domain string) ([]byte, error) {
	ctx, cancel := context.WithTimeout(context.Background(), DefaultTimeout)
	defer cancel()
	return w.ScreenWithContext(ctx, domain)
}

// ScreenWithContext 带Context的截图方法
func (w *WebScreenShot) ScreenWithContext(ctx context.Context, domain string) ([]byte, error) {
	// 创建页面时使用context
	page, err := w.browser.Page(proto.TargetCreateTarget{})
	if err != nil {
		return nil, fmt.Errorf("创建页面失败: %v", err)
	}
	defer func() {
		if closeErr := page.Close(); closeErr != nil {
			gologger.Debugf("关闭页面失败: %v", closeErr)
		}
	}()

	// 禁用弹窗
	_, err = page.EvalOnNewDocument(`
		window.alert = () => {};
		window.confirm = () => true;
		window.prompt = () => '';
		window.onbeforeunload = null;
	`)
	if err != nil {
		gologger.Debugf("禁用弹窗失败: %v", err)
	}

	if err := page.Navigate(domain); err != nil {
		return nil, fmt.Errorf("导航到 %s 失败: %v", domain, err)
	}

	// 使用context控制页面等待
	waitChan := make(chan error, 1)
	go func() {
		// 等待页面稳定，使用较短的等待时间避免卡死
		err := page.WaitStable(5 * time.Second)
		waitChan <- err
	}()

	// 等待页面稳定或context取消
	select {
	case <-ctx.Done():
		//return nil, fmt.Errorf("context已取消: %v", ctx.Err())
	case err := <-waitChan:
		if err != nil {
			gologger.Debugf("页面稳定等待出错: %s, %v", domain, err)
			// 即使等待失败也继续截图
		}
	}

	// 截图，使用context超时控制
	quality := Quality
	buf, err := page.Screenshot(false, &proto.PageCaptureScreenshot{
		Format:  proto.PageCaptureScreenshotFormatJpeg,
		Quality: &quality,
	})
	if err != nil {
		return nil, fmt.Errorf("截图失败: %v", err)
	}

	// 处理图片
	return buf, nil
}

// FindExecPath 查找Chrome可执行文件路径
func FindExecPath() string {
	var locations []string
	switch runtime.GOOS {
	case "darwin":
		locations = []string{
			"/Applications/Chromium.app/Contents/MacOS/Chromium",
			"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
		}
	case "windows":
		locations = []string{
			"chrome",
			"chrome.exe",
			`C:\Program Files (x86)\Google\Chrome\Application\chrome.exe`,
			`C:\Program Files\Google\Chrome\Application\chrome.exe`,
			filepath.Join(os.Getenv("USERPROFILE"), `AppData\Local\Google\Chrome\Application\chrome.exe`),
			filepath.Join(os.Getenv("USERPROFILE"), `AppData\Local\Chromium\Application\chrome.exe`),
		}
	default:
		locations = []string{
			"/usr/lib/chromium-browser",
			"chromium-browser",
			"chromium",
			"/snap/bin/chromium",
			"/snap/chromium/current/usr/lib/chromium-browser/chrome",
			"/opt/google/chrome",
			"google-chrome",
			"google-chrome-stable",
			"google-chrome-beta",
			"google-chrome-unstable",
			"/usr/bin/google-chrome",
			"/usr/local/bin/chrome",
			"chrome",
		}
	}

	for _, path := range locations {
		if found, err := execabs.LookPath(path); err == nil {
			return found
		}
	}
	return ""
}
