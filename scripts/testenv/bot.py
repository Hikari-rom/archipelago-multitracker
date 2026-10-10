#!/usr/bin/env python3
"""TEST bot: connects to a LOCAL test server as a real game client and sends checks.

This is the only code allowed to send LocationChecks / StatusUpdate / Say, and only to the
local test server (127.0.0.1). Library use (tests) or CLI:

  bot.py --slot Celeste --game "Celeste (Open World)" --check 5        # 5 random missing locations
  bot.py --slot Celeste --game "Celeste (Open World)" --check-all
  bot.py --slot Celeste --game "Celeste (Open World)" --goal
  bot.py --slot Celeste --game "Celeste (Open World)" --say "!hint Strawberry"
"""
from __future__ import annotations

import argparse
import asyncio
import random
import sys
import uuid
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from multitracker.ap import net  # noqa: E402

CLIENT_GOAL = 30
LOCAL_HOSTS = ("ws://127.0.0.1:", "ws://localhost:")


class GameBot:
    """Minimal game client. Keeps the slot's checked/missing locations and received items up to date."""

    def __init__(self, server: str, slot: str, game: str, password: str = "test") -> None:
        if not server.startswith(LOCAL_HOSTS):
            raise ValueError("the test bot only talks to a local test server (ws://127.0.0.1:PORT)")
        self.server, self.slot_name, self.game, self.password = server, slot, game, password
        self.sock = None
        self.reader: asyncio.Task | None = None
        self.team = self.slot = None
        self.checked: set[int] = set()
        self.missing: set[int] = set()
        self.items: list[dict[str, Any]] = []
        self.slot_data: dict[str, Any] = {}
        self._connected = asyncio.Event()
        self._refused: list[str] | None = None
        self._update = asyncio.Event()

    async def connect(self, timeout: float = 30) -> "GameBot":
        self.sock, _ = await net.open_socket(self.server)
        self.reader = asyncio.create_task(self._read())
        await self._send({"cmd": "Connect", "password": self.password, "game": self.game, "name": self.slot_name,
                          "uuid": uuid.uuid4().hex, "version": net.AP_VERSION, "items_handling": 0b111,
                          "tags": ["AP", "TestBot"], "slot_data": True})
        await asyncio.wait_for(self._connected.wait(), timeout)
        if self._refused is not None:
            raise ConnectionError(f"connection refused: {self._refused}")
        return self

    async def close(self) -> None:
        if self.sock is not None:
            await self.sock.close()
        if self.reader is not None:
            self.reader.cancel()

    async def __aenter__(self) -> "GameBot":
        return await self.connect()

    async def __aexit__(self, *exc) -> None:
        await self.close()

    async def _send(self, *msgs: dict[str, Any]) -> None:
        await self.sock.send(net.encode(list(msgs)))

    async def _read(self) -> None:
        async for data in self.sock:
            for msg in net.decode(data):
                cmd = msg.get("cmd")
                if cmd == "Connected":
                    self.team, self.slot = msg["team"], msg["slot"]
                    self.checked = set(msg["checked_locations"])
                    self.missing = set(msg["missing_locations"])
                    self.slot_data = msg.get("slot_data") or {}
                    self._connected.set()
                elif cmd == "ConnectionRefused":
                    self._refused = msg.get("errors", [])
                    self._connected.set()
                elif cmd == "ReceivedItems":
                    if msg["index"] == 0:
                        self.items = list(msg["items"])
                    elif msg["index"] == len(self.items):
                        self.items.extend(msg["items"])
                    else:
                        await self._send({"cmd": "Sync"})
                elif cmd == "RoomUpdate" and "checked_locations" in msg:
                    new = set(msg["checked_locations"])
                    self.checked |= new
                    self.missing -= new
                self._update.set()

    async def check(self, locations: Iterable[int]) -> list[int]:
        locs = sorted(set(locations) & self.missing)
        if locs:
            await self._send({"cmd": "LocationChecks", "locations": locs})
            await self.wait_for(lambda: not (set(locs) & self.missing))
        return locs

    async def check_random(self, count: int, rng: random.Random | None = None) -> list[int]:
        rng = rng or random.Random()
        return await self.check(rng.sample(sorted(self.missing), min(count, len(self.missing))))

    async def goal(self) -> None:
        await self._send({"cmd": "StatusUpdate", "status": CLIENT_GOAL})

    async def say(self, text: str) -> None:
        await self._send({"cmd": "Say", "text": text})

    async def wait_for(self, predicate, timeout: float = 30) -> None:
        async def _loop():
            while not predicate():
                self._update.clear()
                await self._update.wait()
        await asyncio.wait_for(_loop(), timeout)


async def _main(args: argparse.Namespace) -> int:
    async with GameBot(args.server, args.slot, args.game, args.password) as bot:
        print(f"connected as {bot.slot_name} (slot {bot.slot}): {len(bot.checked)} checked, "
              f"{len(bot.missing)} missing, {len(bot.items)} items")
        if args.say:
            await bot.say(args.say)
        if args.check_all:
            done = await bot.check(bot.missing)
            print(f"checked {len(done)} locations")
        elif args.check:
            done = await bot.check_random(args.check, random.Random(args.seed))
            print(f"checked {len(done)} locations: {done}")
        if args.goal:
            await bot.goal()
            print("goal sent")
        await asyncio.sleep(0.5)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--server", default="ws://127.0.0.1:38281")
    parser.add_argument("--password", default="test")
    parser.add_argument("--slot", required=True)
    parser.add_argument("--game", required=True)
    parser.add_argument("--check", type=int, default=0, help="check N random missing locations")
    parser.add_argument("--check-all", action="store_true")
    parser.add_argument("--goal", action="store_true")
    parser.add_argument("--say")
    parser.add_argument("--seed", type=int)
    return asyncio.run(_main(parser.parse_args()))


if __name__ == "__main__":
    sys.exit(main())
