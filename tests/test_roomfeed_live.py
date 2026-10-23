"""Room feed against a local test server: live broadcasts are heard, nothing is replayed after a gap, and the catch-up fills it."""
from __future__ import annotations

import asyncio
import json
import random
import time
from pathlib import Path

import pytest

from test_backend_level1 import SLOTS, eventually
from testenv_helpers import generated_seed, start_server, stop_server

PORT = 38283
SERVER = f"ws://127.0.0.1:{PORT}"


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


def make_listener(tmp_path, checks, joins):
    from multitracker.datapackage import DataPackageCache
    from multitracker.roomfeed.listener import RoomListener
    from multitracker.store import Store
    return RoomListener(lambda: f"127.0.0.1:{PORT}", "test", "Celeste", DataPackageCache(Store(tmp_path / "db.sqlite3")),
                        on_check=lambda *a: checks.append(a), on_join=lambda slot, tags: joins.append((slot, tags)),
                        min_delay=0.3, max_delay=1.0)


async def test_hears_checks_and_joins_live(server, tmp_path):
    from bot import GameBot
    checks, joins = [], []
    listener = make_listener(tmp_path, checks, joins)
    listener.start()
    try:
        await eventually(lambda: listener.status == "listening", what="listening")
        assert listener.seed_name and {p["game"] for p in listener.players.values()} >= {"Kingdom Hearts 2"}
        before = time.time()
        async with GameBot(server, "KH2", "Kingdom Hearts 2") as bot:
            done = await bot.check_random(5, random.Random(3))
            await eventually(lambda: len(checks) >= 5, what="5 checks heard")
            after = time.time()
            assert len(done) == 5 and len(checks) == 5
            assert {c[3] for c in checks} == set(done)
            for sender, receiver, item, location, flags, at in checks:
                assert sender == bot.slot and receiver in listener.players
                assert isinstance(item, int) and isinstance(flags, int)
                assert before <= at <= after
            assert any(slot == bot.slot and "Tracker" not in tags for slot, tags in joins), joins
    finally:
        await listener.stop()
    assert listener.status in ("listening", "disconnected")


async def test_no_replay_after_a_gap(server, tmp_path):
    """The server does not replay broadcasts: checks made while nobody listened are never heard afterwards."""
    from bot import GameBot
    checks, joins = [], []
    first = make_listener(tmp_path, checks, joins)
    first.start()
    try:
        await eventually(lambda: first.status == "listening", what="listening")
        async with GameBot(server, "KH2", "Kingdom Hearts 2") as bot:
            await bot.check_random(2, random.Random(1))
            await eventually(lambda: len(checks) == 2, what="2 checks heard")
    finally:
        await first.stop()
    async with GameBot(server, "KH2", "Kingdom Hearts 2") as bot:
        missed = await bot.check_random(4, random.Random(2))
    assert len(missed) == 4
    heard_before = len(checks)
    second = make_listener(tmp_path, checks, joins)
    second.start()
    try:
        await eventually(lambda: second.status == "listening", what="listening again")
        await asyncio.sleep(3)
        assert second.status == "listening"
        assert len(checks) == heard_before
        assert not {c[3] for c in checks} & set(missed)
    finally:
        await second.stop()


ROOM_URL = "https://archipelago.gg/room/AAAAAAAAAAAA"


