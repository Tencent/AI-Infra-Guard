// Package options banner
package options

import (
	"encoding/base64"
	"fmt"
)

const version = "v3.4.3-dev"

// ShowBanner is used to show the banner to the user
func ShowBanner() {
	const banner = `AI Infrastructure Guard System ` + version
	data := "ICAgIF8gICAgX19fICAgX19fICAgICAgICBfXyAgICAgICAgICAgICAgX19fXyAgICAgICAgICAgICAgICAgICAgIF8gCiAgIC8gXCAgfF8gX3wgfF8gX3xfIF9fICAvIF98XyBfXyBfXyBfICAgLyBfX198XyAgIF8gIF9fIF8gXyBfXyBfX3wgfAogIC8gXyBcICB8IHwgICB8IHx8ICdfIFx8IHxffCAnX18vIF9gIHwgfCB8ICBffCB8IHwgfC8gX2AgfCAnX18vIF9gIHwKIC8gX19fIFwgfCB8ICAgfCB8fCB8IHwgfCAgX3wgfCB8IChffCB8IHwgfF98IHwgfF98IHwgKF98IHwgfCB8IChffCB8Ci9fLyAgIFxfXF9fX3wgfF9fX3xffCB8X3xffCB8X3wgIFxfXyxffCAgXF9fX198XF9fLF98XF9fLF98X3wgIFxfXyxffA=="
	bytes, _ := base64.StdEncoding.DecodeString(data)
	fmt.Printf("%s\n\n%s\n\n", string(bytes), banner)
}
