"""scripts/app.sh start, on a stand-in app (a copy of the script in a temporary repo)."""
import os
import shutil
import signal
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PORT = 38293


@pytest.fixture
def fake_repo(tmp_path):
    (tmp_path / "scripts").mkdir()
    shutil.copy(ROOT / "scripts" / "app.sh", tmp_path / "scripts" / "app.sh")
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "room.yaml").write_text("server: x\n")
    (tmp_path / "frontend" / "dist").mkdir(parents=True)
    (tmp_path / "frontend" / "dist" / "index.html").write_text("")
    (tmp_path / "www" / "api").mkdir(parents=True)
    (tmp_path / "www" / "api" / "health").write_text("ok")
    (tmp_path / ".venv" / "bin").mkdir(parents=True)
    yield tmp_path
    pid_file = tmp_path / ".run" / "app.pid"
    if pid_file.exists():
        try:
            os.kill(int(pid_file.read_text()), signal.SIGKILL)
        except (ProcessLookupError, ValueError):
            pass


def fake_python(repo: Path, body: str) -> None:
    path = repo / ".venv" / "bin" / "python"
    path.write_text("#!/bin/bash\n" + body)
    path.chmod(0o755)


def app_sh(repo: Path, *args: str) -> subprocess.CompletedProcess:
    env = {**os.environ, "MT_PORT": str(PORT), "MT_HOST": "127.0.0.1"}
    return subprocess.run(["bash", str(repo / "scripts" / "app.sh"), *args], cwd=repo, capture_output=True, text=True,
                          timeout=90, env=env)


def test_start_waits_for_an_app_whose_command_line_is_not_the_final_one_yet(fake_repo):
    """A starting app is not dead because its command line is not yet `.venv/bin/python -m multitracker` (the
    restart of an update reported a failure while the app was starting: 2026-11-10)."""
    fake_python(fake_repo, f'sleep 1\nexec python3 -m http.server {PORT} --bind 127.0.0.1 --directory "{fake_repo}/www"\n')
    res = app_sh(fake_repo, "start")
    assert res.returncode == 0, res.stdout + res.stderr
    assert "lancé" in res.stdout
    pid = int((fake_repo / ".run" / "app.pid").read_text())
    os.kill(pid, 0)  # still running


def test_start_reports_an_app_that_stops(fake_repo):
    fake_python(fake_repo, "echo boom\nexit 1\n")
    res = app_sh(fake_repo, "start")
    assert res.returncode == 1
    assert "s'est arrêtée" in res.stdout
    assert not (fake_repo / ".run" / "app.pid").exists()
