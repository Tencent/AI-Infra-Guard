//go:build unix

package utils

import (
	"archive/zip"
	"fmt"
	"os"
	"path/filepath"
	"syscall"
	"testing"
)

// ExtractZipFile must not keep every extracted file open until it returns: a
// wheel or skill archive with more entries than the open-file limit would
// otherwise fail with "too many open files".
func TestExtractZipFileClosesEachEntry(t *testing.T) {
	const entries = 300

	dir := t.TempDir()
	archive := filepath.Join(dir, "many.zip")
	f, err := os.Create(archive)
	if err != nil {
		t.Fatal(err)
	}
	zw := zip.NewWriter(f)
	for i := 0; i < entries; i++ {
		w, err := zw.Create(fmt.Sprintf("pkg/mod_%03d.py", i))
		if err != nil {
			t.Fatal(err)
		}
		fmt.Fprintf(w, "VALUE = %d\n", i)
	}
	if err := zw.Close(); err != nil {
		t.Fatal(err)
	}
	if err := f.Close(); err != nil {
		t.Fatal(err)
	}

	var old syscall.Rlimit
	if err := syscall.Getrlimit(syscall.RLIMIT_NOFILE, &old); err != nil {
		t.Skipf("getrlimit: %v", err)
	}
	limited := old
	limited.Cur = 128
	if err := syscall.Setrlimit(syscall.RLIMIT_NOFILE, &limited); err != nil {
		t.Skipf("setrlimit: %v", err)
	}
	defer syscall.Setrlimit(syscall.RLIMIT_NOFILE, &old)

	dest := filepath.Join(dir, "out")
	if err := ExtractZipFile(archive, dest); err != nil {
		t.Fatalf("ExtractZipFile: %v", err)
	}
	syscall.Setrlimit(syscall.RLIMIT_NOFILE, &old)

	for _, i := range []int{0, entries - 1} {
		got, err := os.ReadFile(filepath.Join(dest, "pkg", fmt.Sprintf("mod_%03d.py", i)))
		if err != nil {
			t.Fatal(err)
		}
		if want := fmt.Sprintf("VALUE = %d\n", i); string(got) != want {
			t.Fatalf("entry %d = %q, want %q", i, got, want)
		}
	}
}
