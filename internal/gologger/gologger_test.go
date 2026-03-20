// Copyright (c) 2024-2026 Tencent Zhuque Lab. All rights reserved.
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.
//
// Requirement: Any integration or derivative work must explicitly attribute
// Tencent Zhuque Lab (https://github.com/Tencent/AI-Infra-Guard) in its
// documentation or user interface, as detailed in the NOTICE file.

package gologger

import (
	"errors"
	"testing"
)

func testDebug() {
	Debug("test debug func")
}
func TestLogger(t *testing.T) {
	Debugln("test debug")
	testDebug()
	Infoln("test info")
	Warnln("test warn")
	Errorln("test error")
	WithError(errors.New("test error")).Errorln("error")
}

func TestLoggerFile(t *testing.T) {
	//writer1 := os.Stdout
	//writer2, err := os.OpenFile("test.txt", os.O_WRONLY|os.O_APPEND|os.O_CREATE, 0644)
	//defer writer2.Close()
	//if err != nil {
	//	log.Fatalf("create file log.txt failed: %v", err)
	//}
	//Logger.SetOutput(io.MultiWriter(writer1, writer2))
	//Infoln("test info")
}
