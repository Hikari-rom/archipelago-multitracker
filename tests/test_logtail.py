"""Log file follower behind the "Journal" page (/api/logs/stream)."""
from __future__ import annotations

import os

from multitracker.logtail import Follower, last_lines, mask


def test_last_lines_keeps_complete_lines_only(tmp_path):
    log = tmp_path / "app.log"
    log.write_text("a\nb\nc\npartial")
    lines, offset, inode = last_lines(log, 2)
    assert lines == ["b", "c"]
    assert offset == len("a\nb\nc\n") and inode == os.stat(log).st_ino
    assert last_lines(tmp_path / "missing.log", 5) == ([], 0, 0)


def test_follower_reads_appended_lines_and_finishes_partial_ones(tmp_path):
    log = tmp_path / "app.log"
    log.write_text("old\n")
    _, offset, inode = last_lines(log, 10)
    f = Follower(log, offset, inode)
    assert f.poll() == (False, [])
    with open(log, "a") as fh:
        fh.write("one\ntw")
    assert f.poll() == (False, ["one"])
    with open(log, "a") as fh:
        fh.write("o\n")
    assert f.poll() == (False, ["two"])


def test_follower_restarts_after_rotation_or_truncation(tmp_path):
    log = tmp_path / "app.log"
    log.write_text("x\n" * 5)
    _, offset, inode = last_lines(log, 10)
    f = Follower(log, offset, inode)
    log.rename(tmp_path / "app.log.1")  # scripts/app.sh rotates at start
    log.write_text("new\n")
    assert f.poll() == (True, ["new"])
    log.write_text("")  # truncated (seen when the file is shorter than what was read, like tail -f)
    assert f.poll() == (True, [])
    with open(log, "a") as fh:
        fh.write("again\n")
    assert f.poll() == (False, ["again"])


def test_follower_waits_for_a_file_that_does_not_exist_yet(tmp_path):
    log = tmp_path / "app.log"
    f = Follower(log, 0, 0)
    assert f.poll() == (False, [])
    log.write_text("first\n")
    assert f.poll() == (False, ["first"])


def test_mask_hides_the_room_password():
    assert mask(["password=hunter22 here"], ["hunter22", ""]) == ["password=••• here"]
    assert mask(["ab"], [""]) == ["ab"]


async def test_log_stream_api(tmp_path):
    """/api/logs/stream: last lines, then appended ones, password masked."""
    import asyncio
    import json
    import socket

    import httpx
    import uvicorn
    from multitracker import api
    from multitracker.config import RoomConfig
    from multitracker.service import Service
    from multitracker.store import Store

    log = tmp_path / "app.log"
    log.write_text("old 1\nold 2\nconnect with s3cret-pw\n")
    cfg = RoomConfig(server="ws://127.0.0.1:9", password="s3cret-pw")
    app = api.create_app(lambda: Service(cfg, Store(tmp_path / "db.sqlite3"), reconnect_delays=(30.0,)),
                         frontend_dist=None, log_file=log)
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    uv = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning"))
    task = asyncio.create_task(uv.serve())
    try:
        while not uv.started:
            await asyncio.sleep(0.05)
        async with httpx.AsyncClient(base_url=f"http://127.0.0.1:{port}", timeout=10) as client:
            async with client.stream("GET", "/api/logs/stream", params={"lines": 2}) as resp:
                assert resp.headers["content-type"].startswith("text/event-stream")
                lines = resp.aiter_lines()

                async def next_event():
                    event = {}
                    async for line in lines:
                        if line.startswith("event:"):
                            event["type"] = line.split(":", 1)[1].strip()
                        elif line.startswith("data:"):
                            event["data"] = json.loads(line.split(":", 1)[1])
                        elif line == "" and event:
                            return event

                first = await asyncio.wait_for(next_event(), 10)
                assert first == {"type": "init", "data": {"lines": ["old 2", "connect with •••"], "missing": False}}
                with open(log, "a") as fh:
                    fh.write("new line\n")
                assert await asyncio.wait_for(next_event(), 10) == {"type": "lines", "data": {"lines": ["new line"]}}
    finally:
        uv.should_exit = True
        await asyncio.wait_for(task, 15)
