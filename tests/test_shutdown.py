"""The app stops quickly even while a page keeps its event stream open (python -m multitracker, real server).

Multitracker.exe installs an update only once the old app has exited: an open /api/events (any open page) used to
keep uvicorn "waiting for connections to close" for as long as the browser held it.
"""
import os
import signal
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PORT = 38294


def wait_healthy(proc: subprocess.Popen, timeout: float = 60.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        assert proc.poll() is None, "the app stopped while starting"
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{PORT}/api/health", timeout=2):
                return
        except OSError:
            time.sleep(0.3)
    raise AssertionError("the app never answered")


def test_app_exits_while_an_event_stream_is_open(tmp_path):
    room = tmp_path / "room.yaml"
    room.write_text('server: "127.0.0.1:9"\npassword: ""\nwake_room: false\nslots: []\n')
    env = {**os.environ, "PYTHONPATH": str(ROOT / "backend")}
    proc = subprocess.Popen([sys.executable, "-m", "multitracker", "--host", "127.0.0.1", "--port", str(PORT),
                             "--config", str(room), "--db", str(tmp_path / "t.db"), "--no-logic"],
                            cwd=ROOT / "backend", env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    client = None
    try:
        wait_healthy(proc)
        client = socket.create_connection(("127.0.0.1", PORT))
        client.sendall(b"GET /api/events HTTP/1.1\r\nHost: x\r\nAccept: text/event-stream\r\n\r\n")
        client.settimeout(10)
        assert b"200 OK" in client.recv(4096)
        started = time.monotonic()
        proc.send_signal(signal.SIGINT)  # same path as an update: uvicorn's should_exit
        proc.wait(timeout=20)
        assert time.monotonic() - started < 10
    finally:
        if client is not None:
            client.close()
        if proc.poll() is None:
            proc.kill()
            proc.wait()
