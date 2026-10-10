"""M9: Configuration page backend (yaml upload/listing, backup/restore, room wake-up option, connection test)."""
from __future__ import annotations

import asyncio
from pathlib import Path

import httpx
import pytest

from test_room_discovery import PORT_A, FakeWebHost, _eventually
from testenv_helpers import generated_seed, start_server, stop_server

PROBE_PORT = 38290
OLD = "Sat, 01 Jan 2000 00:00:00 GMT"


@pytest.fixture
def webhost(monkeypatch):
    monkeypatch.setenv("MT_ROOM_HOSTS", "127.0.0.1")
    fake = FakeWebHost()
    yield fake
    fake.close()


@pytest.fixture
def players_dir(tmp_path, monkeypatch):
    from multitracker import config as config_mod
    d = tmp_path / "players"
    d.mkdir()
    monkeypatch.setattr(config_mod, "PLAYERS_DIR", d)
    return d


def make_app(cfg, tmp_path):
    from multitracker.api import create_app
    from multitracker.service import Service
    from multitracker.store import Store
    box = {}

    def factory():
        box["s"] = Service(cfg, Store(tmp_path / "db.sqlite3"), reconnect_delays=(0.3, 1.0))
        return box["s"]
    return create_app(factory, frontend_dist=None), box


# -- player yamls ------------------------------------------------------------------------------------
def test_list_yamls_is_recursive_and_describes_players(players_dir):
    from multitracker.players import list_yamls
    (players_dir / "romain").mkdir()
    (players_dir / "romain" / "a.yaml").write_text("name: A\ngame: Celeste (Open World)\n")
    (players_dir / "multi.yml").write_text("name: B\ngame: Jak 3\n---\nname: C{number}\ngame: {Balatro: 1, Jak 3: 0}\n")
    (players_dir / "broken.yaml").write_text("name: [\n")
    (players_dir / "notes.txt").write_text("x")
    got = {y["path"].rsplit("players/", 1)[1]: y for y in list_yamls()}
    assert set(got) == {"romain/a.yaml", "multi.yml", "broken.yaml"}
    assert got["romain/a.yaml"]["players"] == [{"name": "A", "game": "Celeste (Open World)"}]
    assert got["multi.yml"]["players"] == [{"name": "B", "game": "Jak 3"}, {"name": "C{number}", "game": "Balatro"}]
    assert got["broken.yaml"]["error"]


def test_upload_rules(players_dir):
    from multitracker.config import ConfigError
    from multitracker.players import save_upload
    body = "name: Romain_KH2\ngame: Kingdom Hearts 2\n"
    r = save_upload("../../etc/romain kh2&co.YAML", body)
    assert r["status"] == "created" and r["path"].endswith("players/romain_kh2andco.yaml")
    assert (players_dir / "romain_kh2andco.yaml").read_text() == body
    assert save_upload("romain_kh2andco.yaml", body)["status"] == "unchanged"
    with pytest.raises(FileExistsError):
        save_upload("romain_kh2andco.yaml", body + "# changed\n")
    assert save_upload("romain_kh2andco.yaml", body + "# changed\n", overwrite=True)["status"] == "replaced"
    for name, content in (("x.txt", body), ("x.yaml", "just: options\n"), ("x.yaml", "a: [\n"),
                          ("x.yaml", body + "#" * 600_000), (".yaml", body)):
        with pytest.raises(ConfigError):
            save_upload(name, content)
    assert sorted(p.name for p in players_dir.iterdir()) == ["romain_kh2andco.yaml"]


async def test_upload_api(players_dir, tmp_path):
    from multitracker.config import RoomConfig
    app, _ = make_app(RoomConfig(server="127.0.0.1:1", path=tmp_path / "room.yaml"), tmp_path)
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as client:
            body = {"filename": "kh2.yaml", "content": "name: K\ngame: Kingdom Hearts 2\n"}
            assert (await client.post("/api/yamls", json=body)).status_code == 200
            assert (await client.post("/api/yamls", json={**body, "content": body["content"] + "#\n"})).status_code == 409
            assert (await client.post("/api/yamls", json={**body, "filename": "a.exe"})).status_code == 400
            r = await client.post("/api/yamls", json=body, headers={"origin": "https://evil.example"})
            assert r.status_code == 403
            conf = (await client.get("/api/config")).json()
            assert [y["players"] for y in conf["yamls"]] == [[{"name": "K", "game": "Kingdom Hearts 2"}]]
            assert conf["games"]["Celeste (Open World)"] == {"logic": True, "needs_yaml": True}
            assert conf["wake_room"] is False and conf["has_backup"] is False


