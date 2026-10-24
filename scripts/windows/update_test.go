package main

import (
	"os"
	"path/filepath"
	"reflect"
	"testing"
)

func write(t *testing.T, path, text string) {
	t.Helper()
	if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(path, []byte(text), 0o644); err != nil {
		t.Fatal(err)
	}
}

func read(t *testing.T, path string) string {
	t.Helper()
	b, err := os.ReadFile(path)
	if err != nil {
		t.Fatal(err)
	}
	return string(b)
}

func setup(t *testing.T) string {
	dir := t.TempDir()
	write(t, filepath.Join(dir, "VERSION"), "v0.1.0")
	write(t, filepath.Join(dir, "Multitracker.exe"), "old exe")
	write(t, filepath.Join(dir, "backend", "x.py"), "old")
	write(t, filepath.Join(dir, "gone", "y"), "only in the old version")
	write(t, filepath.Join(dir, "config", "room.yaml"), "mine")
	write(t, filepath.Join(dir, "config", "apworlds.yaml"), "old")
	write(t, filepath.Join(dir, "config", "players", "a.yaml"), "yaml")
	write(t, filepath.Join(dir, "data", "db"), "history")
	staged := filepath.Join(dir, "update", "new", portableDir)
	write(t, filepath.Join(staged, "VERSION"), "v0.2.0")
	write(t, filepath.Join(staged, "Multitracker.exe"), "new exe")
	write(t, filepath.Join(staged, "backend", "x.py"), "new")
	write(t, filepath.Join(staged, "backend", "z.py"), "new file")
	write(t, filepath.Join(staged, "config", "apworlds.yaml"), "new")
	write(t, filepath.Join(staged, "config", "players", "b.yaml"), "never copied")
	return dir
}

func TestInstallKeepsConfigAndData(t *testing.T) {
	dir := setup(t)
	s, err := install(dir)
	if err != nil {
		t.Fatal(err)
	}
	for rel, want := range map[string]string{
		"VERSION": "v0.2.0", "Multitracker.exe": "new exe", "backend/z.py": "new file", "config/apworlds.yaml": "new",
		"config/room.yaml": "mine", "config/players/a.yaml": "yaml", "data/db": "history", "gone/y": "only in the old version",
		"update/old/VERSION": "v0.1.0", "update/old/backend/x.py": "old", "update/old/config/apworlds.yaml": "old",
	} {
		if got := read(t, filepath.Join(dir, rel)); got != want {
			t.Errorf("%s = %q, want %q", rel, got, want)
		}
	}
	if _, err := os.Stat(filepath.Join(dir, "config", "players", "b.yaml")); err == nil {
		t.Error("players/ of the zip copied")
	}
	if _, err := os.Stat(filepath.Join(dir, "update", "new")); err == nil {
		t.Error("update/new left behind")
	}
	if err := s.rollback(); err != nil {
		t.Fatal(err)
	}
	for rel, want := range map[string]string{
		"VERSION": "v0.1.0", "Multitracker.exe": "old exe", "backend/x.py": "old", "config/apworlds.yaml": "old",
		"config/room.yaml": "mine", "data/db": "history", "update/failed/VERSION": "v0.2.0",
	} {
		if got := read(t, filepath.Join(dir, rel)); got != want {
			t.Errorf("after rollback %s = %q, want %q", rel, got, want)
		}
	}
	if _, err := os.Stat(filepath.Join(dir, "backend", "z.py")); err == nil {
		t.Error("new file still there after rollback")
	}
}

func TestInstallWithoutStagedVersion(t *testing.T) {
	dir := t.TempDir()
	write(t, filepath.Join(dir, "VERSION"), "v0.1.0")
	if _, err := install(dir); err == nil {
		t.Fatal("no error")
	}
	if read(t, filepath.Join(dir, "VERSION")) != "v0.1.0" {
		t.Fatal("changed")
	}
}

func TestRelaunchArgs(t *testing.T) {
	cases := []struct {
		in        []string
		noBrowser bool
		want      []string
	}{
		{[]string{"--update", "--port", "42800"}, false, []string{"--port", "42800"}},
		{[]string{"--host", "0.0.0.0"}, true, []string{"--host", "0.0.0.0", "--no-browser"}},
		{[]string{"--no-browser"}, true, []string{"--no-browser"}},
	}
	for _, c := range cases {
		if got := relaunchArgs(c.in, c.noBrowser); !reflect.DeepEqual(got, c.want) {
			t.Errorf("relaunchArgs(%v) = %v, want %v", c.in, got, c.want)
		}
	}
}
