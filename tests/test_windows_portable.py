"""Portable Windows build (scripts/windows/): launcher and folder assembly, checked on Linux.
The Windows side itself (standalone Python, Multitracker.exe, apworlds) runs in .github/workflows/windows.yml."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PORT = 38291


def _load(name: str):
    spec = importlib.util.spec_from_file_location(f"win_{name}", ROOT / "scripts" / "windows" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


launcher = _load("launcher")
build = _load("build_portable")


def test_first_run_creates_room_yaml_from_the_example(tmp_path):
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "room.example.yaml").write_text("room_url: x\n")
    assert launcher.ensure_config(tmp_path) is True
    assert (tmp_path / "config" / "room.yaml").read_text() == "room_url: x\n"
    (tmp_path / "config" / "room.yaml").write_text("room_url: mine\n")
    assert launcher.ensure_config(tmp_path) is False
    assert (tmp_path / "config" / "room.yaml").read_text() == "room_url: mine\n"


def test_log_rotation(tmp_path):
    log = tmp_path / "app.log"
    log.write_text("x" * 20)
    launcher.rotate_log(log, limit=100)
    assert log.exists()
    launcher.rotate_log(log, limit=10)
    assert not log.exists() and (tmp_path / "app.log.1").read_text() == "x" * 20


def test_server_command_and_env(tmp_path):
    cmd = launcher.server_command("127.0.0.1", 42753, ["--no-logic"])
    assert cmd == [sys.executable, "-m", "multitracker", "--host", "127.0.0.1", "--port", "42753", "--no-logic"]
    env = launcher.server_env(tmp_path)
    assert env["PYTHONPATH"].split(":")[0] == str(tmp_path / "backend")
    assert env["PYTHONUTF8"] == "1"


def test_launch_starts_the_app_and_stops_it(tmp_path):
    cfg = tmp_path / "room.yaml"
    cfg.write_text('server: "127.0.0.1:1"\nslots: []\n')  # unreachable: no network, the app still answers
    log = tmp_path / "logs" / "app.log"
    extra = ["--no-logic", "--config", str(cfg), "--db", str(tmp_path / "db.sqlite3")]
    assert launcher.launch(ROOT, "127.0.0.1", PORT, extra, log=log, browser=False, smoke=True) == 0
    assert not launcher.healthy(PORT)  # stopped on the way out
    assert "Uvicorn running" in log.read_text()


def test_launch_reports_an_app_that_exits(tmp_path, capsys):
    log = tmp_path / "app.log"
    extra = ["--no-logic", "--config", str(tmp_path / "missing.yaml"), "--db", str(tmp_path / "db.sqlite3")]
    assert launcher.launch(ROOT, "127.0.0.1", PORT, extra + ["--bogus-flag"], log=log, browser=False) == 1
    assert "L'app s'est arrêtée" in capsys.readouterr().out


def _fake_checkout(root: Path) -> None:
    files = {
        "backend/multitracker/__init__.py": "",
        "backend/multitracker/__pycache__/x.pyc": "",
        "frontend/dist/index.html": "<html>",
        "frontend/src/main.ts": "",
        "vendor/Archipelago/MultiServer.py": "",
        "vendor/Archipelago/.git/HEAD": "",
        "vendor/Archipelago/custom_worlds/celeste.apworld": "",
        "scripts/windows/launcher.py": "",
        "scripts/windows/LISEZMOI.txt": "ligne 1\nligne 2\n",
        "config/apworlds.yaml": "", "config/apworlds.lock.yaml": "", "config/room.example.yaml": "",
        "config/room.yaml": "password: secret", "config/room_players.yaml": "",
        "config/players/romain/romain_kh2.yaml": "name: romain_kh2",
        "data/multitracker.sqlite3": "",
        "tests/test_x.py": "",
    }
    for rel, text in files.items():
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text(text)


def test_portable_folder_has_what_the_app_needs_and_nothing_personal(tmp_path):
    root, py, out = tmp_path / "repo", tmp_path / "python", tmp_path / "out"
    _fake_checkout(root)
    (py / "Lib").mkdir(parents=True)
    (py / "python.exe").write_text("")
    exe = tmp_path / "Multitracker.exe"
    exe.write_text("")
    dest = build.assemble(root, py, exe, out)
    got = {p.relative_to(dest).as_posix() for p in dest.rglob("*") if p.is_file()}
    assert got == {
        "Multitracker.exe", "LISEZMOI.txt", "python/python.exe", "backend/multitracker/__init__.py",
        "frontend/dist/index.html", "vendor/Archipelago/MultiServer.py", "vendor/Archipelago/custom_worlds/celeste.apworld",
        "scripts/windows/launcher.py", "config/apworlds.yaml", "config/apworlds.lock.yaml", "config/room.example.yaml",
    }
    assert (dest / "config" / "players").is_dir()
    assert (dest / "LISEZMOI.txt").read_bytes() == "﻿ligne 1\r\nligne 2\r\n".encode("utf-8")
