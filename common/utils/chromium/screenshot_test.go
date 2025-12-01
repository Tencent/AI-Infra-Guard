package chromium

import (
	"os"
	"testing"

	"github.com/stretchr/testify/assert"
)

func TestScreenshot(t *testing.T) {
	instance, err := NewWebScreenShotWithOptions()
	assert.NoError(t, err)
	url := "https://www.baidu.com/"
	data, err := instance.Screen(url)
	assert.NoError(t, err)
	assert.NotEmpty(t, data)
	err = os.WriteFile("screenshot.png", data, 0644)
	assert.NoError(t, err)
}
