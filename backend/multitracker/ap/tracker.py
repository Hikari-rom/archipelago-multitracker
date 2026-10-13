"""Read-only tracker connection for one Archipelago slot.

The connection uses the `Tracker` tag (the server then refuses location checks and goal
updates from it anyway) and an explicit allow-list of outgoing commands: it can only read
(GetDataPackage, Connect, Sync, Get, SetNotify, and LocationScouts on locations the slot has already checked,
without creating hints). It never sends LocationChecks, StatusUpdate, Say, hint requests or data storage writes.
"""
from __future__ import annotations

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable

from . import net

log = logging.getLogger(__name__)

# The only commands this client is allowed to send. Everything here is a read. LocationScouts is further
# restricted (see SlotTracker._send): already checked locations of the slot only, never as hints, so it tells
# nothing a spoiler would (what a done check held), and only when the "scout_checked" option is on.
ALLOWED_COMMANDS = frozenset({"GetDataPackage", "Connect", "Sync", "Get", "SetNotify", "LocationScouts"})
SCOUT_BATCH = 500  # locations per LocationScouts packet

CLIENT_GOAL = 30
ITEMS_HANDLING_ALL = 0b111  # receive items from other worlds, own world and starting inventory

# Errors that will not fix themselves by retrying quickly.
FATAL_REFUSALS = {"InvalidSlot", "InvalidPassword", "InvalidGame", "IncompatibleVersion"}


class ForbiddenCommand(RuntimeError):
    pass


@dataclass
class SlotState:
    """Everything the server told us about one slot. Ids only: names are resolved with the datapackage."""
    name: str
    game: str
    status: str = "idle"  # idle | connecting | connected | disconnected | error
    error: str | None = None
    url: str | None = None
    seed_name: str | None = None
    team: int | None = None
    slot: int | None = None
    players: dict[int, dict[str, Any]] = field(default_factory=dict)  # slot -> {name, alias, game}
    checked: set[int] = field(default_factory=set)
    missing: set[int] = field(default_factory=set)
    items: list[dict[str, Any]] = field(default_factory=list)  # NetworkItem dicts, in server order
    hints: list[dict[str, Any]] = field(default_factory=list)  # Hint dicts
    client_status: int = 0
    slot_data: dict[str, Any] = field(default_factory=dict)
    games: list[str] = field(default_factory=list)
    datapackage_checksums: dict[str, str] = field(default_factory=dict)
    connected_at: float | None = None
    synced: bool = False  # item list complete for this session
    contents: dict[int, tuple[int, int, int]] = field(default_factory=dict)  # checked location -> (item, receiver, flags)
    new_contents: list[tuple[int, int, int, int]] = field(default_factory=list)  # last LocationInfo batch
    new_checks: int = 0  # locations newly checked by the last RoomUpdate
    updated_at: float = field(default_factory=time.time)

    @property
    def goal_reached(self) -> bool:
        return self.client_status == CLIENT_GOAL


ChangeCallback = Callable[["SlotTracker", set[str]], None]