async def test_catchup_finds_the_checks_missed_while_the_feed_was_stopped(server, tmp_path):
    """Test C: 3 checks heard live, feed stopped, 4 more checks: the next feed's first poll finds exactly those 4."""
    from bot import GameBot
    from multitracker.ap.tracker import SlotTracker
    from multitracker.datapackage import DataPackageCache
    from multitracker.room import RoomInfo
    from multitracker.roomfeed.feed import RoomFeed
    from multitracker.roomfeed.log import RoomLog
    from multitracker.store import Store

    datapackage = DataPackageCache(Store(tmp_path / "db.sqlite3"))
    trackers = {name: SlotTracker(lambda: f"127.0.0.1:{PORT}", "test", name, game, datapackage, min_delay=0.3, max_delay=1.0)
                for name, game in SLOTS.items()}
    polls = {"tracker": 0}

    def fetch(url):  # the WebHost tracker API, built from what read-only trackers see on the local server
        if "static_tracker" in url:
            return {"player_locations_total": [], "player_game": []}
        polls["tracker"] += 1
        rows = [(t.state.slot, list(t.state.items), sorted(t.state.checked)) for t in trackers.values()]
        return {"player_items_received": [{"team": 0, "player": slot, "items": [
                    [i["item"], i["location"], i["player"], i.get("flags") or 0] for i in items]}
                    for slot, items, _checked in rows],
                "player_checks_done": [{"team": 0, "player": slot, "locations": checked} for slot, _i, checked in rows]}

    def fetch_room(url):
        return RoomInfo(url=url, host="archipelago.gg", port=None, players=[], tracker="BBBBBBBBBBBB")

    def make_feed():
        return RoomFeed(server=lambda: f"127.0.0.1:{PORT}", password="test", slot_name="Celeste", room_url=ROOM_URL,
                        tracked={"Celeste"}, datapackage=datapackage, publish=lambda event: None,
                        bk_of=lambda name: None, root=tmp_path / "room_feed", overrides_path=tmp_path / "players.yaml",
                        fetch=fetch, fetch_room=fetch_room, poll_interval=3600, static_interval=3600, heartbeat=0.2,
                        reconnect_delays=(0.3, 1.0))

    def heard_by_trackers(slot, locations):  # the checks of `slot` that some tracker has seen as a received item
        return {i["location"] for t in trackers.values() for i in t.state.items
                if i["player"] == slot and i["location"] in locations}

    for tracker in trackers.values():
        tracker.start()
    first = second = None
    try:
        await eventually(lambda: all(t.state.status == "connected" and t.state.synced for t in trackers.values()),
                         what="all slots tracked")
        first = make_feed()
        first.start()
        await eventually(lambda: first.status()["state"] == "listening" and polls["tracker"] >= 2,
                         what="feed listening, start and session polls done")
        async with GameBot(server, "KH2", "Kingdom Hearts 2") as bot:
            live = await bot.check_random(3, random.Random(1))
            await eventually(lambda: len(first.log.entries) == 3, what="3 live checks")
            await asyncio.sleep(0.5)  # a few heartbeats
            await first.stop()
            saved = RoomLog(tmp_path / "room_feed")
            saved.open_seed(first.log.seed)
            last_live = saved.load_state()["last_live_at"]
            assert last_live >= max(e.at for e in first.log.entries)
            missed = await bot.check_random(4, random.Random(2))
            assert len(live) == 3 and len(missed) == 4 and not set(live) & set(missed)
            await eventually(lambda: heard_by_trackers(bot.slot, set(live) | set(missed)) == set(live) | set(missed),
                             what="the trackers saw the 7 checks")
            polled = time.time()
            second = make_feed()
            second.start()
            await eventually(lambda: len(second.log.entries) == 7, what="catch-up of the missed checks")
            await asyncio.sleep(0.5)  # later polls and live hearing must not add or duplicate anything
            await second.poll_now()
            entries = second.log.entries
            assert len(entries) == 7 and {e.key for e in entries} == {(bot.slot, loc) for loc in [*live, *missed]}
            by_loc = {e.location: e for e in entries}
            assert all(by_loc[loc].src == "live" and by_loc[loc].after is None for loc in live)
            for loc in missed:
                entry = by_loc[loc]
                assert entry.src == "catchup" and entry.at is None
                assert entry.after == last_live and entry.before >= polled and entry.before > entry.after
            rows = [row for path in (tmp_path / "room_feed" / second.log.seed).glob("checks-*.jsonl")
                    for row in map(json.loads, path.read_text().splitlines())]
            assert len(rows) == 7 and len({(r["sender"], r["location"]) for r in rows}) == 7
    finally:
        for feed in (first, second):
            if feed is not None:
                await feed.stop()
        await asyncio.gather(*(t.stop() for t in trackers.values()), return_exceptions=True)
