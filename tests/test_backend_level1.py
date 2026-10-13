"""M3: level-1 tracking (generic, all games) against a local test server driven by the test bot."""
from __future__ import annotations

import asyncio
import json
import random
import socket
from pathlib import Path

import httpx
import pytest
import uvicorn

from testenv_helpers import FIXTURES, generated_seed, start_server, stop_server

PORT = 38288
SERVER = f"ws://127.0.0.1:{PORT}"
SLOTS = {"Celeste": "Celeste (Open World)", "KH2": "Kingdom Hearts 2",
         "Jak": "Jak and Daxter: The Precursor Legacy", "TWWHD": "The Wind Waker HD", "SM64": "Super Mario 64"}

pytestmark = pytest.mark.asyncio


@pytest.fixture(scope="module")
def seed_zip() -> Path:
    return generated_seed("multi5")


@pytest.fixture
def server(seed_zip):
    start_server(seed_zip, PORT)  # fresh state for every test (saves disabled)
    try:
        yield SERVER
    finally:
        stop_server(PORT)


def make_config(tmp_path: Path):
    from multitracker import config
    path = tmp_path / "room.yaml"
    path.write_text(json.dumps({"server": f"127.0.0.1:{PORT}", "password": "test",
                                "slots": [{"name": n, "game": g} for n, g in SLOTS.items()]}))
    return config.load(path)


def make_service(tmp_path: Path):
    from multitracker.service import Service
    from multitracker.store import Store
    return Service(make_config(tmp_path), Store(tmp_path / "db.sqlite3"), publish_debounce=0.05,
                   reconnect_delays=(0.3, 1.0))


async def eventually(predicate, timeout: float = 15.0, what: str = "condition"):
    deadline = asyncio.get_running_loop().time() + timeout
    while asyncio.get_running_loop().time() < deadline:
        if predicate():
            return
        await asyncio.sleep(0.1)
    raise AssertionError(f"timed out waiting for {what}")


async def connected_service(tmp_path):
    service = make_service(tmp_path)
    await service.start()
    await eventually(lambda: all(t.state.status == "connected" for t in service.trackers.values()),
                     what="all slots connected")
    return service


async def test_connects_all_slots_and_matches_server_view(server, tmp_path):
    from bot import GameBot
    service = await connected_service(tmp_path)
    try:
        for name, game in SLOTS.items():
            summary = service.summary(name)
            async with GameBot(server, name, game) as bot:
                assert summary["game"] == game
                assert summary["checks"]["total"] == len(bot.checked) + len(bot.missing)
                assert summary["checks"]["done"] == len(bot.checked)
                await eventually(lambda: service.summary(name)["items"]["received"] == len(bot.items),
                                 what=f"{name} items")
    finally:
        await service.stop()


async def test_checks_items_goal_and_seen(server, tmp_path):
    from bot import GameBot
    service = await connected_service(tmp_path)
    rng = random.Random(7)
    try:
        # Every slot checks some locations: items flow between worlds.
        for name, game in SLOTS.items():
            async with GameBot(server, name, game) as bot:
                await bot.check_random(25, rng)
        for name, game in SLOTS.items():
            async with GameBot(server, name, game) as bot:
                await eventually(lambda: service.summary(name)["checks"]["done"] == len(bot.checked),
                                 what=f"{name} checks")
                await eventually(lambda: service.summary(name)["items"]["received"] == len(bot.items),
                                 what=f"{name} items")
                detail = service.detail(name)
                received = [i["name"] for i in detail["items_list"]]
                assert not any(n.startswith("Item #") for n in received), "item names must come from the datapackage"
                assert len(received) == len(bot.items)

        # "New since last visit" + mark as seen
        name = max(SLOTS, key=lambda n: service.summary(n)["items"]["received"])
        assert service.summary(name)["items"]["new"] == service.summary(name)["items"]["received"] > 0
        service.mark_seen(name)
        assert service.summary(name)["items"]["new"] == 0
        assert service.seen_count(name) == service.summary(name)["items"]["received"]

        # Goal
        async with GameBot(server, "SM64", SLOTS["SM64"]) as bot:
            await bot.goal()
        await eventually(lambda: service.summary("SM64")["goal"], what="goal")
        assert not service.summary("Celeste")["goal"]
    finally:
        await service.stop()


async def test_hints_both_directions(server, tmp_path):
    from bot import GameBot
    service = await connected_service(tmp_path)
    try:
        # Celeste asks for a hint on one of its own progression items.
        names = service.datapackage.names(SLOTS["Celeste"])
        assert names is not None
        async with GameBot(server, "Celeste", SLOTS["Celeste"]) as bot:
            await bot.say("!hint Strawberry")
        await eventually(lambda: service.trackers["Celeste"].state.hints, what="Celeste hint")
        st = service.trackers["Celeste"].state
        hint = st.hints[0]
        assert hint["receiving_player"] == st.slot
        detail = service.detail("Celeste")
        views = detail["hints_mine_elsewhere"] + detail["hints_in_my_world"]
        assert any(h["item"] == "Strawberry" for h in views)
        # The finder's tracker sees the same hint, on the location side.
        finder = next(n for n, t in service.trackers.items() if t.state.slot == hint["finding_player"])
        await eventually(lambda: service.trackers[finder].state.hints, what="finder hint")
        assert any(h["item"] == "Strawberry" and h["receiver"] == "Celeste"
                   for h in service.detail(finder)["hints_in_my_world"])
    finally:
        await service.stop()


