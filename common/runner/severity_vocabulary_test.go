package runner

import (
	"testing"

	vulstruct "github.com/Tencent/AI-Infra-Guard/pkg/vulstruct"
)

// Every spelling below is accepted by the data validator
// (cmd/yamlcheck/main.go isValidSeverity), so a rule file carrying it may ship.
// Each one therefore has to be classified the same way by the scorer; only
// "low", "info" and "unknown" may land in the low bucket.
func TestCalcSecScoreClassifiesEveryValidSeverity(t *testing.T) {
	r := &Runner{}
	cases := []struct {
		severity       string
		high, med, low int
	}{
		{"critical", 1, 0, 0}, {"CRITICAL", 1, 0, 0},
		{"high", 1, 0, 0}, {"High", 1, 0, 0},
		{"高危", 1, 0, 0}, {"严重", 1, 0, 0},
		{"高", 1, 0, 0}, {"危急", 1, 0, 0},
		{"medium", 0, 1, 0}, {"Medium", 0, 1, 0},
		{"中危", 0, 1, 0}, {"中等", 0, 1, 0},
		{"low", 0, 0, 1}, {"低", 0, 0, 1},
		{"info", 0, 0, 1}, {"信息", 0, 0, 1},
		{"unknown", 0, 0, 1},
		{"  HIGH  ", 1, 0, 0}, // trimmed
	}
	for _, c := range cases {
		got := r.CalcSecScore([]vulstruct.Info{{Severity: c.severity}})
		if got.HighRisk != c.high || got.MediumRisk != c.med || got.LowRisk != c.low {
			t.Errorf("severity %q: got high=%d medium=%d low=%d (sec_score=%d), want high=%d medium=%d low=%d",
				c.severity, got.HighRisk, got.MediumRisk, got.LowRisk, got.SecScore, c.high, c.med, c.low)
		}
	}
}
