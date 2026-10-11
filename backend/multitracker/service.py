"""Orchestrates one read-only tracker per configured slot, the logic engine and live updates."""
from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

from .ap.tracker import SlotTracker
from .config import RoomConfig, SlotConfig
from .datapackage import DataPackageCache
from .history import History
from .logic import LogicEngine, LogicRequest, LogicResult, NullLogicEngine
from .store import Store

log = logging.getLogger(__name__)

ITEM_FLAG_PROGRESSION, ITEM_FLAG_USEFUL, ITEM_FLAG_TRAP = 1, 2, 4
HINT_STATUS = {0: "unspecified", 10: "no_priority", 20: "avoid", 30: "priority", 40: "found"}
# Changes that can modify which locations are in logic.
LOGIC_KINDS = {"items", "checks", "status", "synced"}


class Service:
    def __init__(self, config: RoomConfig, store: Store, logic: LogicEngine | None = None,
                 logic_debounce: float = 1.0, publish_debounce: float = 0.3,
                 reconnect_delays: tuple[float, float] = (2.0, 60.0)) -> None:
        self.config = config
        self.store = store
        self.datapackage = DataPackageCache(store)
        self.history = History(store)
        self.logic_engine = logic or NullLogicEngine()
        self.logic_debounce = logic_debounce
        self.publish_debounce = publish_debounce
        self.reconnect_delays = reconnect_delays
        self.trackers: dict[str, SlotTracker] = {}
        self.slot_configs: dict[str, SlotConfig] = {s.name: s for s in config.slots}
        self.logic: dict[str, LogicResult] = {}
        self._logic_tasks: dict[str, asyncio.Task] = {}
        self._logic_dirty: set[str] = set()
        self._session: dict[str, int] = {}  # bumped on every (re)connection: results of older sessions are dropped
        self._publish_pending: set[str] = set()
        self._publish_task: asyncio.Task | None = None
        self.subscribers: set[asyncio.Queue] = set()
        self.started_at = time.time()
        self.current_server = config.server
        self.room_error: str | None = None
        self.room_sleeping = False
        self._wake_lock = asyncio.Lock()
        self._last_room_event: dict[str, Any] | None = None
        self._room_task: asyncio.Task | None = None
        self._room_checked_at = 0.0
        self._room_woken_at = 0.0
        self._reload_lock = asyncio.Lock()

    # -- lifecycle -----------------------------------------------------------------------
    async def start(self) -> None:
        await self.logic_engine.start()
        self._start_trackers()

    def _start_trackers(self) -> None:
        self.current_server = self.config.server
        if self.config.room_url:
            self.refresh_room(force=True)
        for slot in self.config.slots:
            tracker = SlotTracker(lambda: self.current_server, self.config.password, slot.name, slot.game or "",
                                  self.datapackage, on_change=self._on_change,
                                  min_delay=self.reconnect_delays[0], max_delay=self.reconnect_delays[1],
                                  on_connect_error=lambda _t: self.refresh_room())
            self.trackers[slot.name] = tracker
            self.logic[slot.name] = LogicResult("pending")
            tracker.start()

    async def _stop_trackers(self) -> None:
        # Trackers first (stopping them may still schedule logic/publish tasks), then every task.
        await asyncio.gather(*(t.stop() for t in self.trackers.values()), return_exceptions=True)
        self.history.flush()
        tasks = [t for t in [*self._logic_tasks.values(), self._publish_task, self._room_task] if t is not None]
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        self.trackers, self.logic, self._logic_tasks = {}, {}, {}
        self._logic_dirty, self._publish_pending = set(), set()
        self._publish_task = self._room_task = None

    async def stop(self) -> None:
        await self._stop_trackers()
        await self.logic_engine.stop()

    async def reload(self, config: RoomConfig, before_start=None) -> None:
        """Apply a new room configuration (from the web UI) without restarting the app.
        `before_start` (e.g. saving the file) runs under the same lock, between stop and start."""
        async with self._reload_lock:
            await self._stop_trackers()
            if before_start is not None:
                before_start()
            self.config = config
            self.slot_configs = {s.name: s for s in config.slots}
            self.room_error, self._room_checked_at, self._room_woken_at = None, 0.0, 0.0
            self.room_sleeping = False
            self._start_trackers()
        self._broadcast({"type": "snapshot", "slots": [self.summary(n) for n in self.trackers]})
        self._publish_room()

    # -- archipelago.gg room: the port changes when a sleeping room wakes up ------------------
    def refresh_room(self, force: bool = False, min_interval: float = 60.0) -> None:
        if not self.config.room_url:
            return
        if self._room_task is not None and not self._room_task.done():
            return
        if not force and time.monotonic() - self._room_checked_at < min_interval:
            return
        self._room_checked_at = time.monotonic()
        # Loading the room page wakes a sleeping room up. Only with the "wake_room" option (off by default:
        # the tracker alone must not keep the room awake), and at most every 10 minutes.
        wake = self.config.wake_room and time.monotonic() - self._room_woken_at > 600
        if wake:
            self._room_woken_at = time.monotonic()
        self._room_task = asyncio.create_task(self._refresh_room(wake))

    async def wake_room_now(self) -> bool:
        """One explicit wake-up ("Réveiller maintenant"), whatever the wake_room option says. Serialised and
        rate-limited: the room page is loaded at most every 30 seconds. Returns False when rate-limited."""
        if not self.config.room_url:
            raise ValueError("aucune room archipelago.gg configurée")
        async with self._wake_lock:
            if self._room_task is not None and not self._room_task.done():
                await asyncio.gather(self._room_task, return_exceptions=True)
            woke = time.monotonic() - self._room_woken_at > 30
            if woke:
                self._room_checked_at = self._room_woken_at = time.monotonic()
                self._room_task = asyncio.create_task(self._refresh_room(True))
                await self._room_task
        for tracker in self.trackers.values():
            tracker.retry_now()
        return woke

    async def _refresh_room(self, wake: bool = True) -> None:
        from .room import RoomError, fetch_room
        try:
            info = await asyncio.to_thread(fetch_room, self.config.room_url, 15.0, wake)
        except Exception as exc:  # RoomError, or an unexpected answer from the site
            self.room_error = str(exc) if isinstance(exc, RoomError) else f"réponse inattendue du site : {exc}"[:300]
            self.room_sleeping = False  # unknown: the site could not be read
            log.warning("room refresh failed: %s", exc)
            self._publish_room()
            return
        self.room_sleeping = info.sleeping and not wake
        if self.room_sleeping:
            self.room_error = ("room endormie : elle redémarre quand quelqu'un ouvre son lien "
                               "(ou bouton « Réveiller maintenant »)")
        else:
            self.room_error = None if info.server else "la room ne publie pas de port (endormie ?)"
        if info.server and info.server != self.current_server:
            log.info("room server is now %s (was %s)", info.server, self.current_server)
            self.current_server = info.server
        self._publish_room()

    # -- change handling -----------------------------------------------------------------
    def _on_change(self, tracker: SlotTracker, kinds: set[str]) -> None:
        name = tracker.state.name
        if "connected" in kinds and self.room_sleeping:  # someone woke the room up
            self.room_sleeping, self.room_error = False, None
            self._publish_room()
        st = tracker.state
        if st.seed_name and st.status != "connected":
            self.history.lost(st.seed_name, name)
        elif st.synced and st.seed_name and kinds & {"items", "synced", "checks"}:
            self.history.on_items(st.seed_name, name, len(st.items), fresh="synced" in kinds)
            if "checks" in kinds and "connected" not in kinds:
                self.history.on_checks(st.seed_name, name, st.new_checks)
        if "connected" in kinds:
            self._session[name] = self._session.get(name, 0) + 1
            self.logic[name] = LogicResult("pending")  # never show the previous session's results
        if kinds & LOGIC_KINDS and tracker.state.status == "connected":
            self._schedule_logic(name)
        self.publish(name)

    def _schedule_logic(self, name: str) -> None:
        self._logic_dirty.add(name)
        task = self._logic_tasks.get(name)
        if task is None or task.done():
            self._logic_tasks[name] = asyncio.create_task(self._logic_loop(name), name=f"logic:{name}")

    async def _logic_loop(self, name: str) -> None:
        # Debounce: wait for the burst of updates to settle, recompute, repeat while new changes arrived.
        while name in self._logic_dirty:
            await asyncio.sleep(self.logic_debounce)
            self._logic_dirty.discard(name)
            st = self.trackers[name].state
            if st.status != "connected" or st.slot is None or not st.synced:
                return  # "synced" schedules a new computation once the item list is complete
            session = self._session.get(name, 0)
            request = LogicRequest(slot_name=name, game=st.game, team=st.team, slot=st.slot,
                                   slot_data=st.slot_data, yaml=self.slot_configs[name].yaml,
                                   items=list(st.items), missing=set(st.missing), checked=set(st.checked),
                                   seed_name=st.seed_name,
                                   checksum=st.datapackage_checksums.get(st.game) or "")  # "": unknown (D12)
            started = time.perf_counter()
            try:
                result = await self.logic_engine.compute(request)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                log.exception("logic failed for %s", name)
                result = LogicResult("error", message=f"{type(exc).__name__}: {exc}"[:300])
            result.seconds = round(time.perf_counter() - started, 3)
            if self._session.get(name, 0) != session:
                continue  # reconnected (maybe to another seed) meanwhile: this result is stale
            # Locations checked since the request was built are no longer "to do".
            result.in_logic = [loc for loc in result.in_logic if loc in self.trackers[name].state.missing]
            self.logic[name] = result
            self.publish(name)

    def logic_settled(self, name: str) -> bool:
        """True when no logic recomputation is pending or running for this slot."""
        task = self._logic_tasks.get(name)
        return name not in self._logic_dirty and (task is None or task.done())

    def publish(self, name: str) -> None:
        self._publish_pending.add(name)
        if self._publish_task is None or self._publish_task.done():
            self._publish_task = asyncio.create_task(self._publish_soon())

    async def _publish_soon(self) -> None:
        await asyncio.sleep(self.publish_debounce)
        names, self._publish_pending = self._publish_pending, set()
        for name in names:
            if name in self.trackers:
                try:
                    self._broadcast({"type": "slot", "slot": self.summary(name)})
                except Exception:
                    log.exception("could not publish %s", name)

    def room_event(self) -> dict[str, Any]:
        return {"type": "room", "server": self.current_server, "room_url": self.config.room_url,
                "room_error": self.room_error, "room_sleeping": self.room_sleeping}

    def _publish_room(self) -> None:
        """Push the room status (error, sleeping, port) to the dashboards when it changed."""
        event = self.room_event()
        if event != self._last_room_event:
            self._last_room_event = event
            self._broadcast(event)

    def _broadcast(self, event: dict[str, Any]) -> None:
        for queue in list(self.subscribers):
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:  # slow client: end its stream, EventSource reconnects with a snapshot
                self.subscribers.discard(queue)
                queue.get_nowait()
                queue.put_nowait({"type": "_close"})

    def subscribe(self) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue(maxsize=1000)
        self.subscribers.add(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue) -> None:
        self.subscribers.discard(queue)

    # -- "last visit" --------------------------------------------------------------------
    def seen_count(self, name: str) -> int:
        st = self.trackers[name].state
        if not st.seed_name:
            return len(st.items)
        count = self.store.seen_count(st.seed_name, name)
        return 0 if count is None else min(count, len(st.items))

    def mark_seen(self, name: str, count: int | None = None) -> int:
        st = self.trackers[name].state
        if not st.seed_name or not st.synced:
            raise ValueError("slot pas encore synchronisé avec le serveur")
        count = len(st.items) if count is None else max(0, min(int(count), len(st.items)))
        self.store.set_seen_count(st.seed_name, name, count)
        self.publish(name)
        return count

    # -- views ---------------------------------------------------------------------------
    def player_name(self, st, slot: int) -> str:
        if slot == 0:
            return "Archipelago"
        info = st.players.get(slot) or {}
        return info.get("alias") or info.get("name") or f"Joueur {slot}"

    def player_game(self, st, slot: int) -> str | None:
        if slot == 0:
            return "Archipelago"
        return (st.players.get(slot) or {}).get("game")

    def _hint_view(self, st, hint: dict[str, Any], in_logic: set[int]) -> dict[str, Any]:
        finder, receiver = hint.get("finding_player"), hint.get("receiving_player")
        location, item = hint.get("location"), hint.get("item")
        flags = hint.get("item_flags", 0) or 0
        return {
            "item": self.datapackage.item_name(self.player_game(st, receiver), item),
            "item_id": item,
            "location": self.datapackage.location_name(self.player_game(st, finder), location),
            "location_id": location,
            "finder": self.player_name(st, finder),
            "finder_game": self.player_game(st, finder),
            "receiver": self.player_name(st, receiver),
            "receiver_game": self.player_game(st, receiver),
            "found": bool(hint.get("found")),
            "entrance": hint.get("entrance") or "",
            "status": HINT_STATUS.get(hint.get("status", 0), "unspecified"),
            "progression": bool(flags & ITEM_FLAG_PROGRESSION),
            "useful": bool(flags & ITEM_FLAG_USEFUL),
            "trap": bool(flags & ITEM_FLAG_TRAP),
            "in_logic": finder == st.slot and location in in_logic and not hint.get("found"),
        }

    def _hints(self, name: str) -> tuple[list[dict], list[dict]]:
        st = self.trackers[name].state
        in_logic = set(self.logic.get(name, LogicResult("pending")).in_logic)
        mine_elsewhere, in_my_world = [], []
        for hint in st.hints:
            view = self._hint_view(st, hint, in_logic)
            if hint.get("finding_player") == st.slot:
                in_my_world.append(view)
            elif hint.get("receiving_player") == st.slot:
                mine_elsewhere.append(view)
        return mine_elsewhere, in_my_world

    def summary(self, name: str) -> dict[str, Any]:
        tracker = self.trackers[name]
        st = tracker.state
        cfg = self.slot_configs[name]
        logic = self.logic.get(name, LogicResult("pending"))
        total = len(st.checked) + len(st.missing)
        seen = self.seen_count(name)
        mine_elsewhere, in_my_world = self._hints(name)
        hinted_in_logic = sum(1 for h in in_my_world if h["in_logic"])
        return {
            "name": name,
            "game": st.game or cfg.game,
            "owner": cfg.owner,
            "status": st.status,
            "error": st.error,
            "seed_name": st.seed_name,
            "checks": {"done": len(st.checked), "total": total, "remaining": len(st.missing)},
            "items": {"received": len(st.items), "new": max(0, len(st.items) - seen)},
            "hints": {"mine_elsewhere": sum(1 for h in mine_elsewhere if not h["found"]),
                      "in_my_world": sum(1 for h in in_my_world if not h["found"]),
                      "in_my_world_in_logic": hinted_in_logic},
            "goal": st.goal_reached,
            "last_check_at": self.history.last_check(st.seed_name, name) if st.seed_name else None,
            "logic": logic.to_json(),
            "updated_at": st.updated_at,
        }

    def detail(self, name: str) -> dict[str, Any]:
        st = self.trackers[name].state
        seen = self.seen_count(name)
        times = self.history.times(st.seed_name, name) if st.seed_name else []
        items = []
        for index, item in enumerate(st.items):
            received_at, received_after = times[index] if index < len(times) else (None, None)
            sender = item.get("player", 0)
            flags = item.get("flags", 0) or 0
            location = item.get("location")
            location = -1 if location is None else location
            origin = ("start" if location == -2 else "server" if location < 0 or sender == 0
                      else "own" if sender == st.slot else "other")
            items.append({
                "index": index,
                "name": self.datapackage.item_name(st.game, item.get("item")),
                "sender": self.player_name(st, sender),
                "own": sender == st.slot,
                "origin": origin,  # start (inventaire de départ) | server | own | other
                "location": self.datapackage.location_name(self.player_game(st, sender), item.get("location"))
                if location >= 0 else None,
                "progression": bool(flags & ITEM_FLAG_PROGRESSION),
                "useful": bool(flags & ITEM_FLAG_USEFUL),
                "trap": bool(flags & ITEM_FLAG_TRAP),
                "new": index >= seen,
                "received_at": received_at,  # null: before the app tracked this slot
                "received_after": received_after,  # set: received between received_after and received_at
            })
        mine_elsewhere, in_my_world = self._hints(name)
        hinted = {h["location_id"]: h for h in in_my_world if not h["found"]}
        logic = self.logic.get(name, LogicResult("pending"))
        in_logic = [{
            "id": loc,
            "name": self.datapackage.location_name(st.game, loc),
            "region": logic.regions.get(loc),
            "hint": ({"item": hinted[loc]["item"], "receiver": hinted[loc]["receiver"],
                      "progression": hinted[loc]["progression"]} if loc in hinted else None),
        } for loc in logic.in_logic]
        in_logic.sort(key=lambda loc: (loc["hint"] is None, loc["name"]))
        return {
            **self.summary(name),
            "items_list": items,
            "hints_mine_elsewhere": mine_elsewhere,
            "hints_in_my_world": in_my_world,
            "in_logic_locations": in_logic,
            "players": {str(k): {"name": self.player_name(st, k), "game": v.get("game")}
                        for k, v in st.players.items()},
        }
