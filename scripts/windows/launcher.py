"""Launcher of the portable Windows build (started by Multitracker.exe, see scripts/windows/README.md).

Does what scripts/app.sh does on Linux, in the foreground: creates config/room.yaml from the example on the first
run, starts `python -m multitracker` with its output in data/logs/app.log (read by the Journal page), waits until it
answers, opens the browser and keeps running until the window is closed or Ctrl+C. Standard library only.

    python scripts/windows/launcher.py [--host 127.0.0.1] [--port 42753] [--no-browser] [--smoke] [--update]
                                       [-- app args]

Exit codes read by Multitracker.exe (scripts/windows/update.go): EXIT_UPDATE when the app staged a new version from
the Configuration page, EXIT_UPDATE_CLI after --update staged one, START_FAILED when the app never answered (after
an update, the exe then puts the previous version back).
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import time
import urllib.request
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LOG_LIMIT = 5 * 1024 * 1024  # rotated at start when over 5 MB, like scripts/app.sh
START_TIMEOUT = 180  # seconds: the first start of the logic engine loads every apworld
START_FAILED = 3
EXIT_UPDATE = 75  # = multitracker.updater.EXIT_UPDATE
EXIT_UPDATE_CLI = 76


def ensure_config(root: Path) -> bool:
    """Create config/room.yaml from the example when missing; True if it was created."""
    cfg = root / "config" / "room.yaml"
    if cfg.exists():
        return False
    shutil.copyfile(root / "config" / "room.example.yaml", cfg)
    return True


def rotate_log(log: Path, limit: int = LOG_LIMIT) -> None:
    if log.exists() and log.stat().st_size > limit:
        os.replace(log, log.with_name(log.name + ".1"))


def server_command(host: str, port: int, extra: list[str]) -> list[str]:
    return [sys.executable, "-m", "multitracker", "--host", host, "--port", str(port), *extra]


def server_env(root: Path) -> dict[str, str]:
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join(filter(None, [str(root / "backend"), env.get("PYTHONPATH")]))
    env["PYTHONUNBUFFERED"] = "1"
    env["PYTHONUTF8"] = "1"
    return env


def healthy(port: int) -> bool:
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/health", timeout=2) as resp:
            return resp.status == 200
    except OSError:
        return False


def log_tail(log: Path, lines: int = 20) -> str:
    try:
        return "\n".join(log.read_text(encoding="utf-8", errors="replace").splitlines()[-lines:])
    except OSError:
        return ""


def stop(proc: subprocess.Popen) -> None:
    if proc.poll() is not None:
        return
    proc.terminate()
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()


def version(root: Path) -> str:
    try:
        return (root / "VERSION").read_text(encoding="utf-8").strip()
    except OSError:
        return "?"


def stage_update(root: Path, port: int) -> bool:
    """--update: download the latest release into update/new/ (True when one is ready to install)."""
    if healthy(port):
        print("Le Multitracker tourne déjà : lance la mise à jour depuis la page Configuration (Mises à jour),")
        print("ou ferme son autre fenêtre puis relance Multitracker.exe --update.")
        return False
    sys.path.insert(0, str(root / "backend"))
    from multitracker.updater import stage_from_cli
    return stage_from_cli(root)


def launch(root: Path, host: str, port: int, extra: list[str], *, log: Path | None = None, browser: bool = True,
           smoke: bool = False) -> int:
    url = f"http://127.0.0.1:{port}"
    if healthy(port):
        print(f"Le Multitracker tourne déjà : {url}")
        if browser:
            webbrowser.open(url)
        return 0
    if "--config" not in extra and ensure_config(root):
        print("Première utilisation : config/room.yaml créé. Colle le lien de ta room dans la page Configuration.")
    log = log or root / "data" / "logs" / "app.log"
    log.parent.mkdir(parents=True, exist_ok=True)
    rotate_log(log)
    print(f"Démarrage du Multitracker {version(root)}…")
    with open(log, "ab") as out:
        proc = subprocess.Popen(server_command(host, port, extra), cwd=root, env=server_env(root),
                                stdin=subprocess.DEVNULL, stdout=out, stderr=subprocess.STDOUT)
    try:
        deadline = time.monotonic() + START_TIMEOUT
        while not healthy(port):
            if proc.poll() is not None:
                print(f"\nL'app s'est arrêtée (code {proc.returncode}). Fin du journal {log} :\n{log_tail(log)}")
                return START_FAILED
            if time.monotonic() > deadline:
                print(f"\nPas de réponse sur le port {port} après {START_TIMEOUT} s. Fin du journal :\n{log_tail(log)}")
                stop(proc)
                return START_FAILED
            time.sleep(1)
        print(f"\nMultitracker lancé : {url}")
        if host not in ("127.0.0.1", "localhost"):
            print(f"Accessible aussi depuis le réseau local (port {port}).")
        print("Garde cette fenêtre ouverte. La fermer (ou Ctrl+C) arrête l'app.")
        if smoke:
            return 0
        if browser:
            webbrowser.open(url)
        code = proc.wait()
        if code == EXIT_UPDATE:
            print("\nMise à jour : l'app s'arrête pour installer la nouvelle version…")
            return code
        if code:
            print(f"\nL'app s'est arrêtée (code {code}). Fin du journal {log} :\n{log_tail(log)}")
        return 1 if code in (START_FAILED, EXIT_UPDATE_CLI) else code  # those codes mean something to the exe
    except KeyboardInterrupt:
        print("\nArrêt…")
        return 0
    finally:
        stop(proc)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="Multitracker", description="Lance le Multitracker et ouvre le navigateur.")
    # Local only by default: listening on the network makes Windows ask for a firewall rule.
    parser.add_argument("--host", default=os.environ.get("MT_HOST", "127.0.0.1"),
                        help="0.0.0.0 pour l'ouvrir aux autres appareils du réseau (défaut : 127.0.0.1)")
    parser.add_argument("--port", type=int, default=int(os.environ.get("MT_PORT", "42753")))
    parser.add_argument("--no-browser", action="store_true", help="ne pas ouvrir le navigateur")
    parser.add_argument("--smoke", action="store_true", help="démarrer, vérifier que l'app répond, puis arrêter")
    parser.add_argument("--update", action="store_true", help="télécharger la dernière version, l'installer, démarrer")
    args, extra = parser.parse_known_args(argv)
    if extra[:1] == ["--"]:
        extra = extra[1:]
    if args.update and stage_update(ROOT, args.port):
        return EXIT_UPDATE_CLI  # Multitracker.exe installs it, then starts again without --update
    return launch(ROOT, args.host, args.port, extra, browser=not args.no_browser and not args.smoke, smoke=args.smoke)


if __name__ == "__main__":
    sys.exit(main())
