package websocket

import (
	"context"
	"encoding/json"
	"os/exec"
	"testing"
)

func TestRunEngineInfra(t *testing.T) {
	if _, err := exec.LookPath("node"); err != nil {
		t.Skip("node is not installed")
	}
	if _, _, err := engineCLI(); err != nil {
		t.Skip(err.Error())
	}
	out, err := runEngine(context.Background(), []byte(`{"plugins":["infra-scan"],"inputs":{"target":"10.2.0.0/24"}}`))
	if err != nil {
		t.Fatal(err)
	}
	var report struct {
		Plugins []struct {
			Plugin   string `json:"plugin"`
			Findings []struct {
				Prompt string `json:"prompt"`
				Reason string `json:"reason"`
			} `json:"findings"`
		} `json:"plugins"`
	}
	if err := json.Unmarshal(out, &report); err != nil {
		t.Fatal(err)
	}
	if len(report.Plugins) != 1 || report.Plugins[0].Plugin != "infra-scan" {
		t.Fatalf("plugin = %+v", report.Plugins)
	}
	if len(report.Plugins[0].Findings) != 1 || report.Plugins[0].Findings[0].Prompt != "10.2.0.0/24" {
		t.Fatalf("findings = %+v", report.Plugins[0].Findings)
	}
	if report.Plugins[0].Findings[0].Reason != "已记录目标，未发起请求" {
		t.Fatalf("reason = %s", report.Plugins[0].Findings[0].Reason)
	}
}
