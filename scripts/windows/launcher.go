// Multitracker.exe: starts the bundled Python on scripts/windows/launcher.py, next to this executable.
// Built for Windows by .github/workflows/windows.yml (go build -o Multitracker.exe launcher.go).
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

func main() {
	exe, err := os.Executable()
	if err != nil {
		fail(1, "Chemin de l'exécutable introuvable : %v", err)
	}
	dir := filepath.Dir(exe)
	py := filepath.Join(dir, "python", "python.exe")
	args := append([]string{"-X", "utf8", filepath.Join(dir, "scripts", "windows", "launcher.py")}, os.Args[1:]...)
	cmd := exec.Command(py, args...)
	cmd.Dir = dir
	cmd.Stdin, cmd.Stdout, cmd.Stderr = os.Stdin, os.Stdout, os.Stderr
	// Ctrl+C reaches every process of the console: let the Python launcher stop the app, then exit with it.
	signal.Ignore(os.Interrupt)
	if err := cmd.Run(); err != nil {
		var exit *exec.ExitError
		if errors.As(err, &exit) {
			fail(exit.ExitCode(), "")
		}
		fail(1, "Impossible de lancer %s : %v", py, err)
	}
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
