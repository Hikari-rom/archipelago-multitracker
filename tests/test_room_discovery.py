"""M8: archipelago.gg room discovery and port changes, against a fake WebHost + the local test server."""
from __future__ import annotations

import asyncio
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from testenv_helpers import generated_seed, start_server, stop_server

PORT_A, PORT_B = 38285, 38286
ROOM_ID = "AbCdEfGhIjKlMnOp"


class FakeWebHost:
    """Serves /room/<id> and /api/room_status/<id> like archipelago.gg."""

    def __init__(self) -> None:
        self.port_value: int | None = PORT_A
        self.wakes = 0
        self.last_activity: str | None = None  # e.g. "Sat, 11 Oct 2026 00:00:00 GMT"
        self.timeout = 7200
        self.tracker_value: object = "yQdtVUWGRFaaMCu14kdq8A"  # WebHost tracker id (a non-string/absent value is tested)
        self.send_tracker = True
        fake = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_GET(self):
                if self.path == f"/room/{ROOM_ID}":
                    fake.wakes += 1
                    fake.last_activity = None  # loading the room page starts it
                    body, ctype = b"<html>room</html>", "text/html"
                elif self.path == f"/api/room_status/{ROOM_ID}":
                    status = {"players": [["Celeste", "Celeste (Open World)"], ["KH2", "Kingdom Hearts 2"],
                                          ["Jak", "Jak and Daxter: The Precursor Legacy"],
                                          ["TWWHD", "The Wind Waker HD"], ["SM64", "Super Mario 64"]],
                              "last_port": fake.port_value, "downloads": [],
                              "last_activity": fake.last_activity, "timeout": fake.timeout}
                    if fake.send_tracker:
                        status["tracker"] = fake.tracker_value
                    body = json.dumps(status).encode()
                    ctype = "application/json"
                else:
                    self.send_response(404)
                    self.end_headers()
                    return
                self.send_response(200)
                self.send_header("Content-Type", ctype)
                self.end_headers()
                self.wfile.write(body)

        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self.httpd.server_address[1]}/room/{ROOM_ID}"
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()

    def close(self) -> None:
        self.httpd.shutdown()


@pytest.fixture
def webhost(monkeypatch):
    monkeypatch.setenv("MT_ROOM_HOSTS", "127.0.0.1")  # the fake WebHost runs locally over http
    fake = FakeWebHost()
    yield fake
    fake.close()


def test_parse_room_url():
    from multitracker.room import RoomError, parse_room_url
    assert parse_room_url("https://archipelago.gg/room/AbCdEfGhIjKl") == ("https://archipelago.gg", "archipelago.gg",
                                                                           "AbCdEfGhIjKl")
    for bad in ("archipelago.gg/room/x", "https://archipelago.gg/seed/AbCdEfGhIjKl", "ftp://a/room/AbCdEfGhIjKl"):
        with pytest.raises(RoomError):
            parse_room_url(bad)


async def test_fetch_room_lists_slots_and_port(webhost):
    from multitracker.room import fetch_room
    info = await asyncio.to_thread(fetch_room, webhost.url, 5.0, True)
    assert info.server == f"127.0.0.1:{PORT_A}"
    assert ("KH2", "Kingdom Hearts 2") in info.players
    assert webhost.wakes == 1


async def test_fetch_room_parses_the_tracker_id(webhost):
    from multitracker.room import fetch_room
    info = await asyncio.to_thread(fetch_room, webhost.url, 5.0)
    assert info.tracker == "yQdtVUWGRFaaMCu14kdq8A"
    for bad in (None, 42, ""):  # not a usable id
        webhost.tracker_value = bad
        assert (await asyncio.to_thread(fetch_room, webhost.url, 5.0)).tracker is None
    webhost.send_tracker = False  # key missing
    assert (await asyncio.to_thread(fetch_room, webhost.url, 5.0)).tracker is None


