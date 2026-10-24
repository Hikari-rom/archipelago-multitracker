package main

// Installs the version the app extracted into update/new/ArchipelagoMultitracker (backend/multitracker/updater.py),
// once Python has exited: each top entry replaces the current one, which goes to update/old. In config/ only the
// files of the zip are replaced (apworlds.yaml, apworlds.lock.yaml, room.example.yaml): room.yaml, players/ and
// data/ stay. Windows lets a running executable be renamed, so Multitracker.exe is replaced like the rest.

import (
	"fmt"
	"os"
	"path/filepath"
	"time"
)

const portableDir = "ArchipelagoMultitracker"

type moved struct {
	rel    string
	hadOld bool
}

type swap struct {
	dir  string
	done []moved
}

func install(dir string) (*swap, error) {
	staged := filepath.Join(dir, "update", "new", portableDir)
	if _, err := os.Stat(filepath.Join(staged, "VERSION")); err != nil {
		return nil, fmt.Errorf("aucune version prête dans update\\new")
	}
	old := filepath.Join(dir, "update", "old")
	if err := os.RemoveAll(old); err != nil {
		return nil, err
	}
	if err := os.MkdirAll(filepath.Join(old, "config"), 0o755); err != nil {
		return nil, err
	}
	entries, err := os.ReadDir(staged)
	if err != nil {
		return nil, err
	}
	s := &swap{dir: dir}
	for _, e := range entries {
		var rels []string
		switch {
		case e.Name() == "data":
			continue
		case e.Name() == "config" && e.IsDir():
			files, err := os.ReadDir(filepath.Join(staged, "config"))
			if err != nil {
				return nil, s.abort(err)
			}
			for _, f := range files {
				if !f.IsDir() {
					rels = append(rels, filepath.Join("config", f.Name()))
				}
			}
		default:
			rels = []string{e.Name()}
		}
		for _, rel := range rels {
			if err := s.replace(staged, rel); err != nil {
				return nil, s.abort(err)
			}
		}
	}
	os.RemoveAll(filepath.Join(dir, "update", "new"))
	return s, nil
}

func (s *swap) replace(staged, rel string) error {
	cur := filepath.Join(s.dir, rel)
	bak := filepath.Join(s.dir, "update", "old", rel)
	_, statErr := os.Lstat(cur)
	hadOld := statErr == nil
	if hadOld {
		if err := rename(cur, bak); err != nil {
			return err
		}
	}
	if err := rename(filepath.Join(staged, rel), cur); err != nil {
		if hadOld {
			rename(bak, cur)
		}
		return err
	}
	s.done = append(s.done, moved{rel, hadOld})
	return nil
}

// abort puts back what was already replaced and returns err.
func (s *swap) abort(err error) error {
	if rerr := s.rollback(); rerr != nil {
		return fmt.Errorf("%v (et retour impossible : %v)", err, rerr)
	}
	return err
}

// rollback moves the new files to update/failed and the old ones back.
func (s *swap) rollback() error {
	failed := filepath.Join(s.dir, "update", "failed")
	os.RemoveAll(failed)
	if err := os.MkdirAll(filepath.Join(failed, "config"), 0o755); err != nil {
		return err
	}
	var first error
	for i := len(s.done) - 1; i >= 0; i-- {
		m := s.done[i]
		cur := filepath.Join(s.dir, m.rel)
		if err := rename(cur, filepath.Join(failed, m.rel)); err != nil {
			if first == nil {
				first = err
			}
			continue
		}
		if m.hadOld {
			if err := rename(filepath.Join(s.dir, "update", "old", m.rel), cur); err != nil && first == nil {
				first = err
			}
		}
	}
	s.done = nil
	return first
}

// rename retries for a few seconds: an antivirus may still hold a file just after the app stopped.
func rename(from, to string) error {
	var err error
	for i := 0; i < 20; i++ {
		if err = os.Rename(from, to); err == nil {
			return nil
		}
		time.Sleep(500 * time.Millisecond)
	}
	return err
}
