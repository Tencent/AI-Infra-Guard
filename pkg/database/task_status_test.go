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

package database

import (
	"fmt"
	"testing"

	"github.com/stretchr/testify/require"
	"gorm.io/datatypes"
)

func TestGetSessionStatusReadsOnlyStatus(t *testing.T) {
	store, _, cleanup := newTestDB(t)
	defer cleanup()

	require.NoError(t, store.CreateSession(&Session{
		ID:       "status-session",
		Username: "public_user",
		TaskType: "mcp_scan",
		Content:  "test",
		Status:   "doing",
	}))
	for i := 0; i < 100; i++ {
		require.NoError(t, store.CreateTaskMessage(&TaskMessage{
			ID:        fmt.Sprintf("msg-%d", i),
			SessionID: "status-session",
			Type:      "statusUpdate",
			EventData: datatypes.JSON([]byte(`{}`)),
			Timestamp: int64(i),
		}))
	}

	status, err := store.GetSessionStatus("status-session")
	require.NoError(t, err)
	require.Equal(t, "doing", status)

	_, err = store.GetSessionStatus("missing-session")
	require.Error(t, err)
}