# -- backup / restore ------------------------------------------------------------------------------
async def test_save_keeps_a_backup_and_restore_swaps(players_dir, tmp_path):
    from multitracker import config as config_mod
    from multitracker.config import RoomConfig, SlotConfig
    path = tmp_path / "room.yaml"
    first = RoomConfig(server="127.0.0.1:1", password="pw1", slots=[SlotConfig("Test")], path=path)
    config_mod.save(first)
    assert not config_mod.backup_path(path).exists()
    app, box = make_app(first, tmp_path)
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as client:
            r = await client.put("/api/config", json={"server": "127.0.0.1:2", "wake_room": True,
                                                      "slots": [{"name": "Real"}]})
            assert r.status_code == 200
            assert (await client.get("/api/config")).json()["has_backup"] is True
            assert config_mod.load(path).wake_room is True
            assert [s.name for s in config_mod.load(config_mod.backup_path(path)).slots] == ["Test"]
            r = await client.post("/api/config/restore")
            assert r.status_code == 200, r.text
            assert [s.name for s in config_mod.load(path).slots] == ["Test"]
            assert list(box["s"].trackers) == ["Test"] and box["s"].config.password == "pw1"
            # a restore can itself be undone
            assert [s.name for s in config_mod.load(config_mod.backup_path(path)).slots] == ["Real"]
    assert oct(path.stat().st_mode & 0o777) == "0o600"
    assert oct(config_mod.backup_path(path).stat().st_mode & 0o777) == "0o600"


async def test_restore_refuses_yaml_outside_players(players_dir, tmp_path):
    from multitracker import config as config_mod
    from multitracker.config import RoomConfig, SlotConfig
    path = tmp_path / "room.yaml"
    config_mod.save(RoomConfig(server="127.0.0.1:1", slots=[SlotConfig("A", yaml=Path("/etc/passwd.yaml"))], path=path))
    config_mod.save(RoomConfig(server="127.0.0.1:1", slots=[SlotConfig("B")], path=path))
    app, box = make_app(config_mod.load(path), tmp_path)
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as client:
            assert (await client.post("/api/config/restore")).status_code == 400
            assert [s.name for s in config_mod.load(path).slots] == ["B"]  # nothing swapped


async def test_retry_now_during_an_attempt_skips_the_next_delay(tmp_path):
    from multitracker.ap.tracker import SlotTracker
    from multitracker.datapackage import DataPackageCache
    from multitracker.store import Store
    attempts = []

    def server():
        attempts.append(1)
        tracker.retry_now()  # e.g. the room was woken up while this attempt runs
        return "127.0.0.1:1"
    tracker = SlotTracker(server, "", "X", "", DataPackageCache(Store(tmp_path / "db.sqlite3")),
                          min_delay=30, max_delay=60)
    tracker.start()
    try:
        await _eventually(lambda: len(attempts) >= 3, timeout=10)
    finally:
        await tracker.stop()


def test_sleeping_has_a_clock_margin():
    import time
    from multitracker.room import SLEEP_MARGIN, RoomInfo
    info = RoomInfo(url="u", host="h", port=1, players=[], last_activity=time.time() - 7200 - 60, timeout=7200)
    assert info.sleeping is False
    info.last_activity -= SLEEP_MARGIN
    assert info.sleeping is True


# -- room wake-up option ---------------------------------------------------------------------------
async def test_sleeping_room_is_not_woken_by_default(webhost, tmp_path):
    from multitracker.config import RoomConfig, SlotConfig
    webhost.last_activity, webhost.port_value = OLD, 1  # asleep, stale port
    cfg = RoomConfig(server="", password="test", room_url=webhost.url, slots=[SlotConfig("Celeste")],
                     path=tmp_path / "room.yaml")
    app, box = make_app(cfg, tmp_path)
    async with app.router.lifespan_context(app):
        service = box["s"]
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as client:
            await _eventually(lambda: service.room_sleeping)
            assert service._last_room_event["room_sleeping"] is True  # pushed to the dashboards (SSE "room")
            for _ in range(3):  # connection failures re-read the room status, never the room page
                service._room_checked_at = 0
                service.refresh_room()
                await asyncio.sleep(0.3)
            assert webhost.wakes == 0
            slots = (await client.get("/api/slots")).json()
            assert slots["room_sleeping"] is True and "endormie" in slots["room_error"]
            found = (await client.post("/api/discover", json={"url": webhost.url})).json()
            assert found["sleeping"] is True and webhost.wakes == 0
            # explicit wake-up
            r = await client.post("/api/room/wake")
            assert r.status_code == 200 and webhost.wakes == 1
            assert service.room_sleeping is False


