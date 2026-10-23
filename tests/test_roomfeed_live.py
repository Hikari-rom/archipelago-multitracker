"""Room listener against a local test server: live broadcasts are heard, and nothing is replayed after a gap."""
from __future__ import annotations

import asyncio
import random
import time
from pathlib import Path

import pytest

from test_backend_level1 import eventually
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
