package gologger

import (
	"github.com/sirupsen/logrus"
)

type Logger struct {
	log *logrus.Logger
}

func NewLogger() *Logger {
	logger := logrus.New()
	logger.SetLevel(logrus.TraceLevel)
	logger.SetReportCaller(true)
	logger.SetFormatter(&LogFormatter{})
	logger.AddHook(ContextHook{})
	return &Logger{
		log: logger,
	}
}

type Entry struct {
	*logrus.Entry
}

func (l *Logger) Logrus() *logrus.Logger {
	return l.log
}

func (l *Logger) WithError(err error) *Entry {
	entry := l.log.WithError(err)
	return &Entry{
		entry,
	}
}

// Debug logs a message at level Debug on the standard Logger
// 在标准Logger上记录Debug级别的消息
func (l *Logger) Debug(args ...interface{}) {
	l.log.Debug(args...)
}

// Print logs a message at level Info on the standard Logger
// 在标准Logger上记录Info级别的消息
func (l *Logger) Print(args ...interface{}) {
	l.log.Log(logrus.TraceLevel, args...)
}

// Info logs a message at level Info on the standard Logger
// 在标准Logger上记录Info级别的消息
func (l *Logger) Info(args ...interface{}) {
	l.log.Info(args...)
}

// Warn logs a message at level Warn on the standard Logger
// 在标准Logger上记录Warn级别的消息
func (l *Logger) Warn(args ...interface{}) {
	l.log.Warn(args...)
}

// Warning logs a message at level Warn on the standard Logger
// 在标准Logger上记录Warn级别的消息
func (l *Logger) Warning(args ...interface{}) {
	l.log.Warning(args...)
}

// Error logs a message at level Error on the standard Logger
// 在标准Logger上记录Error级别的消息
func (l *Logger) Error(args ...interface{}) {
	l.log.Error(args...)
}

// Panic logs a message at level Panic on the standard Logger
// 在标准Logger上记录Panic级别的消息
func (l *Logger) Panic(args ...interface{}) {
	l.log.Panic(args...)
}

// Fatal logs a message at level Fatal on the standard Logger
// 在标准Logger上记录Fatal级别的消息
func (l *Logger) Fatal(args ...interface{}) {
	l.log.Fatal(args...)
}

// Debugf logs a formatted message at level Debug on the standard Logger
// 在标准Logger上记录格式化的Debug级别消息
func (l *Logger) Debugf(format string, args ...interface{}) {
	l.log.Debugf(format, args...)
}

// Printf logs a formatted message at level Info on the standard Logger
// 在标准Logger上记录格式化的Info级别消息
func (l *Logger) Printf(format string, args ...interface{}) {
	l.log.Printf(format, args...)
}

// Infof logs a formatted message at level Info on the standard Logger
// 在标准Logger上记录格式化的Info级别消息
func (l *Logger) Infof(format string, args ...interface{}) {
	l.log.Infof(format, args...)
}

// Warnf logs a formatted message at level Warn on the standard Logger
// 在标准Logger上记录格式化的Warn级别消息
func (l *Logger) Warnf(format string, args ...interface{}) {
	l.log.Warnf(format, args...)
}

// Warningf logs a formatted message at level Warn on the standard Logger
// 在标准Logger上记录格式化的Warn级别消息
func (l *Logger) Warningf(format string, args ...interface{}) {
	l.log.Warningf(format, args...)
}

// Errorf logs a formatted message at level Error on the standard Logger
// 在标准Logger上记录格式化的Error级别消息
func (l *Logger) Errorf(format string, args ...interface{}) {
	l.log.Errorf(format, args...)
}

// Fatalf logs a formatted message at level Fatal on the standard Logger
// 在标准Logger上记录格式化的Fatal级别消息
func (l *Logger) Fatalf(format string, args ...interface{}) {
	l.log.Fatalf(format, args...)
}

// Debugln logs a message at level Debug on the standard Logger
// 在标准Logger上记录Debug级别的消息
func (l *Logger) Debugln(args ...interface{}) {
	l.log.Debugln(args...)
}

// Println logs a message at level Info on the standard Logger
// 在标准Logger上记录Info级别的消息
func (l *Logger) Println(args ...interface{}) {
	l.log.Println(args...)
}

// Infoln logs a message at level Info on the standard Logger
// 在标准Logger上记录Info级别的消息
func (l *Logger) Infoln(args ...interface{}) {
	l.log.Infoln(args...)
}

// Warnln logs a message at level Warn on the standard Logger
// 在标准Logger上记录Warn级别的消息
func (l *Logger) Warnln(args ...interface{}) {
	l.log.Warnln(args...)
}

