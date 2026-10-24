"""Assemble the portable Windows folder from a prepared checkout (run by .github/workflows/windows.yml).

Expects, in the repository: vendor/Archipelago with the apworlds (scripts/fetch_apworlds.py) and frontend/dist (npm run
build). Copies only what the app needs at run time, next to a standalone Python that already holds the dependencies:

    ArchipelagoMultitracker/
      Multitracker.exe  LISEZMOI.txt
      python/  backend/  frontend/dist/  vendor/Archipelago/  scripts/windows/launcher.py
      config/  (apworlds.yaml, apworlds.lock.yaml, room.example.yaml, empty players/)

Never copied: config/room.yaml (room password), config/players/* (players' yamls), data/, tests, .git.

    python scripts/windows/build_portable.py --python build/python --exe build/Multitracker.exe --out build/dist
"""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
NAME = "ArchipelagoMultitracker"
CONFIG_FILES = ("apworlds.yaml", "apworlds.lock.yaml", "room.example.yaml")
IGNORE = shutil.ignore_patterns("__pycache__", "*.pyc", ".git", ".github", ".pytest_cache")


def assemble(root: Path, python: Path, exe: Path, out: Path) -> Path:
    for need in (root / "vendor" / "Archipelago", root / "frontend" / "dist" / "index.html", python / "python.exe", exe):
        if not need.exists():
            raise SystemExit(f"manquant : {need}")
    dest = out / NAME
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    shutil.copytree(python, dest / "python", ignore=IGNORE)
    shutil.copytree(root / "backend", dest / "backend", ignore=IGNORE)
    shutil.copytree(root / "frontend" / "dist", dest / "frontend" / "dist")
    shutil.copytree(root / "vendor" / "Archipelago", dest / "vendor" / "Archipelago", ignore=IGNORE)
    (dest / "scripts" / "windows").mkdir(parents=True)
    shutil.copy2(root / "scripts" / "windows" / "launcher.py", dest / "scripts" / "windows" / "launcher.py")
    (dest / "config" / "players").mkdir(parents=True)
    for name in CONFIG_FILES:
        shutil.copy2(root / "config" / name, dest / "config" / name)
    shutil.copy2(exe, dest / "Multitracker.exe")
    # CRLF: Notepad shows LF-only files on one line on older Windows versions.
    text = (root / "scripts" / "windows" / "LISEZMOI.txt").read_text(encoding="utf-8")
    (dest / "LISEZMOI.txt").write_bytes(text.replace("\r\n", "\n").replace("\n", "\r\n").encode("utf-8-sig"))
    return dest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--python", type=Path, required=True, help="standalone Python with the dependencies installed")
    parser.add_argument("--exe", type=Path, required=True, help="Multitracker.exe (scripts/windows/launcher.go)")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    dest = assemble(ROOT, args.python, args.exe, args.out)
    size = sum(f.stat().st_size for f in dest.rglob("*") if f.is_file())
    print(f"{dest} : {size / 1e6:.0f} Mo")
    return 0


if __name__ == "__main__":
    sys.exit(main())
