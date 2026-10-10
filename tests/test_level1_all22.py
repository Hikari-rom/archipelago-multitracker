"""Level 1 for every game of the room: one 22-slot seed (default options), names resolved from the
datapackage, counters equal to what a real game client sees."""
from __future__ import annotations

import asyncio
import json
import random

import pytest
import yaml

from testenv_helpers import FIXTURES, generated_seed, start_server, stop_server

PORT = 38284


@pytest.fixture(scope="module")
def all22():
    zip_path = generated_seed("all22", 7, spoiler=1)
    start_server(zip_path, PORT)
    try:
        yield {d["name"]: d["game"] for d in (yaml.safe_load(p.read_text()) for p in (FIXTURES / "all22").glob("*.yaml"))}
    finally:
        stop_server(PORT)


async def test_level1_for_all_22_games(all22, tmp_path):
    from bot import GameBot
    from multitracker import config
    from multitracker.service import Service
    from multitracker.store import Store
    room = tmp_path / "room.yaml"
    room.write_text(json.dumps({"server": f"ws://127.0.0.1:{PORT}", "password": "test",
                                "slots": [{"name": n} for n in all22]}))
    service = Service(config.load(room), Store(tmp_path / "db.sqlite3"), publish_debounce=0.05)
    await service.start()
    try:
        loop = asyncio.get_running_loop()
        deadline = loop.time() + 60
        while not all(t.state.status == "connected" and t.state.synced for t in service.trackers.values()):
            assert loop.time() < deadline, {n: t.state.status for n, t in service.trackers.items()}
            await asyncio.sleep(0.2)
        rng = random.Random(5)
        for name, game in all22.items():
            async with GameBot(f"ws://127.0.0.1:{PORT}", name, game) as bot:
                await bot.check_random(10, rng)
        for name, game in all22.items():
            async with GameBot(f"ws://127.0.0.1:{PORT}", name, game) as bot:
                deadline = loop.time() + 20
                while not (service.summary(name)["checks"]["done"] == len(bot.checked)
                           and service.summary(name)["items"]["received"] == len(bot.items)):
                    assert loop.time() < deadline, (name, service.summary(name), len(bot.checked), len(bot.items))
                    await asyncio.sleep(0.1)
            detail = service.detail(name)
            assert detail["game"] == game
            assert detail["checks"]["total"] > 0
            unresolved = [i["name"] for i in detail["items_list"] if i["name"].startswith("Item #")]
            unresolved += [i["location"] for i in detail["items_list"] if (i["location"] or "").startswith("Location #")]
            assert not unresolved, (name, unresolved[:5])
    finally:
        await service.stop()
