package gologger

import (
	"errors"
	"io"
	"log"
	"os"
	"testing"
)

func testDebug() {
	Debug("test debug func")
}
func TestLogger(t *testing.T) {
	Logger.SetLevel(DebugLevel)
	WithField("field1", "value").WithField("field2", "value21").Info()
	Debugln("test debug")
	testDebug()
	Infoln("test info")
	Warnln("test warn")
	Errorln("test error")
	WithError(errors.New("test error")).Errorln("error")
}

func TestLoggerFile(t *testing.T) {
	writer1 := os.Stdout
	writer2, err := os.OpenFile("test.txt", os.O_WRONLY|os.O_APPEND|os.O_CREATE, 0644)
	defer writer2.Close()
	if err != nil {
		log.Fatalf("create file log.txt failed: %v", err)
	}
	Logger.SetOutput(io.MultiWriter(writer1, writer2))
	Infoln("test info")
}