async def test_wake_room_option_wakes_the_room(webhost, tmp_path):
    from multitracker.config import RoomConfig, SlotConfig
    from multitracker.service import Service
    from multitracker.store import Store
    webhost.last_activity, webhost.port_value = OLD, 1
    cfg = RoomConfig(server="", password="test", room_url=webhost.url, slots=[SlotConfig("Celeste")],
                     path=tmp_path / "room.yaml", wake_room=True)
    service = Service(cfg, Store(tmp_path / "db.sqlite3"), reconnect_delays=(0.3, 1.0))
    try:
        await service.start()
        await _eventually(lambda: webhost.wakes >= 1)
    finally:
        await service.stop()


async def test_sleeping_state_clears_when_someone_wakes_the_room(webhost, tmp_path):
    from multitracker.config import RoomConfig, SlotConfig
    from multitracker.service import Service
    from multitracker.store import Store
    zip_path = generated_seed("multi5")
    webhost.last_activity = OLD
    cfg = RoomConfig(server="", password="test", room_url=webhost.url, slots=[SlotConfig("Celeste")],
                     path=tmp_path / "room.yaml")
    service = Service(cfg, Store(tmp_path / "db.sqlite3"), reconnect_delays=(0.3, 1.0))
    try:
        await service.start()
        await _eventually(lambda: service.room_sleeping)
        start_server(zip_path, PORT_A)  # someone opened the room link
        webhost.last_activity = None
        await _eventually(lambda: service.trackers["Celeste"].state.status == "connected", timeout=30)
        assert service.room_sleeping is False and service.room_error is None and webhost.wakes == 0
    finally:
        await service.stop()
        stop_server(PORT_A)


# -- connection test -------------------------------------------------------------------------------
async def test_probe_password_and_slot():
    from multitracker.ap.tracker import probe
    start_server(generated_seed("multi5"), PROBE_PORT)
    try:
        address = f"127.0.0.1:{PROBE_PORT}"
        ok = await probe(address, "test", "KH2")
        assert ok["ok"] is True and ok["game"] == "Kingdom Hearts 2"
        assert (await probe(address, "nope", "KH2"))["errors"] == ["InvalidPassword"]
        assert "InvalidSlot" in (await probe(address, "test", "Nobody"))["errors"]
        down = await probe("127.0.0.1:1", "test", "KH2", timeout=10)
        assert down["ok"] is False and down["errors"]
    finally:
        stop_server(PROBE_PORT)


async def test_connection_test_api(webhost, tmp_path):
    from multitracker.config import RoomConfig
    start_server(generated_seed("multi5"), PORT_A)
    try:
        cfg = RoomConfig(server="", room_url=webhost.url, password="test", path=tmp_path / "room.yaml")
        app, _ = make_app(cfg, tmp_path)
        async with app.router.lifespan_context(app):
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t",
                                         timeout=60) as client:
                r = (await client.post("/api/config/test", json={"room_url": webhost.url, "slot": "Jak"})).json()
                assert r["ok"] is True, r  # saved password used when none is sent
                r = (await client.post("/api/config/test", json={"room_url": webhost.url, "slot": "Jak",
                                                                 "password": "bad"})).json()
                assert r["errors"] == ["InvalidPassword"]
                # the saved password is never sent to another server
                r = (await client.post("/api/config/test", json={"server": f"localhost:{PORT_A}", "slot": "Jak"})).json()
                assert r["ok"] is False and "mot de passe" in r["errors"][0]
                r = (await client.post("/api/config/test", json={"server": f"localhost:{PORT_A}", "slot": "Jak",
                                                                 "password": "test"})).json()
                assert r["ok"] is True, r
                webhost.last_activity = OLD
                r = (await client.post("/api/config/test", json={"room_url": webhost.url, "slot": "Jak"})).json()
                assert r["ok"] is False and r["sleeping"] is True and webhost.wakes == 0
    finally:
        stop_server(PORT_A)
