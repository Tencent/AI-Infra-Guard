// Package gologger logger
package gologger

import (
	"bytes"
	"encoding/json"
	"fmt"
	"github.com/sirupsen/logrus"
	"path"
	"runtime"
	"strings"
)

var (
	// Positions in the call stack when tracing to report the calling method
	minimumCallerDepth int
)

const (
	ErrorLevel = logrus.ErrorLevel
	WarnLevel  = logrus.WarnLevel
	InfoLevel  = logrus.InfoLevel
	DebugLevel = logrus.DebugLevel
	TraceLevel = logrus.TraceLevel
)
const (
	maximumCallerDepth int = 20
	knownLogrusFrames  int = 5
)

var StdLogger *Logger

func init() {
	StdLogger = NewLogger()
}

// getCaller retrieves the name of the first non-logrus calling function
// 获取第一个非logrus调用函数的名称
func getCaller() *runtime.Frame {
	minimumCallerDepth = knownLogrusFrames
	pcs := make([]uintptr, maximumCallerDepth)
	loggerPackage := "AI-Infra-Guard/internal/gologger/types.go"
	depth := runtime.Callers(minimumCallerDepth, pcs)
	frames := runtime.CallersFrames(pcs[:depth])
	skip := false
	for f, again := frames.Next(); again; f, again = frames.Next() {
		if strings.HasSuffix(f.File, loggerPackage) {
			skip = true
			continue
		}
		if skip {
			return &f
		}
	}
	// if we got here, we failed to find the caller's context
	return nil
}

// ContextHook hook logger
type ContextHook struct {
}

// Levels returns all log levels
// 返回所有日志级别
func (hook ContextHook) Levels() []logrus.Level {
	return logrus.AllLevels
}

// Fire sets the caller information in the log entry
// 在日志条目中设置调用者信息
func (hook ContextHook) Fire(entry *logrus.Entry) error {
	entry.Caller = getCaller()
	return nil
}

// 颜色
const (
	red    = 31
	yellow = 33
	blue   = 36
	gray   = 37
)

// LogFormatter 日志格式化
type LogFormatter struct{}

// Format formats the log entry
// 格式化日志条目
func (t *LogFormatter) Format(entry *logrus.Entry) ([]byte, error) {
	//根据不同的level去展示颜色
	var levelColor int
	switch entry.Level {
	case logrus.DebugLevel, logrus.TraceLevel:
		levelColor = gray
	case logrus.WarnLevel:
		levelColor = yellow
	case logrus.ErrorLevel, logrus.FatalLevel, logrus.PanicLevel:
		levelColor = red
	default:
		levelColor = blue
	}
	if entry.Level == logrus.TraceLevel {
		return []byte(entry.Message), nil
	}
	var b *bytes.Buffer
	if entry.Buffer != nil {
		b = entry.Buffer
	} else {
		b = &bytes.Buffer{}
	}
	//自定义日期格式
	timestamp := entry.Time.Format("2006-01-02 15:04:05")
	if entry.HasCaller() {
		//自定义文件路径
		//funcVal := entry.Caller.Function
		fileVal := fmt.Sprintf("%s:%d", path.Base(entry.Caller.File), entry.Caller.Line)
		//自定义输出格式
		fmt.Fprintf(b, "[%s] \x1b[%dm[%s]\x1b[0m %s ", timestamp, levelColor, entry.Level, fileVal)
	} else {
		fmt.Fprintf(b, "[%s] \x1b[%dm[%s]\x1b[0m ", timestamp, levelColor, entry.Level)
	}
	data := make(map[string]interface{})
	for k, v := range entry.Data {
		switch v := v.(type) {
		case error:
			// Otherwise errors are ignored by `encoding/json`
			// https://github.com/sirupsen/logrus/issues/137
			data[k] = v.Error()
		case string:
			data[k] = v
		default:
			data[k] = fmt.Sprintf("%v", v)
		}
	}
	if len(data) > 0 {
		encoder := json.NewEncoder(b)
		encoder.SetEscapeHTML(true)
		//encoder.SetIndent("", "  ")
		if err := encoder.Encode(data); err != nil {
			return nil, fmt.Errorf("failed to marshal fields to JSON, %w", err)
		}
		b.WriteByte(' ')
	}
	fmt.Fprintf(b, "%s", entry.Message)
	if !strings.HasSuffix(entry.Message, "\n") {
		b.WriteByte('\n')
	}
	return b.Bytes(), nil
}
