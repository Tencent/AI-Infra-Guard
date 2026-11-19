package utils

import (
	"net"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"strings"
	"testing"
	"time"
)

// A clone that hits its timeout must not leak the goroutine that waits for
// git, and must not leave a partial checkout behind: git refuses to clone
// into a non-empty directory, so a leftover would make every retry fail.
func TestGitCloneTimeoutCleansUpAndDoesNotLeak(t *testing.T) {
	if _, err := exec.LookPath("git"); err != nil {
		t.Skip("git not installed")
	}
	// A server that accepts connections and never answers.
	ln, err := net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		t.Fatal(err)
	}
	defer ln.Close()
	go func() {
		for {
			conn, err := ln.Accept()
			if err != nil {
				return
			}
			defer conn.Close()
		}
	}()

	target := filepath.Join(t.TempDir(), "repo")
	before := runtime.NumGoroutine()
	err = GitClone("http://"+ln.Addr().String()+"/repo.git", target, 300*time.Millisecond)
	if err == nil {
		t.Fatal("GitClone succeeded against a server that never answers")
	}
	if !strings.Contains(err.Error(), "操作超时") {
		t.Errorf("GitClone error = %q, want the timeout error from every attempt", err)
	}
	if _, statErr := os.Stat(target); !os.IsNotExist(statErr) {
		t.Errorf("partial clone left at %s (stat err %v)", target, statErr)
	}

	deadline := time.Now().Add(5 * time.Second)
	for runtime.NumGoroutine() > before && time.Now().Before(deadline) {
		time.Sleep(20 * time.Millisecond)
	}
	if after := runtime.NumGoroutine(); after > before {
		t.Errorf("goroutines: %d before GitClone, %d after", before, after)
	}
}

func TestGitCloneClonesLocalRepository(t *testing.T) {
	if _, err := exec.LookPath("git"); err != nil {
		t.Skip("git not installed")
	}
	src := t.TempDir()
	for _, args := range [][]string{
		{"init", "-q"},
		{"-c", "user.name=t", "-c", "user.email=t@example.invalid", "commit", "-q", "--allow-empty", "-m", "init"},
	} {
		cmd := exec.Command("git", args...)
		cmd.Dir = src
		if out, err := cmd.CombinedOutput(); err != nil {
			t.Fatalf("git %v: %v\n%s", args, err, out)
		}
	}
	target := filepath.Join(t.TempDir(), "clone")
	if err := GitClone(src, target, time.Minute); err != nil {
		t.Fatalf("GitClone: %v", err)
	}
	if _, err := os.Stat(filepath.Join(target, ".git")); err != nil {
		t.Fatalf("clone has no .git: %v", err)
	}
}
