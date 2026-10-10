"""Orchestrates one read-only tracker per configured slot, the logic engine and live updates."""
from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

from .ap.tracker import SlotTracker
from .config import RoomConfig, SlotConfig
from .datapackage import DataPackageCache
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
        self.logic_engine = logic or NullLogicEngine()
        self.logic_debounce = logic_debounce
        self.publish_debounce = publish_debounce
        self.reconnect_delays = reconnect_delays
        self.trackers: dict[str, SlotTracker] = {}
        self.slot_configs: dict[str, SlotConfig] = {s.name: s for s in config.slots}
        self.logic: dict[str, LogicResult] = {}
        self._logic_tasks: dict[str, asyncio.Task] = {}
        self._logic_dirty: set[str] = set()
        self._publish_pending: set[str] = set()
        self._publish_task: asyncio.Task | None = None
        self.subscribers: set[asyncio.Queue] = set()
        self.started_at = time.time()

    # -- lifecycle -----------------------------------------------------------------------
    async def start(self) -> None:
        await self.logic_engine.start()
        for slot in self.config.slots:
            tracker = SlotTracker(self.config.server, self.config.password, slot.name, slot.game or "",
                                  self.datapackage, on_change=self._on_change,
                                  min_delay=self.reconnect_delays[0], max_delay=self.reconnect_delays[1])
            self.trackers[slot.name] = tracker
            self.logic[slot.name] = LogicResult("pending")
            tracker.start()

    async def stop(self) -> None:
        for task in [*self._logic_tasks.values(), self._publish_task]:
            if task is not None:
                task.cancel()
        await asyncio.gather(*(t.stop() for t in self.trackers.values()), return_exceptions=True)
        await self.logic_engine.stop()

    # -- change handling -----------------------------------------------------------------
    def _on_change(self, tracker: SlotTracker, kinds: set[str]) -> None:
        name = tracker.state.name
        if "connected" in kinds:
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
            if st.status != "connected" or st.slot is None:
                return
            request = LogicRequest(slot_name=name, game=st.game, team=st.team, slot=st.slot,
                                   slot_data=st.slot_data, yaml=self.slot_configs[name].yaml,
                                   items=list(st.items), missing=set(st.missing), checked=set(st.checked))
            started = time.perf_counter()
            try:
                result = await self.logic_engine.compute(request)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                log.exception("logic failed for %s", name)
                result = LogicResult("error", message=f"{type(exc).__name__}: {exc}"[:300])
            result.seconds = round(time.perf_counter() - started, 3)
            # Locations checked since the request was built are no longer "to do".
            result.in_logic = [loc for loc in result.in_logic if loc in self.trackers[name].state.missing]
            self.logic[name] = result
            self.publish(name)

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
            "logic": logic.to_json(),
            "updated_at": st.updated_at,
        }

    def detail(self, name: str) -> dict[str, Any]:
        st = self.trackers[name].state
        seen = self.seen_count(name)
        items = []
        for index, item in enumerate(st.items):
            sender = item.get("player", 0)
            flags = item.get("flags", 0) or 0
            items.append({
                "index": index,
                "name": self.datapackage.item_name(st.game, item.get("item")),
                "sender": self.player_name(st, sender),
                "own": sender == st.slot,
                "location": self.datapackage.location_name(self.player_game(st, sender), item.get("location"))
                if (item.get("location") or -1) >= 0 else None,
                "progression": bool(flags & ITEM_FLAG_PROGRESSION),
                "useful": bool(flags & ITEM_FLAG_USEFUL),
                "trap": bool(flags & ITEM_FLAG_TRAP),
                "new": index >= seen,
            })
        mine_elsewhere, in_my_world = self._hints(name)
        hinted = {h["location_id"]: h for h in in_my_world if not h["found"]}
        logic = self.logic.get(name, LogicResult("pending"))
        in_logic = [{
            "id": loc,
            "name": self.datapackage.location_name(st.game, loc),
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