// Warningln logs a message at level Warn on the standard Logger
// 在标准Logger上记录Warn级别的消息
func (l *Logger) Warningln(args ...interface{}) {
	l.log.Warningln(args...)
}

// Errorln logs a message at level Error on the standard Logger
// 在标准Logger上记录Error级别的消息
func (l *Logger) Errorln(args ...interface{}) {
	l.log.Errorln(args...)
}

// Panicln logs a message at level Panic on the standard Logger
// 在标准Logger上记录Panic级别的消息
func (l *Logger) Panicln(args ...interface{}) {
	l.log.Panicln(args...)
}

// Fatalln logs a message at level Fatal on the standard Logger
// 在标准Logger上记录Fatal级别的消息
func (l *Logger) Fatalln(args ...interface{}) {
	l.log.Fatalln(args...)
}

// Debug logs a message at level Debug
// 记录Debug级别的消息
func (e *Entry) Debug(args ...interface{}) {
	e.Entry.Debug(args...)
}

// Print logs a message at level Info
// 记录Info级别的消息
func (e *Entry) Print(args ...interface{}) {
	e.Entry.Log(logrus.TraceLevel, args...)
}

// Info logs a message at level Info
// 记录Info级别的消息
func (e *Entry) Info(args ...interface{}) {
	e.Entry.Info(args...)
}

// Warn logs a message at level Warn
// 记录Warn级别的消息
func (e *Entry) Warn(args ...interface{}) {
	e.Entry.Warn(args...)
}

// Warning logs a message at level Warn
// 记录Warn级别的消息
func (e *Entry) Warning(args ...interface{}) {
	e.Entry.Warning(args...)
}

// Error logs a message at level Error
// 记录Error级别的消息
func (e *Entry) Error(args ...interface{}) {
	e.Entry.Error(args...)
}

// Panic logs a message at level Panic
// 记录Panic级别的消息
func (e *Entry) Panic(args ...interface{}) {
	e.Entry.Panic(args...)
}

// Fatal logs a message at level Fatal
// 记录Fatal级别的消息
func (e *Entry) Fatal(args ...interface{}) {
	e.Entry.Fatal(args...)
}

// Debugf logs a formatted message at level Debug
// 记录格式化的Debug级别消息
func (e *Entry) Debugf(format string, args ...interface{}) {
	e.Entry.Debugf(format, args...)
}

// Printf logs a formatted message at level Info
// 记录格式化的Info级别消息
func (e *Entry) Printf(format string, args ...interface{}) {
	e.Entry.Printf(format, args...)
}

// Infof logs a formatted message at level Info
// 记录格式化的Info级别消息
func (e *Entry) Infof(format string, args ...interface{}) {
	e.Entry.Infof(format, args...)
}

// Warnf logs a formatted message at level Warn
// 记录格式化的Warn级别消息
func (e *Entry) Warnf(format string, args ...interface{}) {
	e.Entry.Warnf(format, args...)
}

// Warningf logs a formatted message at level Warn
// 记录格式化的Warn级别消息
func (e *Entry) Warningf(format string, args ...interface{}) {
	e.Entry.Warningf(format, args...)
}

// Errorf logs a formatted message at level Error
// 记录格式化的Error级别消息
func (e *Entry) Errorf(format string, args ...interface{}) {
	e.Entry.Errorf(format, args...)
}

// Fatalf logs a formatted message at level Fatal
// 记录格式化的Fatal级别消息
func (e *Entry) Fatalf(format string, args ...interface{}) {
	e.Entry.Fatalf(format, args...)
}

// Debugln logs a message at level Debug
// 记录Debug级别的消息
func (e *Entry) Debugln(args ...interface{}) {
	e.Entry.Debugln(args...)
}

// Println logs a message at level Info
// 记录Info级别的消息
func (e *Entry) Println(args ...interface{}) {
	e.Entry.Println(args...)
}

// Infoln logs a message at level Info
// 记录Info级别的消息
func (e *Entry) Infoln(args ...interface{}) {
	e.Entry.Infoln(args...)
}

// Warnln logs a message at level Warn
// 记录Warn级别的消息
func (e *Entry) Warnln(args ...interface{}) {
	e.Entry.Warnln(args...)
}

// Warningln logs a message at level Warn
// 记录Warn级别的消息
func (e *Entry) Warningln(args ...interface{}) {
	e.Entry.Warningln(args...)
}

// Errorln logs a message at level Error
// 记录Error级别的消息
func (e *Entry) Errorln(args ...interface{}) {
	e.Entry.Errorln(args...)
}

// Panicln logs a message at level Panic
// 记录Panic级别的消息
func (e *Entry) Panicln(args ...interface{}) {
	e.Entry.Panicln(args...)
}

