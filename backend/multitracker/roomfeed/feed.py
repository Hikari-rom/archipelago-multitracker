"""RoomFeed: wires the listener, the check log, the HTTP catch-up, presence and player grouping together.

It is driven by `Service` but isolated: every task body catches its errors, nothing here touches the trackers' state,
and it only reads what the room already announced (checks done, items received).
"""
from __future__ import annotations

import asyncio
import logging
import time
from bisect import bisect_right
from pathlib import Path
from typing import Callable

from .. import room
from ..apenv import ROOT
from ..room import RoomError, RoomInfo, parse_room_url
from . import catchup
from .catchup import StaticInfo, TrackerSnapshot
from .listener import RoomListener
from .log import ROOT_DIR, CheckEntry, RoomLog
from .players import OVERRIDES_PATH, group_players, load_overrides
from .presence import Presence

log = logging.getLogger(__name__)

NO_SLOT = "aucun slot configuré pour écouter"
WAITING_SEED = "en attente du seed"
NO_TRACKER = "la room ne publie pas d'identifiant de tracker"
GOAL_STATUS = 30
WINDOW_MAX = 7200  # a catch-up window up to this wide is dated by its midpoint (activity)
HOURS, DAYS = 48, 30
SSE_BATCH_MAX = 200
FLAG_PROGRESSION, FLAG_USEFUL, FLAG_TRAP = 1, 2, 4


def _describe(exc: BaseException) -> str:
    return str(exc) if isinstance(exc, RoomError) else f"{type(exc).__name__}: {exc}"[:300]


def _category(flags: int) -> str | None:
    if flags & FLAG_PROGRESSION:
        return "PROG"
    if flags & FLAG_USEFUL:
        return "UTILE"
    if flags & FLAG_TRAP:
        return "PIÈGE"
    return None


def _bucket_starts(bucket: str, now: float) -> tuple[list[float], float]:
    """Start of every bucket (oldest first) and the end of the last one, on local-time boundaries."""
    lt = time.localtime(now)
    if bucket == "hour":
        def at(k: int) -> float:
            return time.mktime((lt.tm_year, lt.tm_mon, lt.tm_mday, lt.tm_hour + k, 0, 0, 0, 0, -1))
        count = HOURS
    else:
        def at(k: int) -> float:
            return time.mktime((lt.tm_year, lt.tm_mon, lt.tm_mday + k, 0, 0, 0, 0, 0, -1))
        count = DAYS
    return [at(k) for k in range(1 - count, 1)], at(1)


def _entry_time(entry: CheckEntry) -> float | None:
    if entry.at is not None:
        return entry.at
    if entry.after is not None and entry.before is not None and entry.before - entry.after <= WINDOW_MAX:
        return (entry.after + entry.before) / 2
    return None


