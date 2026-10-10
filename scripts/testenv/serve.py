#!/usr/bin/env python3
"""Host a TEST multiworld with Archipelago's MultiServer on 127.0.0.1 (test code only).

  serve.py start AP_xxx.zip [--port 38281] [--password test] [--keep-save]
  serve.py stop  [--port 38281]
  serve.py status [--port 38281]

The server PID is stored in .run/testserver-<port>.pid, its log in test-output/server-<port>.log.
Only ports 38281-38290 are allowed. Saves are disabled unless --keep-save (fresh state each run).
"""
from __future__ import annotations

import argparse
import os
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from multitracker import apenv  # noqa: E402

RUN = ROOT / ".run"
LOGS = ROOT / "test-output"
PORTS = range(38281, 38291)


def pid_file(port: int) -> Path:
    return RUN / f"testserver-{port}.pid"


def is_our_server(pid: int, port: int) -> bool:
    """True only if pid is a MultiServer we started on this port (guards against recycled PIDs)."""
    try:
        cmdline = Path(f"/proc/{pid}/cmdline").read_bytes().split(b"\0")
        return (any(arg.endswith(b"MultiServer.py") for arg in cmdline) and str(port).encode() in cmdline
                and os.getpgid(pid) == pid)
    except (OSError, ProcessLookupError):
        return False


def read_pid(port: int) -> int | None:
    try:
        pid = int(pid_file(port).read_text().strip())
    except (OSError, ValueError):
        return None
    if not is_our_server(pid, port):
        pid_file(port).unlink(missing_ok=True)  # stale or recycled pid: never kill it
        return None
    return pid


def port_open(port: int) -> bool:
    with socket.socket() as sock:
        sock.settimeout(0.5)
        return sock.connect_ex(("127.0.0.1", port)) == 0


def start(multidata: Path, port: int, password: str, keep_save: bool, timeout: float = 120) -> int:
    if read_pid(port):
        raise SystemExit(f"a test server is already running on port {port} (pid {read_pid(port)})")
    if port_open(port):
        raise SystemExit(f"port {port} is already in use by another process")
    RUN.mkdir(exist_ok=True)
    LOGS.mkdir(exist_ok=True)
    cmd = [sys.executable, str(apenv.AP_DIR / "MultiServer.py"), str(multidata.resolve()),
           "--host", "127.0.0.1", "--port", str(port), "--password", password,
           "--location_check_points", "1", "--hint_cost", "0",
           "--release_mode", "goal", "--collect_mode", "goal", "--loglevel", "info"]
    if not keep_save:
        cmd.append("--disable_save")
    log = open(LOGS / f"server-{port}.log", "wb")
    proc = subprocess.Popen(cmd, cwd=apenv.AP_DIR, env=apenv.subprocess_env(), stdin=subprocess.DEVNULL,
                            stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
    pid_file(port).write_text(str(proc.pid))
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            pid_file(port).unlink(missing_ok=True)
            raise SystemExit(f"server exited with code {proc.returncode}, see {log.name}")
        if port_open(port):
            return proc.pid
        time.sleep(0.5)
    stop(port)
    raise SystemExit(f"server did not open port {port} within {timeout}s")


def stop(port: int) -> bool:
    pid = read_pid(port)
    if not pid:
        return False
    try:
        os.killpg(pid, signal.SIGTERM)
        for _ in range(50):
            if not is_our_server(pid, port):
                break
            time.sleep(0.1)
        else:
            os.killpg(pid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError):
        pass
    pid_file(port).unlink(missing_ok=True)
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("action", choices=["start", "stop", "status"])
    parser.add_argument("multidata", nargs="?", type=Path)
    parser.add_argument("--port", type=int, default=38281)
    parser.add_argument("--password", default="test")
    parser.add_argument("--keep-save", action="store_true")
    args = parser.parse_args()
    if args.port not in PORTS:
        parser.error("port must be in 38281-38290")
    if args.action == "start":
        if not args.multidata:
            parser.error("start needs the AP_*.zip (or .archipelago) to host")
        pid = start(args.multidata, args.port, args.password, args.keep_save)
        print(f"test server pid {pid} on ws://127.0.0.1:{args.port}")
    elif args.action == "stop":
        print("stopped" if stop(args.port) else "not running")
    else:
        pid = read_pid(args.port)
        print(f"running (pid {pid})" if pid else "not running")
    return 0


if __name__ == "__main__":
    sys.exit(main())