class SlotTracker:
    """Keeps one tracker connection alive (auto-reconnect) and mirrors the slot state."""

    def __init__(self, server: str | Callable[[], str], password: str, name: str, game: str,
                 datapackage: "DataPackageProvider", on_change: ChangeCallback | None = None,
                 min_delay: float = 2.0, max_delay: float = 60.0,
                 on_connect_error: Callable[["SlotTracker"], None] | None = None, scout_checked: bool = False) -> None:
        self.server = server  # address, or a callable returning the current address (room port changes)
        self.on_connect_error = on_connect_error
        self.password = password or None
        self.state = SlotState(name=name, game=game)
        self.scout_checked = scout_checked  # ask the server what the checked locations held (LocationScouts)
        self._scouting: set[int] = set()  # asked, answer pending
        self.datapackage = datapackage
        self.on_change = on_change
        self.min_delay, self.max_delay = min_delay, max_delay
        self._uuid = uuid.uuid4().hex
        self._sock = None
        self._task: asyncio.Task | None = None
        self._stopping = False
        self._had_session = False
        self._retry = asyncio.Event()

    # -- lifecycle -------------------------------------------------------------------------
    def start(self) -> None:
        if self._task is None or self._task.done():
            self._stopping = False
            self._task = asyncio.create_task(self._run(), name=f"tracker:{self.state.name}")

    async def stop(self) -> None:
        self._stopping = True
        if self._sock is not None:
            await self._sock.close()
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except (asyncio.CancelledError, Exception):
                pass

    def retry_now(self) -> None:
        """Skip the current reconnection delay (e.g. right after waking the room up)."""
        self._retry.set()

    async def _run(self) -> None:
        delay = self.min_delay
        while not self._stopping:
            try:
                self._retry.clear()  # a retry_now() during this attempt skips the next delay
                self._set_status("connecting")
                address = self.server() if callable(self.server) else self.server
                if not address:
                    if self.on_connect_error:
                        self.on_connect_error(self)  # ask for the room's current port again
                    raise ConnectionError("adresse du serveur inconnue (room endormie ?)")
                try:
                    self._sock, self.state.url = await net.open_socket(address)
                except ConnectionError:
                    if self.on_connect_error:
                        self.on_connect_error(self)
                    raise
                self._had_session = False
                try:
                    await self._session()
                finally:
                    if self._had_session:
                        delay = self.min_delay
                if self._stopping:
                    break
                self._set_status("disconnected", "connexion fermée par le serveur")
                delay = self.min_delay  # a session happened: retry quickly
            except _Refused as exc:
                fatal = bool(set(exc.errors) & FATAL_REFUSALS)
                self._reset_slot_data()
                self._set_status("error", "connexion refusée : " + ", ".join(exc.errors))
                delay = self.max_delay if fatal else delay
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # network errors, server restarts, malformed packets
                log.info("tracker %s: %s", self.state.name, exc)
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
            try:
                await asyncio.wait_for(self._retry.wait(), delay)
                delay = self.min_delay  # retry_now(): the room was just woken up
            except asyncio.TimeoutError:
                delay = min(delay * 2, self.max_delay)

    # -- protocol --------------------------------------------------------------------------
    async def _send(self, *msgs: dict[str, Any]) -> None:
        for msg in msgs:
            if msg.get("cmd") not in ALLOWED_COMMANDS:
                raise ForbiddenCommand(f"read-only tracker may not send {msg.get('cmd')!r}")
            if msg["cmd"] == "LocationScouts":
                locations = set(msg.get("locations") or ())
                if not self.scout_checked or msg.get("create_as_hint") != 0 or not locations <= self.state.checked:
                    raise ForbiddenCommand("LocationScouts only on checked locations, without hints, when enabled")
        await self._sock.send(net.encode(list(msgs)))

    async def _scout_checked(self) -> None:
        """Ask what the slot's checked locations held (not known yet): already found, so no spoiler."""
        st = self.state
        if not self.scout_checked or not st.synced:
            return
        wanted = sorted(st.checked - st.contents.keys() - self._scouting)
        for start in range(0, len(wanted), SCOUT_BATCH):
            batch = wanted[start:start + SCOUT_BATCH]
            self._scouting.update(batch)
            await self._send({"cmd": "LocationScouts", "locations": batch, "create_as_hint": 0})

    async def _session(self) -> None:
        async for data in self._sock:
            for msg in net.decode(data):
                await self._handle(msg)

    async def _handle(self, msg: dict[str, Any]) -> None:
        cmd = msg.get("cmd")
        st = self.state
        if cmd == "RoomInfo":
            if st.seed_name is not None and msg.get("seed_name") != st.seed_name:
                self._reset_slot_data()  # another seed is hosted at this address
            st.seed_name = msg.get("seed_name")
            st.games = list(msg.get("games", []))
            st.datapackage_checksums = dict(msg.get("datapackage_checksums", {}))
            wanted = self.datapackage.missing(st.datapackage_checksums)
            if wanted:
                await self._send({"cmd": "GetDataPackage", "games": wanted})
            await self._send({"cmd": "Connect", "password": self.password, "game": "", "name": st.name,
                              "uuid": self._uuid, "version": net.AP_VERSION,
                              "items_handling": ITEMS_HANDLING_ALL, "tags": ["Tracker", "NoText"],
                              "slot_data": True})
        elif cmd == "DataPackage":
            games = msg.get("data", {}).get("games", {})
            self.datapackage.add(games)
            self._changed({"datapackage"})
        elif cmd == "ConnectionRefused":
            raise _Refused(msg.get("errors") or ["unknown"])
        elif cmd == "Connected":
            st.team, st.slot = msg["team"], msg["slot"]
            st.checked = set(msg.get("checked_locations", []))
            st.missing = set(msg.get("missing_locations", []))
            st.slot_data = msg.get("slot_data") or {}
            st.players = {}
            slot_info = {int(k): v for k, v in (msg.get("slot_info") or {}).items()}
            for p in msg.get("players", []):
                info = slot_info.get(p["slot"], {})
                st.players[p["slot"]] = {"name": p.get("name"), "alias": p.get("alias"), "game": info.get("game"),
                                         "team": p.get("team")}
            for sid, info in slot_info.items():  # item link groups are not in `players`
                st.players.setdefault(sid, {"name": info.get("name"), "alias": info.get("name"),
                                            "game": info.get("game"), "team": st.team})
            real_game = slot_info.get(st.slot, {}).get("game")
            if real_game:
                st.game = real_game
            st.items = []
            st.hints = []
            st.synced = False
            self._scouting = set()
            st.connected_at = time.time()
            self._had_session = True
            st.status, st.error = "connected", None
            keys = [self.hints_key, self.status_key]
            await self._send({"cmd": "Get", "keys": keys}, {"cmd": "SetNotify", "keys": keys})
            self._changed({"connected", "status", "checks", "items", "hints", "goal"})
        elif cmd == "ReceivedItems":
            index = msg.get("index", 0)
            items = msg.get("items", [])
            if index == 0:
                st.items = list(items)
            elif index == len(st.items):
                st.items.extend(items)
            else:
                log.info("tracker %s: item index desync (%s != %s), resyncing", st.name, index, len(st.items))
                await self._send({"cmd": "Sync"})
                return
            self._changed({"items"})
        elif cmd == "RoomUpdate":
            kinds = set()
            if "checked_locations" in msg:
                new = set(msg["checked_locations"])
                if new - st.checked:
                    st.new_checks = len(new - st.checked)
                    st.checked |= new
                    st.missing -= new
                    kinds.add("checks")
            if "players" in msg:
                for p in msg["players"]:
                    st.players.setdefault(p["slot"], {}).update({"name": p.get("name"), "alias": p.get("alias")})
                kinds.add("players")
            if kinds:
                self._changed(kinds)
            if "checks" in kinds:
                await self._scout_checked()
        elif cmd in ("Retrieved", "SetReply"):
            values = msg.get("keys", {}) if cmd == "Retrieved" else {msg.get("key"): msg.get("value")}
            kinds = set()
            if self.hints_key in values:
                st.hints = list(values[self.hints_key] or [])
                kinds.add("hints")
            if self.status_key in values:
                st.client_status = int(values[self.status_key] or 0)
                kinds.add("goal")
            if cmd == "Retrieved" and not st.synced:
                # Answered after the ReceivedItems that followed Connected: the item list is now complete.
                st.synced = True
                kinds.add("synced")
            if kinds:
                self._changed(kinds)
            if "synced" in kinds:
                await self._scout_checked()
        elif cmd == "LocationInfo":
            batch = []
            for net_item in msg.get("locations") or []:
                loc = int(net_item.get("location", 0))
                if loc in st.checked:  # only answers to our scouts of checked locations are kept
                    content = (int(net_item.get("item", 0)), int(net_item.get("player", 0)),
                               int(net_item.get("flags", 0) or 0))
                    st.contents[loc] = content
                    batch.append((loc, *content))
                self._scouting.discard(loc)
            if batch:
                st.new_contents = batch
                self._changed({"contents"})
        elif cmd == "InvalidPacket":
            log.warning("tracker %s: server reported invalid packet: %s", st.name, msg)

    @property
    def hints_key(self) -> str:
        return f"_read_hints_{self.state.team}_{self.state.slot}"

    @property
    def status_key(self) -> str:
        return f"_read_client_status_{self.state.team}_{self.state.slot}"

    def _reset_slot_data(self) -> None:
        st = self.state
        st.items, st.hints, st.checked, st.missing = [], [], set(), set()
        st.players, st.client_status, st.slot_data, st.synced = {}, 0, {}, False
        st.contents, st.new_contents = {}, []
        st.team = st.slot = None
        self._changed({"connected", "items", "checks", "hints", "goal"})

    def _set_status(self, status: str, error: str | None = None) -> None:
        if (self.state.status, self.state.error) != (status, error):
            self.state.status, self.state.error = status, error
            self._changed({"status"})

    def _changed(self, kinds: set[str]) -> None:
        self.state.updated_at = time.time()
        if self.on_change:
            try:
                self.on_change(self, kinds)
            except Exception:
                log.exception("on_change callback failed")


