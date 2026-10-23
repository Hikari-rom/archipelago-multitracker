"""Read-only room listener: a Tracker-tagged connection that hears the room's ItemSend/Join/Part broadcasts.

It sends nothing but GetDataPackage, Connect, Get and SetNotify (enforced in `_send`). It never scouts, never reads
hints and never writes anything: the checks it reports are the ones the server already announced to everybody.
"""
from __future__ import annotations

import asyncio
import logging
import time
import uuid
from typing import Any, Callable

from ..ap import net
from ..ap.tracker import FATAL_REFUSALS, ForbiddenCommand

log = logging.getLogger(__name__)

LISTENER_COMMANDS = frozenset({"GetDataPackage", "Connect", "Get", "SetNotify"})
NO_ADDRESS = "adresse du serveur inconnue (room endormie ?)"
STATUS_KEY_PREFIX = "_read_client_status_"

class _Refused(Exception):
    def __init__(self, errors: list[str]) -> None:
        super().__init__(", ".join(errors))
        self.errors = errors

def _int(value: Any) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None

class RoomListener:
    """Keeps one listening connection alive (auto-reconnect) and reports what the room broadcasts."""

    def __init__(self, server: Callable[[], str], password: str, slot_name: str, datapackage,
                 on_session: Callable[["RoomListener"], None] | None = None,
                 on_check: Callable[[int, int, int, int, int, float], None] | None = None,  # sender, receiver, item, location, flags, at
                 on_join: Callable[[int, list[str]], None] | None = None,
                 on_part: Callable[[int], None] | None = None,
                 on_status: Callable[[int, int], None] | None = None,  # slot, client status
                 on_state: Callable[["RoomListener"], None] | None = None,
                 min_delay: float = 2.0, max_delay: float = 60.0) -> None:
        self.server = server
        self.password = password or None
        self.slot_name = slot_name
        self.datapackage = datapackage
        self.on_session, self.on_check, self.on_join = on_session, on_check, on_join
        self.on_part, self.on_status, self.on_state = on_part, on_status, on_state
        self.min_delay, self.max_delay = min_delay, max_delay
        self.status = "idle"  # idle | connecting | listening | disconnected | error
        self.error: str | None = None
        self.seed_name: str | None = None
        self.team: int | None = None
        self.slot: int | None = None
        self.players: dict[int, dict[str, Any]] = {}  # slot -> {"name", "game", "type"} (type 1 player, 2 item-link group)
        self.listening_since: float | None = None
        self.statuses: dict[int, int] = {}
        self._status_keys: dict[str, int] = {}  # data storage key -> slot
        self._uuid = uuid.uuid4().hex
        self._sock = None
        self._task: asyncio.Task | None = None
        self._stopping = False
        self._had_session = False  # a Connected was received on the current connection

    def start(self) -> None:
        if self._task is None or self._task.done():
            self._stopping = False
            self._task = asyncio.create_task(self._run(), name="roomfeed:listener")

    async def stop(self) -> None:
        self._stopping = True
        if self._sock is not None:
            try:
                await self._sock.close()
            except Exception:
                pass
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except (asyncio.CancelledError, Exception):
                pass

    async def _run(self) -> None:
        delay = self.min_delay
        while not self._stopping:
            try:
                self._set_status("connecting")
                address = self.server()
                if not address:  # the room sleeps: never wake it, look again later
                    self._set_status("disconnected", NO_ADDRESS)
                    await asyncio.sleep(self.max_delay)
                    continue
                self._sock, _ = await net.open_socket(address)
                self._had_session = False
                try:
                    await self._session()
                finally:
                    if self._had_session:  # also when the session ends by exception (abnormal close)
                        delay = self.min_delay
                if self._stopping:
                    break
                self._set_status("disconnected", "connexion fermée par le serveur")
                delay = self.min_delay  # a session happened: retry quickly
            except _Refused as exc:
                fatal = bool(set(exc.errors) & FATAL_REFUSALS)
                self._set_status("error", "connexion refusée : " + ", ".join(exc.errors))
                delay = self.max_delay if fatal else delay
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # network errors, server restarts, malformed packets
                log.info("roomfeed listener: %s", exc)
                self._set_status("disconnected", f"{type(exc).__name__}: {exc}"[:300])
            finally:
                if self._sock is not None:
                    try:
                        await self._sock.close()
                    except Exception:
                        pass
                    self._sock = None
            if self._stopping:
                break
            await asyncio.sleep(delay)
            delay = min(delay * 2, self.max_delay)

    # -- protocol --------------------------------------------------------------------------
    async def _send(self, *msgs: dict[str, Any]) -> None:
        for msg in msgs:
            if msg.get("cmd") not in LISTENER_COMMANDS:
                raise ForbiddenCommand(f"read-only room listener may not send {msg.get('cmd')!r}")
        await self._sock.send(net.encode(list(msgs)))

    async def _session(self) -> None:
        async for data in self._sock:
            for msg in net.decode(data):
                await self._handle(msg)

    async def _handle(self, msg: dict[str, Any]) -> None:
        cmd = msg.get("cmd")
        if cmd == "RoomInfo":
            self.seed_name = msg.get("seed_name")
            wanted = self.datapackage.missing(dict(msg.get("datapackage_checksums") or {}))
            if wanted:
                await self._send({"cmd": "GetDataPackage", "games": wanted})
            await self._send({"cmd": "Connect", "password": self.password, "game": "", "name": self.slot_name,
                              "uuid": self._uuid, "version": net.AP_VERSION, "items_handling": 0,
                              "tags": ["Tracker"], "slot_data": False})
        elif cmd == "DataPackage":
            self.datapackage.add(msg.get("data", {}).get("games", {}))
        elif cmd == "ConnectionRefused":
            raise _Refused(msg.get("errors") or ["unknown"])
        elif cmd == "Connected":
            await self._connected_packet(msg)
        elif cmd in ("Retrieved", "SetReply"):
            values = msg.get("keys", {}) if cmd == "Retrieved" else {msg.get("key"): msg.get("value")}
            for key, value in values.items():
                slot = self._status_keys.get(key) if isinstance(key, str) else None
                if slot is not None:
                    status = _int(value) or 0
                    self.statuses[slot] = status
                    self._call(self.on_status, slot, status)
        elif cmd == "PrintJSON":
            self._print_json(msg)

    async def _connected_packet(self, msg: dict[str, Any]) -> None:
        self.team, self.slot = msg["team"], msg["slot"]
        slot_info = {int(k): v for k, v in (msg.get("slot_info") or {}).items()}
        players: dict[int, dict[str, Any]] = {}
        for p in msg.get("players", []):
            info = slot_info.get(p["slot"], {})
            players[p["slot"]] = {"name": p.get("name"), "game": info.get("game"), "type": info.get("type", 1)}
        for sid, info in slot_info.items():  # item link groups are not in `players`
            players.setdefault(sid, {"name": info.get("name"), "game": info.get("game"), "type": info.get("type", 1)})
        self.players = players
        self.statuses = {}
        self._status_keys = {f"{STATUS_KEY_PREFIX}{self.team}_{sid}": sid for sid in players}
        self.listening_since = time.time()
        self._had_session = True
        self._set_status("listening", notify=False)  # on_state fires once, below
        keys = list(self._status_keys)
        await self._send({"cmd": "Get", "keys": keys})
        await self._send({"cmd": "SetNotify", "keys": keys})
        self._call(self.on_session, self)
        self._call(self.on_state, self)

    def _print_json(self, msg: dict[str, Any]) -> None:
        kind = msg.get("type")
        if kind == "ItemSend":
            parsed = self._parse_item_send(msg)
            if parsed is None:
                log.debug("roomfeed listener: malformed ItemSend ignored: %r", msg)
                return
            sender, receiver, item, location, flags = parsed
            self._call(self.on_check, sender, receiver, item, location, flags, time.time())
        elif kind in ("Join", "Part") and msg.get("team") == self.team:
            slot = _int(msg.get("slot"))
            if slot is None:
                return
            if kind == "Join":
                self._call(self.on_join, slot, list(msg.get("tags") or []))
            else:
                self._call(self.on_part, slot)

    @staticmethod
    def _parse_item_send(msg: dict[str, Any]) -> tuple[int, int, int, int, int] | None:
        raw = msg.get("item")
        if isinstance(raw, dict):
            fields = [raw.get("item"), raw.get("location"), raw.get("player"), raw.get("flags", 0)]
        elif isinstance(raw, list) and len(raw) >= 4:
            fields = raw[:4]
        else:
            return None
        item, location, sender, flags = (_int(v) for v in fields)  # NetworkItem order: item, location, player, flags
        receiver = _int(msg.get("receiving"))
        if None in (item, location, sender, flags, receiver):
            return None
        return sender, receiver, item, location, flags

    def _set_status(self, status: str, error: str | None = None, notify: bool = True) -> None:
        if (self.status, self.error) != (status, error):
            self.status, self.error = status, error
            if notify:
                self._call(self.on_state, self)

    def _call(self, callback: Callable | None, *args: Any) -> None:
        if callback is None:
            return
        try:
            callback(*args)
        except Exception:
            log.exception("roomfeed listener callback failed")

__all__ = ["RoomListener", "LISTENER_COMMANDS"]