async def test_follows_room_port_change(webhost, tmp_path):
    from multitracker.config import RoomConfig, SlotConfig
    from multitracker.service import Service
    from multitracker.store import Store
    zip_path = generated_seed("multi5")
    start_server(zip_path, PORT_A)
    cfg = RoomConfig(server="", password="test", room_url=webhost.url,
                     slots=[SlotConfig("Celeste"), SlotConfig("KH2")], path=tmp_path / "room.yaml")
    service = Service(cfg, Store(tmp_path / "db.sqlite3"), reconnect_delays=(0.3, 1.0))
    try:
        await service.start()
        await _eventually(lambda: all(t.state.status == "connected" for t in service.trackers.values()))
        assert service.current_server == f"127.0.0.1:{PORT_A}"
        # The room goes to sleep and wakes up on another port.
        stop_server(PORT_A)
        webhost.port_value = PORT_B
        start_server(zip_path, PORT_B)
        service._room_checked_at = 0  # do not wait for the 60 s rate limit in the test
        await _eventually(lambda: all(t.state.status == "connected" for t in service.trackers.values())
                          and service.current_server == f"127.0.0.1:{PORT_B}", timeout=30)
    finally:
        await service.stop()
        stop_server(PORT_A)
        stop_server(PORT_B)


async def test_config_api_discover_and_save(webhost, tmp_path, monkeypatch):
    import httpx
    from multitracker import config as config_mod
    from multitracker.api import create_app
    from multitracker.config import RoomConfig
    from multitracker.service import Service
    from multitracker.store import Store

    players_dir = tmp_path / "players"
    players_dir.mkdir()
    (players_dir / "kh2.yaml").write_text("name: KH2\ngame: Kingdom Hearts 2\n")
    monkeypatch.setattr(config_mod, "PLAYERS_DIR", players_dir)

    cfg = RoomConfig(server="127.0.0.1:1", password="secret", slots=[], path=tmp_path / "room.yaml")
    app = create_app(lambda: Service(cfg, Store(tmp_path / "db.sqlite3")), frontend_dist=None)
    async with app.router.lifespan_context(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://t") as client:
            found = (await client.post("/api/discover", json={"url": webhost.url})).json()
            assert found["server"] == f"127.0.0.1:{PORT_A}" and len(found["players"]) == 5
            assert (await client.post("/api/discover", json={"url": "https://x/nope"})).status_code == 400
            bad = await client.put("/api/config", json={"room_url": webhost.url, "slots": [
                {"name": "KH2", "yaml": "/etc/passwd"}]})
            assert bad.status_code == 400  # yamls must live in config/players/
            ok = await client.put("/api/config", json={"room_url": webhost.url, "slots": [
                {"name": "KH2", "game": "Kingdom Hearts 2", "yaml": str(players_dir / "kh2.yaml"), "owner": "Romain"}]})
            assert ok.status_code == 200, ok.text
            saved = config_mod.load(tmp_path / "room.yaml")
            assert saved.password == "secret"  # kept when not sent
            assert saved.room_url == webhost.url and saved.slots[0].owner == "Romain"
            assert [s["name"] for s in (await client.get("/api/slots")).json()["slots"]] == ["KH2"]
            conf = (await client.get("/api/config")).json()
            assert conf["has_password"] is True and "password" not in conf


async def _eventually(predicate, timeout: float = 15.0):
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout
    while loop.time() < deadline:
        if predicate():
            return
        await asyncio.sleep(0.1)
    raise AssertionError("timed out")


def test_room_targets_are_restricted(monkeypatch):
    from multitracker.room import RoomError, fetch_room
    monkeypatch.delenv("MT_ROOM_HOSTS", raising=False)
    for url in ("http://archipelago.gg/room/AbCdEfGhIjKl",        # not https
                "https://192.168.1.1/room/AbCdEfGhIjKl",          # not an allowed site
                "https://evil.example/room/AbCdEfGhIjKl"):
        with pytest.raises(RoomError):
            fetch_room(url, 2.0)


async def test_cross_site_writes_are_refused(tmp_path):
    import httpx
    from multitracker.api import create_app
    from multitracker.config import RoomConfig
    from multitracker.service import Service
    from multitracker.store import Store
    cfg = RoomConfig(server="127.0.0.1:1", slots=[], path=tmp_path / "room.yaml")
    app = create_app(lambda: Service(cfg, Store(tmp_path / "db.sqlite3")), frontend_dist=None)
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://pi:42753") as client:
            r = await client.put("/api/config", json={"server": "x:1", "slots": []},
                                 headers={"origin": "https://evil.example"})
            assert r.status_code == 403
            r = await client.put("/api/config", json={"server": "x:1", "slots": []},
                                 headers={"origin": "http://pi:42753"})
            assert r.status_code == 200
