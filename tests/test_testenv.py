"""M2: the test environment itself (generation, local server, bot)."""
import asyncio
import random

import pytest

from testenv_helpers import generated_seed, start_server, stop_server

PORT = 38289


@pytest.fixture(scope="module")
def server():
    zip_path = generated_seed("multi5")
    start_server(zip_path, PORT)
    try:
        yield f"ws://127.0.0.1:{PORT}"
    finally:
        stop_server(PORT)


def test_bot_checks_are_seen_by_a_second_client(server):
    from bot import GameBot

    async def scenario():
        async with GameBot(server, "Celeste", "Celeste (Open World)") as bot:
            before = len(bot.missing)
            done = await bot.check_random(3, random.Random(1))
            assert len(done) == 3
            assert len(bot.missing) == before - 3
        async with GameBot(server, "Celeste", "Celeste (Open World)") as again:
            assert set(done) <= again.checked

    asyncio.run(scenario())


def test_bot_refuses_remote_servers():
    from bot import GameBot
    with pytest.raises(ValueError):
        GameBot("wss://archipelago.gg:38281", "x", "y")
    with pytest.raises(ValueError):
        GameBot("ws://127.0.0.1:1@evil.example:38281", "x", "y")
    with pytest.raises(ValueError):
        GameBot("ws://127.0.0.1:8080", "x", "y")