class RoomFeed:
    def __init__(self, *, server: Callable[[], str], password: str, slot_name: str | None, room_url: str | None,
                 tracked: set[str], datapackage, publish: Callable[[dict], None],
                 bk_of: Callable[[str], bool | None], room_sleeping: Callable[[], bool] = lambda: False,
                 root: Path = ROOT_DIR, overrides_path: Path = OVERRIDES_PATH,
                 fetch: Callable[[str], dict] = catchup.fetch_json,
                 fetch_room: Callable[[str], RoomInfo] = lambda url: room.fetch_room(url, 15.0, False),
                 listener_factory: Callable[..., RoomListener] = RoomListener,
                 poll_interval: float = 300.0, sleeping_interval: float = 600.0, static_interval: float = 1800.0,
                 heartbeat: float = 60.0, flush_delay: float = 0.5, state_throttle: float = 2.0,
                 reconnect_delays: tuple[float, float] = (2.0, 60.0)) -> None:
        self.server, self.password, self.slot_name = server, password, slot_name
        self.room_url = room_url
        self.tracked = set(tracked)
        self.datapackage = datapackage
        self._publish = publish
        self._bk_of = bk_of
        self._room_sleeping = room_sleeping
        self._overrides_path = overrides_path
        self._fetch = fetch
        self._fetch_room = fetch_room
        self._listener_factory = listener_factory
        self.poll_interval, self.sleeping_interval, self.static_interval = poll_interval, sleeping_interval, static_interval
        self.heartbeat, self.flush_delay, self.state_throttle = heartbeat, flush_delay, state_throttle
        self.reconnect_delays = reconnect_delays
        self.log = RoomLog(root)
        self._room_id: str | None = None
        self._room_error: str | None = None
        if room_url:
            try:
                self._room_id = parse_room_url(room_url)[2]
            except RoomError as exc:
                self._room_error = str(exc)
        self._listener: RoomListener | None = None
        self._tasks: list[asyncio.Task] = []
        self._stopped = False
        # slots
        self._slots: dict[int, dict[str, str | None]] = {}  # slot id -> {"name", "game"}
        self._player_of: dict[int, str] = {}
        self._me: set[str] = set()
        self._room_players: list[tuple[str, str]] = []
        self._tracked_ids: set[int] = set()
        self.presence = Presence(set())
        self._live_check_at: dict[int, float] = {}
        self._awaiting_statuses = False
        # log indexes (sender slot -> count / latest time)
        self._counts: dict[int, int] = {}
        self._last_when: dict[int, float] = {}
        # listening gaps
        self._ever_listened = False
        self._was_listening = False
        self._gap_start: float | None = None  # start of the current gap in this run, if the listener dropped
        self._prior_live: float | None = None  # last_live_at saved by a previous run (before this app start)
        self._reconnected_at: float | None = None
        self._polls_since_reconnect = 0
        # polls
        self._poll_lock = asyncio.Lock()
        self._poll_wakeup = asyncio.Event()
        self._tracker_id: str | None = None
        self._snapshot: TrackerSnapshot | None = None
        self._static: StaticInfo | None = None
        self._static_at: float | None = None  # monotonic
        self._last_poll_at: float | None = None
        self._poll_error: str | None = self._room_error
        # events
        self._pending: list[CheckEntry] = []
        self._flush_task: asyncio.Task | None = None
        self._notify_task: asyncio.Task | None = None
        self._last_emit = float("-inf")

    # -- lifecycle ---------------------------------------------------------------------------
    def start(self) -> None:
        if self._tasks or self._stopped:
            return
        if self._room_id:
            seed = self.log.seed_for_room(self._room_id)
            if seed:
                self._open_seed(seed)
        self._tasks = [asyncio.create_task(self._poll_loop(), name="roomfeed:poll"),
                       asyncio.create_task(self._heartbeat_loop(), name="roomfeed:heartbeat")]
        if self.slot_name:
            self._listener = self._listener_factory(
                server=self.server, password=self.password, slot_name=self.slot_name, datapackage=self.datapackage,
                on_session=self._on_session, on_check=self._on_check, on_join=self._on_join, on_part=self._on_part,
                on_status=self._on_status, on_state=self._on_state,
                min_delay=self.reconnect_delays[0], max_delay=self.reconnect_delays[1])
            self._listener.start()

    async def stop(self) -> None:
        self._stopped = True  # callbacks fired while stopping are ignored
        if self._was_listening:  # a clean stop starts the gap now
            self.log.save_state(last_live_at=time.time())
        tasks = [t for t in [*self._tasks, self._flush_task, self._notify_task] if t is not None]
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        self._tasks, self._flush_task, self._notify_task = [], None, None
        if self._listener is not None:
            await self._listener.stop()
        self._pending = []

    # -- seed and slot table -------------------------------------------------------------------
    def _open_seed(self, seed: str) -> None:
        if seed == self.log.seed:
            return
        self.log.open_seed(seed)
        saved = self.log.load_state().get("last_live_at")
        self._prior_live = float(saved) if isinstance(saved, (int, float)) and not isinstance(saved, bool) else None
        self._gap_start = None
        self._counts, self._last_when = {}, {}
        for entry in self.log.entries:
            self._index(entry)

    def _index(self, entry: CheckEntry) -> None:
        self._counts[entry.sender] = self._counts.get(entry.sender, 0) + 1
        prev = self._last_when.get(entry.sender)
        self._last_when[entry.sender] = entry.when if prev is None else max(prev, entry.when)

    def _refresh_slots(self) -> None:
        lst = self._listener
        if lst is not None and lst.players:
            table = {sid: {"name": p.get("name"), "game": p.get("game")} for sid, p in lst.players.items()}
        else:
            table = {i + 1: {"name": n, "game": g} for i, (n, g) in enumerate(self._room_players)}
        if self._static is not None:
            for sid, game in self._static.games.items():
                if sid in table and not table[sid]["game"]:
                    table[sid]["game"] = game
        names = [s["name"] for s in table.values() if s["name"]]
        groups = group_players(names, load_overrides(self._overrides_path))
        self._slots = table
        self._player_of = {sid: groups[s["name"]] if s["name"] else f"Slot {sid}" for sid, s in table.items()}
        ids = {sid for sid, s in table.items() if s["name"] in self.tracked}
        if ids != self._tracked_ids:
            self._tracked_ids = ids
            self.presence = Presence(ids)
            for sid, at in self._live_check_at.items():
                self.presence.check(sid, at)
        self._me = {self._player_of[sid] for sid in ids}

    # -- listener callbacks ------------------------------------------------------------------------
    def _on_session(self, listener: RoomListener) -> None:
        if self._stopped:
            return
        if listener.seed_name:
            self._open_seed(listener.seed_name)
            if self._room_id:
                self.log.remember_room(self._room_id, listener.seed_name)
        self._refresh_slots()
        self.log.save_state(listening_since=listener.listening_since)
        self._awaiting_statuses = True  # the server's statuses arrive right after Connected
        self._poll_wakeup.set()

    def _on_state(self, listener: RoomListener) -> None:
        if self._stopped:
            return
        listening = listener.status == "listening"
        now = time.time()
        if listening and not self._was_listening:
            self._ever_listened = True
            self._reconnected_at, self._polls_since_reconnect = now, 0
        elif not listening and self._was_listening:
            if self._gap_start is None:
                self._gap_start = now
            self.log.save_state(last_live_at=now)
        self._was_listening = listening
        self._notify()

    def _on_check(self, sender: int, receiver: int, item: int, location: int, flags: int, at: float) -> None:
        if self._stopped:
            return
        entry = CheckEntry(recorded_at=at, at=at, after=None, before=None, src="live", sender=sender,
                           receiver=receiver, item=item, location=location, flags=flags)
        self._live_check_at[sender] = max(at, self._live_check_at.get(sender, at))
        self.presence.check(sender, at)
        if self._record(entry):
            self._queue(entry)
            self._notify()

    def _on_join(self, slot: int, tags: list[str]) -> None:
        if self._stopped:
            return
        self.presence.join(slot, tags)
        self.log.add_presence(time.time(), slot, "join", tags)
        self._notify()

    def _on_part(self, slot: int) -> None:
        if self._stopped:
            return
        self.presence.part(slot)
        self.log.add_presence(time.time(), slot, "part", [])
        self._notify()

    def _on_status(self, slot: int, value: int) -> None:
        if self._stopped:
            return
        if self._awaiting_statuses and self._listener is not None:
            self._awaiting_statuses = False
            self.presence.session_start(self._listener.statuses)
        self.presence.status(slot, value)
        self._notify()

    # -- recording ------------------------------------------------------------------------------------
    def _lookup_name(self, kind: str, game: str | None, ident: int) -> str | None:
        if game is None or self.datapackage.names(game) is None:
            return None
        return getattr(self.datapackage, kind)(game, ident)

    def _record(self, entry: CheckEntry) -> bool:
        sender, receiver = self._slots.get(entry.sender, {}), self._slots.get(entry.receiver, {})
        names = {"sender_name": sender.get("name"), "sender_game": sender.get("game"),
                 "receiver_name": receiver.get("name"), "receiver_game": receiver.get("game"),
                 "item_name": self._lookup_name("item_name", receiver.get("game"), entry.item),
                 "location_name": self._lookup_name("location_name", sender.get("game"), entry.location)}
        added = self.log.add(entry, names)
        if added:
            self._index(entry)
        return added

    # -- polls and catch-up -------------------------------------------------------------------------------
    def _after(self) -> float | None:
        return self._gap_start if self._gap_start is not None else self._prior_live

    async def _poll_loop(self) -> None:
        while True:
            try:
                await self.poll_now()
            except asyncio.CancelledError:
                raise
            except Exception:
                log.exception("roomfeed poll failed")
            interval = self.sleeping_interval if self._room_sleeping() else self.poll_interval
            try:
                await asyncio.wait_for(self._poll_wakeup.wait(), interval)
            except asyncio.TimeoutError:
                pass
            self._poll_wakeup.clear()

    async def poll_now(self) -> None:
        async with self._poll_lock:
            await self._poll()

    async def _poll(self) -> None:
        if not self._room_id or not self.room_url:
            return  # no room link: listening only, no HTTP
        started = time.time()
        errors: list[str] = []
        static_due = self._static_at is None or time.monotonic() - self._static_at >= self.static_interval
        if self._tracker_id is None or static_due:
            try:
                info = await asyncio.to_thread(self._fetch_room, self.room_url)
            except Exception as exc:
                errors.append(_describe(exc))
            else:
                self._tracker_id = info.tracker or None
                self._room_players = list(info.players)
                if not info.tracker:
                    errors.append(NO_TRACKER)
        urls = None
        if self._tracker_id is not None:
            try:
                urls = catchup.api_urls(self.room_url, self._tracker_id)
            except Exception as exc:
                self._tracker_id = None
                errors.append(_describe(exc))
        team = self._listener.team if self._listener is not None and self._listener.team is not None else 0
        if urls is not None and static_due:
            try:
                self._static = catchup.parse_static(await asyncio.to_thread(self._fetch, urls[1]), team)
                self._static_at = time.monotonic()
            except Exception as exc:
                errors.append(_describe(exc))
        if static_due:
            self._refresh_slots()  # the room's slot list, the games and the players file may have changed
        if urls is not None:
            try:
                snapshot = catchup.parse_tracker(await asyncio.to_thread(self._fetch, urls[0]), team)
            except Exception as exc:
                self._tracker_id = None  # look the id up again next time
                errors.append(_describe(exc))
            else:
                polled_at = time.time()
                self._snapshot, self._last_poll_at = snapshot, polled_at
                self._merge(snapshot, polled_at, errors)
                self._close_gap(started)
        self._poll_error = errors[0] if errors else None
        self._notify()

    def _merge(self, snapshot: TrackerSnapshot, polled_at: float, errors: list[str]) -> None:
        if self.log.seed is None:
            errors.append(WAITING_SEED)
            return
        for entry in catchup.missing_entries(snapshot, self.log.keys, polled_at, self._after()):
            if self._record(entry) and entry.after is not None:  # no news flash for the history import
                self._queue(entry)

    def _close_gap(self, started: float) -> None:
        """The listening gap stays open until the *second* poll that started after the reconnection has merged.
        The tracker API lags (cached up to 60 s), so the first poll after a reconnection may still miss checks made
        during the gap: those must keep getting the old `after` when a later poll reveals them."""
        lst = self._listener
        if lst is None or lst.status != "listening" or self._reconnected_at is None:
            return
        if started <= self._reconnected_at:
            return
        self._polls_since_reconnect += 1
        if self._polls_since_reconnect >= 2:
            self._gap_start = self._prior_live = None

    async def _heartbeat_loop(self) -> None:
        while True:
            await asyncio.sleep(self.heartbeat)
            try:
                if self._listener is not None and self._listener.status == "listening":
                    self.log.save_state(last_live_at=time.time())
            except Exception:
                log.exception("roomfeed heartbeat failed")

    # -- events ---------------------------------------------------------------------------------------
    def _queue(self, entry: CheckEntry) -> None:
        self._pending.append(entry)
        if self._flush_task is None or self._flush_task.done():
            self._flush_task = asyncio.create_task(self._flush_soon(), name="roomfeed:flush")

    async def _flush_soon(self) -> None:
        await asyncio.sleep(self.flush_delay)
        batch, self._pending = self._pending, []
        if not batch or self._stopped:
            return
        batch.sort(key=lambda e: e.when, reverse=True)
        try:
            self._publish({"type": "roomfeed_check", "checks": [self._item_json(e) for e in batch[:SSE_BATCH_MAX]]})
        except Exception:
            log.exception("roomfeed: could not publish checks")

    def _notify(self) -> None:
        """Status/summary changed: tell the dashboards, at most every `state_throttle` seconds (trailing call kept)."""
        if self._stopped or (self._notify_task is not None and not self._notify_task.done()):
            return
        wait = self._last_emit + self.state_throttle - time.monotonic()
        if wait <= 0:
            self._emit()
        else:
            self._notify_task = asyncio.create_task(self._emit_later(wait), name="roomfeed:notify")

    async def _emit_later(self, wait: float) -> None:
        await asyncio.sleep(wait)
        self._emit()

    def _emit(self) -> None:
        self._last_emit = time.monotonic()
        try:
            self._publish({"type": "roomfeed", "status": self.status()})
        except Exception:
            log.exception("roomfeed: could not publish status")

    # -- views --------------------------------------------------------------------------------------------
    def _dir(self) -> str | None:
        d = self.log.dir
        if d is None:
            return None
        try:
            return str(d.relative_to(ROOT))
        except ValueError:
            return str(d)

    def status(self) -> dict:
        lst = self._listener
        if lst is None:
            state, error = ("error", NO_SLOT) if not self.slot_name else ("starting", None)
        else:
            error = lst.error
            if lst.status == "listening":
                state = "listening"
            elif lst.status == "error":
                state = "error"
            elif lst.status == "disconnected" or self._ever_listened:
                state = "disconnected"
            else:
                state = "starting"
        listening = lst is not None and lst.status == "listening"
        return {"enabled": True, "state": state, "error": error, "seed": self.log.seed,
                "listening_since": lst.listening_since if listening else None,
                "last_poll_at": self._last_poll_at, "poll_error": self._poll_error,
                "catchup_available": self._room_id is not None, "unreadable_lines": self.log.unreadable_lines,
                "dir": self._dir(), "write_error": self.log.write_error}

    def summary(self) -> dict:
        now = time.time()
        snap, static = self._snapshot, self._static
        live = self._listener.statuses if self._listener is not None else {}
        grouped: dict[str, list[dict]] = {}
        for sid, slot in sorted(self._slots.items()):
            name = slot["name"]
            done = self._counts.get(sid, 0)
            if snap is not None:
                done = max(done, snap.checks_done.get(sid, 0))
            goal = (snap is not None and snap.status.get(sid) == GOAL_STATUS) or live.get(sid) == GOAL_STATUS
            grouped.setdefault(self._player_of[sid], []).append({
                "name": name, "game": slot["game"], "done": done,
                "total": static.totals.get(sid, 0) if static is not None else 0, "goal": goal,
                "presence": self.presence.state(sid, now), "last_check_at": self._last_when.get(sid),
                "bk": self._bk_of(name) if name in self.tracked else None})

        def ratio(done: int, total: int) -> float:
            return done / total if total else 0.0

        players = []
        for player, slots in grouped.items():
            slots.sort(key=lambda s: (-ratio(s["done"], s["total"]), s["name"] or ""))
            last = [s["last_check_at"] for s in slots if s["last_check_at"] is not None]
            players.append({"player": player, "me": player in self._me,
                            "done": sum(s["done"] for s in slots), "total": sum(s["total"] for s in slots),
                            "goals": sum(1 for s in slots if s["goal"]),
                            "playing": sum(1 for s in slots if s["presence"] == "playing"),
                            "last_check_at": max(last) if last else None, "slots": slots})
        players.sort(key=lambda p: (-ratio(p["done"], p["total"]), p["player"]))
        return {"room": {"done": sum(p["done"] for p in players), "total": sum(p["total"] for p in players),
                         "slots": len(self._slots), "goals": sum(p["goals"] for p in players),
                         "playing": sum(p["playing"] for p in players)},
                "players": players}

    def _item_json(self, e: CheckEntry) -> dict:
        s, r = self._slots.get(e.sender, {}), self._slots.get(e.receiver, {})
        return {"key": f"{e.sender}:{e.location}", "at": e.at, "after": e.after, "before": e.before, "src": e.src,
                "sender": s.get("name"), "sender_game": s.get("game"), "sender_player": self._player_of.get(e.sender),
                "receiver": r.get("name"), "receiver_game": r.get("game"),
                "receiver_player": self._player_of.get(e.receiver),
                "item": self._lookup_name("item_name", r.get("game"), e.item),
                "location": self._lookup_name("location_name", s.get("game"), e.location),
                "category": _category(e.flags), "mine": r.get("name") in self.tracked,
                "self": e.sender == e.receiver}

    def checks(self, limit: int = 50, offset: int = 0, player: str | None = None, slot: str | None = None,
               game: str | None = None) -> dict:
        def wanted(e: CheckEntry) -> bool:
            s = self._slots.get(e.sender, {})
            return ((player is None or self._player_of.get(e.sender) == player)
                    and (slot is None or s.get("name") == slot) and (game is None or s.get("game") == game))

        rows = [(e.when, i, e) for i, e in enumerate(self.log.entries) if wanted(e)]
        rows.sort(key=lambda row: (row[0], row[1]), reverse=True)
        offset, limit = max(0, offset), max(0, limit)
        return {"total": len(rows), "offset": offset,
                "items": [self._item_json(e) for _w, _i, e in rows[offset:offset + limit]]}

    def activity(self, bucket: str = "hour", player: str | None = None, now: float | None = None) -> dict:
        starts, end = _bucket_starts(bucket, time.time() if now is None else now)
        buckets = [{"start": start, "count": 0, "by_player": {}} for start in starts]
        undated = 0
        for e in self.log.entries:
            who = self._player_of.get(e.sender) or f"Slot {e.sender}"
            if player is not None and who != player:
                continue
            at = _entry_time(e)
            if at is None:
                undated += 1
                continue
            if at < starts[0] or at >= end:
                continue
            b = buckets[bisect_right(starts, at) - 1]
            b["count"] += 1
            b["by_player"][who] = b["by_player"].get(who, 0) + 1
        return {"bucket": bucket, "buckets": buckets, "undated": undated}


__all__ = ["RoomFeed"]
