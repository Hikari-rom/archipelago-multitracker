// Multitracker.exe: starts the bundled Python on scripts/windows/launcher.py, next to this executable, and installs
// the updates the app downloaded (update.go). Built for Windows by .github/workflows/windows.yml (go build).
package main

import (
	"bufio"
	"errors"
	"fmt"
	"os"
	"os/exec"
	"os/signal"
	"path/filepath"
)

// Exit codes of scripts/windows/launcher.py.
const (
	startFailed   = 3  // the app never answered
	exitUpdate    = 75 // the app staged a new version (Configuration page)
	exitUpdateCLI = 76 // --update staged a new version
)

func main() {
	exe, err := os.Executable()
	if err != nil {
		fail(1, "Chemin de l'exécutable introuvable : %v", err)
	}
	dir := filepath.Dir(exe)
	// Ctrl+C reaches every process of the console: let the Python launcher stop the app, then exit with it.
	signal.Ignore(os.Interrupt)
	args := os.Args[1:]
	var installed *swap // the last update, until the new version has started
	for {
		code := run(dir, args)
		switch {
		case code == startFailed && installed != nil:
			fmt.Println("\nLa nouvelle version ne démarre pas : retour à la version précédente.")
			if err := installed.rollback(); err != nil {
				fail(1, "Retour impossible : %v\nLa version précédente est dans le dossier update\\old.", err)
			}
			installed = nil
			continue
		case code == exitUpdate || code == exitUpdateCLI:
			// from the page, the browser is already open on the app: it reloads by itself
			args = relaunchArgs(args, code == exitUpdate)
			fmt.Println("\nInstallation de la mise à jour…")
			s, err := install(dir)
			if err != nil {
				fmt.Printf("Mise à jour impossible : %v\nL'app redémarre sur la version actuelle.\n", err)
				installed = nil
			} else {
				installed = s
			}
			continue
		}
		if code != 0 {
			fail(code, "")
		}
		return
	}
}

// run starts the Python launcher (the current one: an update replaces it) and returns its exit code.
func run(dir string, args []string) int {
	py := filepath.Join(dir, "python", "python.exe")
	cmd := exec.Command(py, append([]string{"-X", "utf8", filepath.Join(dir, "scripts", "windows", "launcher.py")}, args...)...)
	cmd.Dir = dir
	cmd.Stdin, cmd.Stdout, cmd.Stderr = os.Stdin, os.Stdout, os.Stderr
	if err := cmd.Run(); err != nil {
		var exit *exec.ExitError
		if errors.As(err, &exit) {
			return exit.ExitCode()
		}
		fail(1, "Impossible de lancer %s : %v", py, err)
	}
	return 0
}

func relaunchArgs(args []string, noBrowser bool) []string {
	out := []string{}
	has := false
	for _, a := range args {
		if a == "--update" {
			continue
		}
		has = has || a == "--no-browser"
		out = append(out, a)
	}
	if noBrowser && !has {
		out = append(out, "--no-browser")
	}
	return out
}

// fail keeps the console open so that a double-clicked window does not vanish before the message is read.
func fail(code int, format string, a ...any) {
	if format != "" {
		fmt.Printf(format+"\n", a...)
	}
	fmt.Print("\nAppuie sur Entrée pour fermer cette fenêtre.")
	bufio.NewReader(os.Stdin).ReadString('\n')
	os.Exit(code)
}