// Fatalln logs a message at level Fatal
// 记录Fatal级别的消息
func (e *Entry) Fatalln(args ...interface{}) {
	e.Entry.Fatalln(args...)
}

// Debug logs a message at level Debug on the standard Logger
// 在标准Logger上记录Debug级别的消息
func Debug(args ...interface{}) {
	StdLogger.Debug(args...)
}

// Print logs a message at level Info on the standard Logger
// 在标准Logger上记录Info级别的消息
func Print(args ...interface{}) {
	StdLogger.Print(args...)
}

// Info logs a message at level Info on the standard Logger
// 在标准Logger上记录Info级别的消息
func Info(args ...interface{}) {
	StdLogger.Info(args...)
}

// Warn logs a message at level Warn on the standard Logger
// 在标准Logger上记录Warn级别的消息
func Warn(args ...interface{}) {
	StdLogger.Warn(args...)
}

// Warning logs a message at level Warn on the standard Logger
// 在标准Logger上记录Warn级别的消息
func Warning(args ...interface{}) {
	StdLogger.Warning(args...)
}

// Error logs a message at level Error on the standard Logger
// 在标准Logger上记录Error级别的消息
func Error(args ...interface{}) {
	StdLogger.Error(args...)
}

// Panic logs a message at level Panic on the standard Logger
// 在标准Logger上记录Panic级别的消息
func Panic(args ...interface{}) {
	StdLogger.Panic(args...)
}

// Fatal logs a message at level Fatal on the standard Logger
// 在标准Logger上记录Fatal级别的消息
func Fatal(args ...interface{}) {
	StdLogger.Fatal(args...)
}

// Debugf logs a formatted message at level Debug on the standard Logger
// 在标准Logger上记录格式化的Debug级别消息
func Debugf(format string, args ...interface{}) {
	StdLogger.Debugf(format, args...)
}

// Printf logs a formatted message at level Info on the standard Logger
// 在标准Logger上记录格式化的Info级别消息
func Printf(format string, args ...interface{}) {
	StdLogger.Printf(format, args...)
}

// Infof logs a formatted message at level Info on the standard Logger
// 在标准Logger上记录格式化的Info级别消息
func Infof(format string, args ...interface{}) {
	StdLogger.Infof(format, args...)
}

// Warnf logs a formatted message at level Warn on the standard Logger
// 在标准Logger上记录格式化的Warn级别消息
func Warnf(format string, args ...interface{}) {
	StdLogger.Warnf(format, args...)
}

// Warningf logs a formatted message at level Warn on the standard Logger
// 在标准Logger上记录格式化的Warn级别消息
func Warningf(format string, args ...interface{}) {
	StdLogger.Warningf(format, args...)
}

// Errorf logs a formatted message at level Error on the standard Logger
// 在标准Logger上记录格式化的Error级别消息
func Errorf(format string, args ...interface{}) {
	StdLogger.Errorf(format, args...)
}

// Fatalf logs a formatted message at level Fatal on the standard Logger
// 在标准Logger上记录格式化的Fatal级别消息
func Fatalf(format string, args ...interface{}) {
	StdLogger.Fatalf(format, args...)
}

// Debugln logs a message at level Debug on the standard Logger
// 在标准Logger上记录Debug级别的消息
func Debugln(args ...interface{}) {
	StdLogger.Debugln(args...)
}

// Println logs a message at level Info on the standard Logger
// 在标准Logger上记录Info级别的消息
func Println(args ...interface{}) {
	StdLogger.Println(args...)
}

// Infoln logs a message at level Info on the standard Logger
// 在标准Logger上记录Info级别的消息
func Infoln(args ...interface{}) {
	StdLogger.Infoln(args...)
}

// Warnln logs a message at level Warn on the standard Logger
// 在标准Logger上记录Warn级别的消息
func Warnln(args ...interface{}) {
	StdLogger.Warnln(args...)
}

// Warningln logs a message at level Warn on the standard Logger
// 在标准Logger上记录Warn级别的消息
func Warningln(args ...interface{}) {
	StdLogger.Warningln(args...)
}

// Errorln logs a message at level Error on the standard Logger
// 在标准Logger上记录Error级别的消息
func Errorln(args ...interface{}) {
	StdLogger.Errorln(args...)
}

// Panicln logs a message at level Panic on the standard Logger
// 在标准Logger上记录Panic级别的消息
func Panicln(args ...interface{}) {
	StdLogger.Panicln(args...)
}

// Fatalln logs a message at level Fatal on the standard Logger
// 在标准Logger上记录Fatal级别的消息
func Fatalln(args ...interface{}) {
	StdLogger.Fatalln(args...)
}

// WithError adds an error as single field to the log entry
// 为日志条目添加错误字段
func WithError(err error) *Entry {
	return StdLogger.WithError(err)
}
