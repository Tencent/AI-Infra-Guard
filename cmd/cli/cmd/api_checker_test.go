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

package cmd

import (
	"os"
	"path/filepath"
	"testing"

	"github.com/stretchr/testify/require"
)

func TestIsAPICheckerDir(t *testing.T) {
	dir := t.TempDir()
	require.False(t, isAPICheckerDir(dir))
	for _, name := range []string{"main.py", "server.py", "requirements.txt"} {
		require.NoError(t, os.WriteFile(filepath.Join(dir, name), []byte("# test\n"), 0o600))
	}
	require.True(t, isAPICheckerDir(dir))
}

func TestFindAPICheckerDirFromEnvironment(t *testing.T) {
	dir := t.TempDir()
	for _, name := range []string{"main.py", "server.py", "requirements.txt"} {
		require.NoError(t, os.WriteFile(filepath.Join(dir, name), []byte("# test\n"), 0o600))
	}
	t.Setenv(apiCheckerDirEnv, dir)

	got, err := findAPICheckerDir()
	require.NoError(t, err)
	require.Equal(t, dir, got)
}

func TestFindAPICheckerDirRejectsInvalidEnvironment(t *testing.T) {
	t.Setenv(apiCheckerDirEnv, t.TempDir())

	_, err := findAPICheckerDir()
	require.ErrorContains(t, err, apiCheckerDirEnv)
}

func TestFindAPICheckerPythonMakesConfiguredPathAbsolute(t *testing.T) {
	dir := t.TempDir()
	python := filepath.Join(dir, "python")
	require.NoError(t, os.WriteFile(python, []byte("#!/bin/sh\n"), 0o700))

	cwd, err := os.Getwd()
	require.NoError(t, err)
	relative, err := filepath.Rel(cwd, python)
	require.NoError(t, err)
	t.Setenv(apiCheckerPythonEnv, relative)

	got, err := findAPICheckerPython()
	require.NoError(t, err)
	require.True(t, filepath.IsAbs(got))
	require.Equal(t, python, got)
}