async def test_reconnects_after_server_restart(seed_zip, tmp_path):
    start_server(seed_zip, PORT)
    service = await connected_service(tmp_path)
    try:
        stop_server(PORT)
        await eventually(lambda: all(t.state.status != "connected" for t in service.trackers.values()),
                         what="disconnect detected")
        start_server(seed_zip, PORT)
        await eventually(lambda: all(t.state.status == "connected" for t in service.trackers.values()),
                         timeout=30, what="reconnection")
    finally:
        await service.stop()
        stop_server(PORT)


async def test_wrong_password_is_reported(server, tmp_path):
    from multitracker.service import Service
    from multitracker.store import Store
    cfg = make_config(tmp_path)
    cfg.password = "wrong"
    service = Service(cfg, Store(tmp_path / "db.sqlite3"), reconnect_delays=(0.3, 1.0))
    await service.start()
    try:
        await eventually(lambda: service.summary("Celeste")["status"] == "error", what="error status")
        assert "InvalidPassword" in service.summary("Celeste")["error"]
    finally:
        await service.stop()


async def test_tracker_never_sends_write_commands():
    from multitracker.ap.tracker import ALLOWED_COMMANDS, ForbiddenCommand, SlotTracker
    assert ALLOWED_COMMANDS == {"GetDataPackage", "Connect", "Sync", "Get", "SetNotify", "LocationScouts"}
    tracker = SlotTracker("127.0.0.1:1", "", "x", "y", datapackage=None)  # scout_checked off by default

    class FakeSock:
        sent = []

        async def send(self, data):
            self.sent.append(data)

    tracker._sock = FakeSock()
    for cmd in ("LocationChecks", "StatusUpdate", "Say", "Set", "LocationScouts", "CreateHints", "Bounce"):
        with pytest.raises(ForbiddenCommand):
            await tracker._send({"cmd": cmd})
    # LocationScouts: only when enabled, on checked locations, never as hints
    tracker.state.checked = {1, 2}
    with pytest.raises(ForbiddenCommand):
        await tracker._send({"cmd": "LocationScouts", "locations": [1], "create_as_hint": 0})
    tracker.scout_checked = True
    for bad in ({"locations": [1, 3], "create_as_hint": 0}, {"locations": [1], "create_as_hint": 2},
                {"locations": [1]}):
        with pytest.raises(ForbiddenCommand):
            await tracker._send({"cmd": "LocationScouts", **bad})
    assert FakeSock.sent == []
    await tracker._send({"cmd": "LocationScouts", "locations": [1, 2], "create_as_hint": 0})
    assert len(FakeSock.sent) == 1


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


async def test_http_api_and_sse(server, tmp_path):
    from bot import GameBot
    from multitracker.api import create_app
    app = create_app(lambda: make_service(tmp_path), frontend_dist=None)
    port = free_port()
    uv = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning"))
    task = asyncio.create_task(uv.serve())
    try:
        await eventually(lambda: uv.started, what="uvicorn started")
        async with httpx.AsyncClient(base_url=f"http://127.0.0.1:{port}", timeout=10) as client:
            async def all_connected():
                data = (await client.get("/api/slots")).json()
                return all(s["status"] == "connected" for s in data["slots"])
            for _ in range(100):
                if await all_connected():
                    break
                await asyncio.sleep(0.1)
            assert (await client.get("/api/health")).json()["connected"] == len(SLOTS)
            assert (await client.get("/api/slots/Nope")).status_code == 404
            detail = (await client.get("/api/slots/Celeste")).json()
            assert detail["name"] == "Celeste" and "items_list" in detail

            async with client.stream("GET", "/api/events") as resp:
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
                assert first["type"] == "snapshot" and len(first["data"]["slots"]) == len(SLOTS)
                async with GameBot(server, "Celeste", SLOTS["Celeste"]) as bot:
                    await bot.check_random(2, random.Random(3))
                while True:
                    event = await asyncio.wait_for(next_event(), 10)
                    if event["type"] == "slot" and event["data"]["slot"]["name"] == "Celeste" \
                            and event["data"]["slot"]["checks"]["done"] >= 2:
                        break

            seen = await client.post("/api/slots/Celeste/seen", json={})
            assert seen.status_code == 200
            assert (await client.get("/api/slots/Celeste")).json()["items"]["new"] == 0
    finally:
        uv.should_exit = True
        await asyncio.wait_for(task, 15)


_ = FIXTURES
