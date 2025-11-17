package preload

import (
	"testing"

	"github.com/stretchr/testify/assert"
)

func TestParseVersionRangeComparators(t *testing.T) {
	vr, err := parseVersionRange(">=1.0.0,<2.0.0")
	assert.NoError(t, err)
	assert.Equal(t, ">=1.0.0,<2.0.0", vr.String())
}

func TestParseVersionRangeBracketNotation(t *testing.T) {
	vr, err := parseVersionRange("[1.2.0,2.3.0)")
	assert.NoError(t, err)
	assert.Equal(t, ">=1.2.0,<2.3.0", vr.String())
}

func TestParseVersionRangeEquality(t *testing.T) {
	vr, err := parseVersionRange("1.5.1")
	assert.NoError(t, err)
	assert.Equal(t, "=1.5.1", vr.String())
}

func TestIntersectVersionRanges(t *testing.T) {
	r1, err := parseVersionRange(">=1.0.0,<2.0.0")
	assert.NoError(t, err)
	r2, err := parseVersionRange(">=1.5.0,<3.0.0")
	assert.NoError(t, err)

	result, ok := intersectVersionRanges([]versionRange{r1, r2})
	assert.True(t, ok)
	assert.Equal(t, ">=1.5.0,<2.0.0", result.String())
}

func TestIntersectVersionRangesEquality(t *testing.T) {
	r1, err := parseVersionRange(">=1.0.0")
	assert.NoError(t, err)
	r2, err := parseVersionRange("=1.5.0")
	assert.NoError(t, err)

	result, ok := intersectVersionRanges([]versionRange{r1, r2})
	assert.True(t, ok)
	assert.Equal(t, "=1.5.0", result.String())
}

func TestIntersectVersionRangesEmpty(t *testing.T) {
	r1, err := parseVersionRange(">=2.0.0")
	assert.NoError(t, err)
	r2, err := parseVersionRange("<1.0.0")
	assert.NoError(t, err)

	_, ok := intersectVersionRanges([]versionRange{r1, r2})
	assert.False(t, ok)
}
