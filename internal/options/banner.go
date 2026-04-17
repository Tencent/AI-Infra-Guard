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

// Package options banner
package options

import (
	"encoding/base64"
	"fmt"
)

const version = "v4.1.4"

func GetVersion() string {
	return version
}

// ShowBanner is used to show the banner to the user
func ShowBanner() {
	const banner = `AI Infrastructure Guard System ` + version
	data := "ICAgIF8gICAgX19fICAgX19fICAgICAgICBfXyAgICAgICAgICAgICAgX19fXyAgICAgICAgICAgICAgICAgICAgIF8gCiAgIC8gXCAgfF8gX3wgfF8gX3xfIF9fICAvIF98XyBfXyBfXyBfICAgLyBfX198XyAgIF8gIF9fIF8gXyBfXyBfX3wgfAogIC8gXyBcICB8IHwgICB8IHx8ICdfIFx8IHxffCAnX18vIF9gIHwgfCB8ICBffCB8IHwgfC8gX2AgfCAnX18vIF9gIHwKIC8gX19fIFwgfCB8ICAgfCB8fCB8IHwgfCAgX3wgfCB8IChffCB8IHwgfF98IHwgfF98IHwgKF98IHwgfCB8IChffCB8Ci9fLyAgIFxfXF9fX3wgfF9fX3xffCB8X3xffCB8X3wgIFxfXyxffCAgXF9fX198XF9fLF98XF9fLF98X3wgIFxfXyxffA=="
	bytes, _ := base64.StdEncoding.DecodeString(data)
	fmt.Printf("%s\n\n%s\n\n", string(bytes), banner)
}
