// Package gologger logger
package gologger

import (
	"bytes"
	"encoding/json"
	"fmt"
	"path"
	"runtime"
	"strings"
	"sync"
	"time"

	"github.com/sirupsen/logrus"
)

var (
	logrusPackage string

	// Positions in the call stack when tracing to report the calling method
	minimumCallerDepth int

	// Used for caller information initialisation
	callerInitOnce sync.Once
)

const (
	DebugLevel = logrus.DebugLevel
	ErrorLevel = logrus.ErrorLevel
	WarnLevel  = logrus.WarnLevel
	InfoLevel  = logrus.InfoLevel
	TraceLevel = logrus.TraceLevel
)
const (
	maximumCallerDepth int = 25
	knownLogrusFrames  int = 7
)

var Logger *logrus.Logger
var noColor = false

func init() {
	Logger = logrus.New()
	Logger.SetLevel(logrus.TraceLevel)
	Logger.SetReportCaller(true)
	Logger.SetFormatter(&LogFormatter{})
	Logger.AddHook(ContextHook{})
}
func SetColor(color bool) {
	noColor = !color
}

// getPackageName reduces a fully qualified function name to the package name
// 将完整的函数名简化为包名
func getPackageName(f string) string {
	for {
		lastPeriod := strings.LastIndex(f, ".")
		lastSlash := strings.LastIndex(f, "/")
		if lastPeriod > lastSlash {
			f = f[:lastPeriod]
		} else {
			break
		}
	}

	return f
}

