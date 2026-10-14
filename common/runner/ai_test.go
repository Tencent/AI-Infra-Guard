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

package runner

import (
	"context"
	"errors"
	"io"
	"testing"

	"github.com/Tencent/AI-Infra-Guard/common/utils/models"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

type fakeScreenshotAnalysisModel struct {
	imageSummary string
	imageErr     error
	events       []models.ChatStreamEvent
	history      []map[string]string
}

func (m *fakeScreenshotAnalysisModel) ChatWithImageByte(context.Context, string, []byte) (string, error) {
	return m.imageSummary, m.imageErr
}

func (m *fakeScreenshotAnalysisModel) ChatStream(_ context.Context, history []map[string]string) <-chan models.ChatStreamEvent {
	m.history = history
	events := make(chan models.ChatStreamEvent, len(m.events))
	for _, event := range m.events {
		events <- event
	}
	close(events)
	return events
}

func TestAnalyzeScreenshotCleanStream(t *testing.T) {
	model := &fakeScreenshotAnalysisModel{
		imageSummary: "A public dashboard",
		events: []models.ChatStreamEvent{
			{Text: "<result><title> Dashboard access </title><details> Sensitive data "},
			{Text: "is visible </details><severity> high </severity><summary> Review access </summary></result>"},
		},
	}
	screenshot := []byte("screenshot")
	gotScreenshot, info, summary, err := analyzeScreenshot("https://example.test", "<html>Dashboard</html>", "en", screenshot, model)
	require.NoError(t, err)
	assert.Equal(t, screenshot, gotScreenshot)
	require.NotNil(t, info)
	assert.Equal(t, "Dashboard access", info.Summary)
	assert.Equal(t, "Sensitive data is visible", info.Details)
	assert.Equal(t, "high", info.Severity)
	assert.Equal(t, "Review access", summary)
	require.Len(t, model.history, 1)
	assert.Contains(t, model.history[0]["content"], "https://example.test")
	assert.Contains(t, model.history[0]["content"], "<html>Dashboard</html>")
	assert.Contains(t, model.history[0]["content"], model.imageSummary)
}

func TestAnalyzeScreenshotRejectsAbortedReport(t *testing.T) {
	completeLookingReport := "<result><title>Exposure</title><details>Data exposed</details><severity>high</severity><summary>Unsafe</summary></result>"
	for _, test := range []struct {
		name    string
		partial string
		err     error
	}{
		{name: "before output", err: errors.New("provider unavailable")},
		{name: "partial report", partial: "<result><title>Expos", err: io.ErrUnexpectedEOF},
		{name: "complete tags before abort", partial: completeLookingReport, err: io.ErrUnexpectedEOF},
		{name: "canceled after output", partial: "<result>", err: context.Canceled},
	} {
		t.Run(test.name, func(t *testing.T) {
			model := &fakeScreenshotAnalysisModel{
				imageSummary: "Screenshot description",
				events: []models.ChatStreamEvent{
					{Text: test.partial},
					{Err: test.err},
				},
			}
			screenshot := []byte("screenshot")
			gotScreenshot, info, partial, err := analyzeScreenshot("https://example.test", "", "en", screenshot, model)
			require.ErrorIs(t, err, test.err)
			assert.Equal(t, screenshot, gotScreenshot)
			assert.Nil(t, info, "an interrupted report must not become a vulnerability")
			assert.Equal(t, test.partial, partial, "partial output remains available only with an error")
		})
	}
}

func TestAnalyzeScreenshotImageFailure(t *testing.T) {
	wantErr := errors.New("image analysis failed")
	model := &fakeScreenshotAnalysisModel{imageSummary: "Partial image description", imageErr: wantErr}
	screenshot := []byte("screenshot")
	gotScreenshot, info, partial, err := analyzeScreenshot("https://example.test", "", "en", screenshot, model)
	require.ErrorIs(t, err, wantErr)
	assert.Equal(t, screenshot, gotScreenshot)
	assert.Nil(t, info)
	assert.Equal(t, model.imageSummary, partial)
	assert.Nil(t, model.history, "failed image analysis must not trigger report generation")
}
