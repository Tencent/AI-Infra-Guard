package preload

import (
	"fmt"
	"strings"

	vv "github.com/hashicorp/go-version"
)

type versionRange struct {
	min          *vv.Version
	max          *vv.Version
	minInclusive bool
	maxInclusive bool
}

func parseVersionRange(rangeStr string) (versionRange, error) {
	s := strings.TrimSpace(rangeStr)
	if s == "" {
		return versionRange{}, fmt.Errorf("empty version range")
	}

	var vr versionRange

	if (strings.HasPrefix(s, "[") || strings.HasPrefix(s, "(")) &&
		(strings.HasSuffix(s, "]") || strings.HasSuffix(s, ")")) {
		minInclusive := strings.HasPrefix(s, "[")
		maxInclusive := strings.HasSuffix(s, "]")
		content := strings.TrimSpace(s[1 : len(s)-1])
		bounds := strings.Split(content, ",")
		if len(bounds) != 2 {
			return versionRange{}, fmt.Errorf("invalid range format: %s", rangeStr)
		}
		if min := strings.TrimSpace(bounds[0]); min != "" {
			v, err := vv.NewVersion(min)
			if err != nil {
				return versionRange{}, err
			}
			vr.applyLowerBound(v, minInclusive)
		}
		if max := strings.TrimSpace(bounds[1]); max != "" {
			v, err := vv.NewVersion(max)
			if err != nil {
				return versionRange{}, err
			}
			vr.applyUpperBound(v, maxInclusive)
		}
		if !vr.isValid() {
			return versionRange{}, fmt.Errorf("invalid range: %s", rangeStr)
		}
		return vr, nil
	}

	parts := strings.Split(s, ",")
	for _, part := range parts {
		part = strings.TrimSpace(part)
		if part == "" {
			continue
		}
		switch {
		case strings.HasPrefix(part, ">="):
			v, err := vv.NewVersion(strings.TrimSpace(part[2:]))
			if err != nil {
				return versionRange{}, err
			}
			vr.applyLowerBound(v, true)
		case strings.HasPrefix(part, ">"):
			v, err := vv.NewVersion(strings.TrimSpace(part[1:]))
			if err != nil {
				return versionRange{}, err
			}
			vr.applyLowerBound(v, false)
		case strings.HasPrefix(part, "<="):
			v, err := vv.NewVersion(strings.TrimSpace(part[2:]))
			if err != nil {
				return versionRange{}, err
			}
			vr.applyUpperBound(v, true)
		case strings.HasPrefix(part, "<"):
			v, err := vv.NewVersion(strings.TrimSpace(part[1:]))
			if err != nil {
				return versionRange{}, err
			}
			vr.applyUpperBound(v, false)
		case strings.HasPrefix(part, "=="):
			v, err := vv.NewVersion(strings.TrimSpace(part[2:]))
			if err != nil {
				return versionRange{}, err
			}
			vr.applyLowerBound(v, true)
			vr.applyUpperBound(v, true)
		case strings.HasPrefix(part, "="):
			v, err := vv.NewVersion(strings.TrimSpace(part[1:]))
			if err != nil {
				return versionRange{}, err
			}
			vr.applyLowerBound(v, true)
			vr.applyUpperBound(v, true)
		default:
			v, err := vv.NewVersion(part)
			if err != nil {
				return versionRange{}, fmt.Errorf("invalid version constraint: %s", part)
			}
			vr.applyLowerBound(v, true)
			vr.applyUpperBound(v, true)
		}
	}

	if !vr.isValid() {
		return versionRange{}, fmt.Errorf("invalid range: %s", rangeStr)
	}

	return vr, nil
}

func (vr *versionRange) applyLowerBound(v *vv.Version, inclusive bool) {
	if vr.min == nil {
		vr.min = v
		vr.minInclusive = inclusive
		return
	}

	if v.GreaterThan(vr.min) {
		vr.min = v
		vr.minInclusive = inclusive
		return
	}

	if v.Equal(vr.min) {
		vr.minInclusive = vr.minInclusive && inclusive
	}
}

func (vr *versionRange) applyUpperBound(v *vv.Version, inclusive bool) {
	if vr.max == nil {
		vr.max = v
		vr.maxInclusive = inclusive
		return
	}

	if v.LessThan(vr.max) {
		vr.max = v
		vr.maxInclusive = inclusive
		return
	}

	if v.Equal(vr.max) {
		vr.maxInclusive = vr.maxInclusive && inclusive
	}
}

func (vr versionRange) isValid() bool {
	if vr.min == nil || vr.max == nil {
		return true
	}

	if vr.min.GreaterThan(vr.max) {
		return false
	}

	if vr.min.Equal(vr.max) && (!vr.minInclusive || !vr.maxInclusive) {
		return false
	}

	return true
}

func (vr versionRange) String() string {
	if vr.min == nil && vr.max == nil {
		return ""
	}

	if vr.min != nil && vr.max != nil && vr.min.Equal(vr.max) && vr.minInclusive && vr.maxInclusive {
		return "=" + vr.min.String()
	}

	parts := make([]string, 0, 2)
	if vr.min != nil {
		op := ">"
		if vr.minInclusive {
			op = ">="
		}
		parts = append(parts, fmt.Sprintf("%s%s", op, vr.min.String()))
	}
	if vr.max != nil {
		op := "<"
		if vr.maxInclusive {
			op = "<="
		}
		parts = append(parts, fmt.Sprintf("%s%s", op, vr.max.String()))
	}
	return strings.Join(parts, ",")
}

func intersectVersionRanges(ranges []versionRange) (versionRange, bool) {
	if len(ranges) == 0 {
		return versionRange{}, false
	}

	var result versionRange
	for _, r := range ranges {
		if r.min != nil {
			result.applyLowerBound(r.min, r.minInclusive)
		}
		if r.max != nil {
			result.applyUpperBound(r.max, r.maxInclusive)
		}
		if !result.isValid() {
			return versionRange{}, false
		}
	}

	if result.min == nil && result.max == nil {
		return versionRange{}, false
	}

	return result, true
}