// getCaller retrieves the name of the first non-logrus calling function
// 获取第一个非logrus调用函数的名称
func getCaller() *runtime.Frame {
	// Restrict the lookback frames to avoid runaway lookups
	minimumCallerDepth = knownLogrusFrames
	logrusPackage = "github.com/sirupsen/logrus"
	pcs := make([]uintptr, maximumCallerDepth)
	depth := runtime.Callers(minimumCallerDepth, pcs)
	frames := runtime.CallersFrames(pcs[:depth])
	for f, again := frames.Next(); again; f, again = frames.Next() {
		// If the caller isn't part of this package, we're done
		pkg := getPackageName(f.Function)
		prefix := "github.com/Tencent/AI-Infra-Guard/internal/gologger."
		x := []string{
			"Debug",
			"Trace",
			"Print",
			"Info",
			"Warn",
			"Error",
			"Panic",
			"Fatal",
		}
		// If the caller isn't part of this package, we're done
		if pkg != logrusPackage {
			if pkg == "github.com/Tencent/AI-Infra-Guard/internal/gologger" {
				funcName := f.Function
				skip := false
				for _, cc := range x {
					if strings.HasPrefix(funcName, prefix+cc) {
						skip = true
						break
					}
				}
				if skip {
					continue
				}
			}
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
	if noColor {
		fmt.Fprintf(b, "[%s] [%s] ", timestamp, entry.Level)
	} else {
		if entry.HasCaller() {
			//自定义文件路径
			//funcVal := entry.Caller.Function
			fileVal := fmt.Sprintf("%s:%d", path.Base(entry.Caller.File), entry.Caller.Line)
			//自定义输出格式
			fmt.Fprintf(b, "[%s] \x1b[%dm[%s]\x1b[0m %s ", timestamp, levelColor, entry.Level, fileVal)
		} else {
			fmt.Fprintf(b, "[%s] \x1b[%dm[%s]\x1b[0m ", timestamp, levelColor, entry.Level)
		}
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

// WithError creates an entry from the standard Logger and adds an error to it
// 从标准Logger创建一个条目并添加一个错误
func WithError(err error) *logrus.Entry {
	return Logger.WithField(logrus.ErrorKey, err)
}

// WithField creates an entry from the standard Logger and adds a field to it
// 从标准Logger创建一个条目并添加一个字段
func WithField(key string, value interface{}) *logrus.Entry {
	return Logger.WithField(key, value)
}

// WithFields creates an entry from the standard Logger and adds multiple fields to it
// 从标准Logger创建一个条目并添加多个字段
func WithFields(fields logrus.Fields) *logrus.Entry {
	return Logger.WithFields(fields)
}

// WithTime creates an entry from the standard Logger and overrides the time of logs generated with it
// 从标准Logger创建一个条目并覆盖生成日志的时间
func WithTime(t time.Time) *logrus.Entry {
	return Logger.WithTime(t)
}

// Trace logs a message at level Trace on the standard Logger
// 在标准Logger上记录Trace级别的消息
func Trace(args ...interface{}) {
	Logger.Trace(args...)
}

// Debug logs a message at level Debug on the standard Logger
// 在标准Logger上记录Debug级别的消息
func Debug(args ...interface{}) {
	Logger.Debug(args...)
}

// Print logs a message at level Info on the standard Logger
// 在标准Logger上记录Info级别的消息
func Print(args ...interface{}) {
	Logger.Log(logrus.TraceLevel, args...)
}

// Info logs a message at level Info on the standard Logger
// 在标准Logger上记录Info级别的消息
func Info(args ...interface{}) {
	Logger.Info(args...)
}

// Warn logs a message at level Warn on the standard Logger
// 在标准Logger上记录Warn级别的消息
func Warn(args ...interface{}) {
	Logger.Warn(args...)
}

// Warning logs a message at level Warn on the standard Logger
// 在标准Logger上记录Warn级别的消息
func Warning(args ...interface{}) {
	Logger.Warning(args...)
}

// Error logs a message at level Error on the standard Logger
// 在标准Logger上记录Error级别的消息
func Error(args ...interface{}) {
	Logger.Error(args...)
}

// Panic logs a message at level Panic on the standard Logger
// 在标准Logger上记录Panic级别的消息
func Panic(args ...interface{}) {
	Logger.Panic(args...)
}

// Fatal logs a message at level Fatal on the standard Logger
// 在标准Logger上记录Fatal级别的消息
func Fatal(args ...interface{}) {
	Logger.Fatal(args...)
}

// Tracef logs a formatted message at level Trace on the standard Logger
// 在标准Logger上记录格式化的Trace级别消息
func Tracef(format string, args ...interface{}) {
	Logger.Tracef(format, args...)
}

// Debugf logs a formatted message at level Debug on the standard Logger
// 在标准Logger上记录格式化的Debug级别消息
func Debugf(format string, args ...interface{}) {
	Logger.Debugf(format, args...)
}

// Printf logs a formatted message at level Info on the standard Logger
// 在标准Logger上记录格式化的Info级别消息
func Printf(format string, args ...interface{}) {
	Logger.Printf(format, args...)
}

// Infof logs a formatted message at level Info on the standard Logger
// 在标准Logger上记录格式化的Info级别消息
func Infof(format string, args ...interface{}) {
	Logger.Infof(format, args...)
}

// Warnf logs a formatted message at level Warn on the standard Logger
// 在标准Logger上记录格式化的Warn级别消息
func Warnf(format string, args ...interface{}) {
	Logger.Warnf(format, args...)
}

// Warningf logs a formatted message at level Warn on the standard Logger
// 在标准Logger上记录格式化的Warn级别消息
func Warningf(format string, args ...interface{}) {
	Logger.Warningf(format, args...)
}

// Errorf logs a formatted message at level Error on the standard Logger
// 在标准Logger上记录格式化的Error级别消息
func Errorf(format string, args ...interface{}) {
	Logger.Errorf(format, args...)
}

// Panicf logs a formatted message at level Panic on the standard Logger
// 在标准Logger上记录格式化的Panic级别消息
func Panicf(format string, args ...interface{}) {
	Logger.Panicf(format, args...)
}

// Fatalf logs a formatted message at level Fatal on the standard Logger
// 在标准Logger上记录格式化的Fatal级别消息
func Fatalf(format string, args ...interface{}) {
	Logger.Fatalf(format, args...)
}

// Traceln logs a message at level Trace on the standard Logger
// 在标准Logger上记录Trace级别的消息
func Traceln(args ...interface{}) {
	Logger.Traceln(args...)
}

// Debugln logs a message at level Debug on the standard Logger
// 在标准Logger上记录Debug级别的消息
func Debugln(args ...interface{}) {
	Logger.Debugln(args...)
}

// Println logs a message at level Info on the standard Logger
// 在标准Logger上记录Info级别的消息
func Println(args ...interface{}) {
	Logger.Println(args...)
}

// Infoln logs a message at level Info on the standard Logger
// 在标准Logger上记录Info级别的消息
func Infoln(args ...interface{}) {
	Logger.Infoln(args...)
}

// Warnln logs a message at level Warn on the standard Logger
// 在标准Logger上记录Warn级别的消息
func Warnln(args ...interface{}) {
	Logger.Warnln(args...)
}

// Warningln logs a message at level Warn on the standard Logger
// 在标准Logger上记录Warn级别的消息
func Warningln(args ...interface{}) {
	Logger.Warningln(args...)
}

// Errorln logs a message at level Error on the standard Logger
// 在标准Logger上记录Error级别的消息
func Errorln(args ...interface{}) {
	Logger.Errorln(args...)
}

// Panicln logs a message at level Panic on the standard Logger
// 在标准Logger上记录Panic级别的消息
func Panicln(args ...interface{}) {
	Logger.Panicln(args...)
}

// Fatalln logs a message at level Fatal on the standard Logger
// 在标准Logger上记录Fatal级别的消息
func Fatalln(args ...interface{}) {
	Logger.Fatalln(args...)
}
