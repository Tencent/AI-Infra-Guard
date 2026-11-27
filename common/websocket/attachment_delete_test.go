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

package websocket

import (
	"fmt"
	"os"
	"path/filepath"
	"testing"

	"github.com/Tencent/AI-Infra-Guard/pkg/database"
	"github.com/stretchr/testify/require"
	"gorm.io/datatypes"
)

// TestDeleteSessionAttachmentsRemovesStoredFile: GetFileURL returns the secure
// on-disk name verbatim, so deleteSessionAttachments must delete that name
// directly. The old code reconstructed the original name first and skipped
// whenever the reconstruction was a no-op, orphaning every uploaded file.
func TestDeleteSessionAttachmentsRemovesStoredFile(t *testing.T) {
	tm, cleanupTM := newTestTaskManager(t)
	defer cleanupTM()

	uploadDir := t.TempDir()
	tm.fileConfig = &FileUploadConfig{UploadDir: uploadDir}

	stored := generateSecureFileName("report.pdf")
	storedPath := filepath.Join(uploadDir, stored)
	require.NoError(t, os.WriteFile(storedPath, []byte("payload"), 0644))

	// A "../" entry must not let the caller delete files outside the upload dir.
	outside := filepath.Join(filepath.Dir(uploadDir), "outside.txt")
	require.NoError(t, os.WriteFile(outside, []byte("keep"), 0644))

	attachments := fmt.Sprintf(`[%q, %q]`, stored, "../../outside.txt")
	session := &database.Session{Attachments: datatypes.JSON([]byte(attachments))}

	require.NoError(t, tm.deleteSessionAttachments(session))

	if _, err := os.Stat(storedPath); !os.IsNotExist(err) {
		t.Fatal("uploaded attachment was not deleted from disk")
	}
	if _, err := os.Stat(outside); err != nil {
		t.Fatal("attachment deletion escaped the upload directory")
	}
}