class _Refused(Exception):
    def __init__(self, errors: list[str]) -> None:
        super().__init__(", ".join(errors))
        self.errors = errors


class DataPackageProvider:
    """Interface of the shared datapackage cache used by trackers."""

    def missing(self, checksums: dict[str, str]) -> list[str]:
        raise NotImplementedError

    def add(self, games: dict[str, dict[str, Any]]) -> None:
        raise NotImplementedError


__all__ = ["SlotTracker", "SlotState", "DataPackageProvider", "ALLOWED_COMMANDS", "ForbiddenCommand"]
_ = Awaitable  # typing re-export guard


async def probe(address: str, password: str | None, name: str, timeout: float = 20.0) -> dict[str, Any]:
    """One-shot connection test (room reachable, password and slot name accepted), then disconnect.
    Same read-only rules as SlotTracker: only allow-listed commands, `Tracker` tag."""
    async def send(sock, msg: dict[str, Any]) -> None:
        if msg.get("cmd") not in ALLOWED_COMMANDS or msg.get("cmd") == "LocationScouts":
            raise ForbiddenCommand(f"read-only tracker may not send {msg.get('cmd')!r}")
        await sock.send(net.encode([msg]))

    async def run() -> dict[str, Any]:
        sock, url = await net.open_socket(address)
        try:
            async for data in sock:
                for msg in net.decode(data):
                    cmd = msg.get("cmd")
                    if cmd == "RoomInfo":
                        await send(sock, {"cmd": "Connect", "password": password or None, "game": "", "name": name,
                                          "uuid": uuid.uuid4().hex, "version": net.AP_VERSION,
                                          "items_handling": 0, "tags": ["Tracker", "NoText"], "slot_data": False})
                    elif cmd == "ConnectionRefused":
                        return {"ok": False, "url": url, "errors": list(msg.get("errors") or ["unknown"])}
                    elif cmd == "Connected":
                        slot_info = {int(k): v for k, v in (msg.get("slot_info") or {}).items()}
                        game = slot_info.get(msg.get("slot"), {}).get("game")
                        return {"ok": True, "url": url, "errors": [], "game": game,
                                "players": len(msg.get("players") or [])}
            return {"ok": False, "url": url, "errors": ["connexion fermée par le serveur"]}
        finally:
            await sock.close()

    try:
        return await asyncio.wait_for(run(), timeout)
    except asyncio.TimeoutError:
        return {"ok": False, "url": None, "errors": ["pas de réponse du serveur"]}
    except ForbiddenCommand:
        raise
    except Exception as exc:  # unreachable server, closed socket, malformed packet
        return {"ok": False, "url": None, "errors": [f"{exc}"[:300] or type(exc).__name__]}
