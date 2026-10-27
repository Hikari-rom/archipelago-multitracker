"""Indices page (M26): the hints of every tracked slot in one table, with whether the player who has to do the check
can do it now, and what blocks it otherwise.

Each tracked slot already receives its hints (`_read_hints_<team>_<slot>`): the ones for its items, wherever they
are, and the ones for the items in its world. The accessibility of a hint is the logic of the slot that has to do the
check (the "finder"): a tracked slot's logic, or, for a slot nobody tracks here, the logic of a read-only "foreign"
tracker the board keeps for it (option `hints_foreign_logic`). Only the slots holding hinted items of tracked slots
are followed that way, at most FOREIGN_MAX, and only while those hints are not found.
"""
from __future__ import annotations

import asyncio
import logging
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any

from .ap.tracker import SlotTracker
from .logic import LogicRequest, LogicResult

if TYPE_CHECKING:
    from .service import Service

log = logging.getLogger(__name__)

FOREIGN_MAX = 12  # untracked slots followed for their logic (each one is a connection and a world in the worker)
FOREIGN_DEBOUNCE = 5.0  # seconds: a followed slot's logic waits for its updates to settle
PUBLISH_DEBOUNCE = 1.0
LOGIC_KINDS = {"items", "checks", "status", "synced"}
HINT_STATUS = {0: "unspecified", 10: "no_priority", 20: "avoid", 30: "priority", 40: "found"}
ITEM_FLAG_PROGRESSION, ITEM_FLAG_USEFUL, ITEM_FLAG_TRAP = 1, 2, 4


def hinted_locations(st, finder: int | None = None) -> set[int]:
    """Locations of not found hints whose item is in the world of `finder` (default: the slot itself)."""
    finder = st.slot if finder is None else finder
    return {int(h["location"]) for h in st.hints if h.get("finding_player") == finder and not h.get("found")}


class HintsBoard:
    def __init__(self, service: Service) -> None:
        self.service = service
        self.trackers: dict[str, SlotTracker] = {}  # foreign slot name -> its read-only tracker
        self.logic: dict[str, LogicResult] = {}
        self.capped: set[str] = set()  # slots that would be followed but for FOREIGN_MAX
        self._tasks: dict[str, asyncio.Task] = {}
        self._dirty: set[str] = set()
        self._session: dict[str, int] = {}
        self._reconcile_task: asyncio.Task | None = None
        self._publish_task: asyncio.Task | None = None

    # -- foreign slots ----------------------------------------------------------------------
    def wanted(self) -> dict[str, tuple[str, int]]:
        """Untracked slots holding not found hinted items of tracked slots: name -> (game, hints)."""
        out: dict[str, tuple[str, int]] = {}
        seen: set[tuple[int, int]] = set()
        for tracker in self.service.trackers.values():
            st = tracker.state
            for hint in st.hints:
                finder, location = hint.get("finding_player"), hint.get("location")
                if hint.get("found") or not finder or finder == st.slot or (finder, location) in seen:
                    continue
                seen.add((finder, location))
                info = st.players.get(finder) or {}
                name, game = info.get("name"), info.get("game")
                if not name or not game or name in self.service.trackers:
                    continue
                out[name] = (game, out.get(name, (game, 0))[1] + 1)
        return out

    def reconcile_soon(self) -> None:
        if self._reconcile_task is None or self._reconcile_task.done():
            self._reconcile_task = asyncio.create_task(self._reconcile(), name="hints:reconcile")

    async def _reconcile(self) -> None:
        await asyncio.sleep(PUBLISH_DEBOUNCE)
        wanted = self.wanted() if self.service.config.hints_foreign_logic else {}
        ranked = sorted(wanted, key=lambda n: (-wanted[n][1], n))
        keep = set(ranked[:FOREIGN_MAX])
        self.capped = set(ranked[FOREIGN_MAX:])
        for name in [n for n in self.trackers if n not in keep]:
            await self._drop(name)
        for name in ranked[:FOREIGN_MAX]:
            if name not in self.trackers:
                self._start(name, wanted[name][0])
        self.publish()

    def _start(self, name: str, game: str) -> None:
        s = self.service
        tracker = SlotTracker(lambda: s.current_server, s.config.password, name, game, s.datapackage,
                              on_change=self._on_change, min_delay=s.reconnect_delays[0],
                              max_delay=s.reconnect_delays[1], on_connect_error=lambda _t: s.refresh_room())
        self.trackers[name] = tracker
        self.logic[name] = LogicResult("pending")
        log.info("hints: following %s (%s) for its logic", name, game)
        tracker.start()

    async def _drop(self, name: str) -> None:
        tracker = self.trackers.pop(name, None)
        task = self._tasks.pop(name, None)
        if task is not None:
            task.cancel()
        self._dirty.discard(name)
        self.logic.pop(name, None)
        if tracker is not None:
            await tracker.stop()
        await self.service.logic_engine.forget(name)

    async def stop(self) -> None:
        for task in (self._reconcile_task, self._publish_task):
            if task is not None:
                task.cancel()
        for name in list(self.trackers):
            await self._drop(name)
        self.capped = set()

    def restart_logic(self) -> None:
        for name, tracker in self.trackers.items():
            self._session[name] = self._session.get(name, 0) + 1
            self.logic[name] = LogicResult("pending")
            if tracker.state.status == "connected":
                self._schedule(name)

    def _on_change(self, tracker: SlotTracker, kinds: set[str]) -> None:
        name = tracker.state.name
        if name not in self.trackers:
            return
        if "connected" in kinds:
            self._session[name] = self._session.get(name, 0) + 1
            self.logic[name] = LogicResult("pending")
        if kinds & LOGIC_KINDS and tracker.state.status == "connected":
            self._schedule(name)
        if kinds & {"connected", "status"}:
            self.publish()

    def schedule_explain(self) -> None:
        """Hints changed: the hinted locations of the followed slots may have too."""
        for name, tracker in self.trackers.items():
            if tracker.state.status == "connected":
                self._schedule(name)

    def _schedule(self, name: str) -> None:
        self._dirty.add(name)
        task = self._tasks.get(name)
        if task is None or task.done():
            self._tasks[name] = asyncio.create_task(self._logic_loop(name), name=f"hints-logic:{name}")

    def _explain_for(self, name: str) -> set[int]:
        """Hinted locations of the foreign slot `name`, from the hints of the tracked slots."""
        out: set[int] = set()
        for tracker in self.service.trackers.values():
            st = tracker.state
            finder = next((sid for sid, p in st.players.items() if p.get("name") == name), None)
            if finder is not None:
                out |= hinted_locations(st, finder)
        return out

    async def _logic_loop(self, name: str) -> None:
        while name in self._dirty:
            await asyncio.sleep(FOREIGN_DEBOUNCE)
            self._dirty.discard(name)
            tracker = self.trackers.get(name)
            if tracker is None:
                return
            st = tracker.state
            if st.status != "connected" or st.slot is None or not st.synced:
                return
            session = self._session.get(name, 0)
            request = LogicRequest(slot_name=name, game=st.game, team=st.team, slot=st.slot, slot_data=st.slot_data,
                                   yaml=self.yaml_of(name, st.game), items=list(st.items), missing=set(st.missing),
                                   checked=set(st.checked), seed_name=st.seed_name,
                                   checksum=st.datapackage_checksums.get(st.game) or "",
                                   explain=self._explain_for(name) & st.missing)
            started = time.perf_counter()
            try:
                result = await self.service.logic_engine.compute(request)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                log.exception("logic failed for followed slot %s", name)
                result = LogicResult("error", message=f"{type(exc).__name__}: {exc}"[:300])
            result.seconds = round(time.perf_counter() - started, 3)
            if self._session.get(name, 0) != session or name not in self.trackers:
                continue
            result.in_logic = [loc for loc in result.in_logic if loc in st.missing]
            self.logic[name] = result
            self.publish()

    @staticmethod
    def yaml_of(name: str, game: str) -> Path | None:
        """The player's yaml when config/players/ has one for this slot (same name and game)."""
        from .config import ROOT
        from .players import list_yamls
        for entry in list_yamls():
            if any(p["name"] == name and p["game"] == game for p in entry["players"]):
                return ROOT / entry["path"]
        return None

    # -- live updates -----------------------------------------------------------------------
    def publish(self) -> None:
        """Tell the pages the table changed (they fetch /api/hints again)."""
        if self._publish_task is None or self._publish_task.done():
            self._publish_task = asyncio.create_task(self._publish_soon(), name="hints:publish")

    async def _publish_soon(self) -> None:
        await asyncio.sleep(PUBLISH_DEBOUNCE)
        self.service._broadcast({"type": "hints"})

    # -- the table ----------------------------------------------------------------------------
    def _access(self, finder_name: str | None, location: int, found: bool) -> dict[str, Any]:
        if found:
            return {"state": "found"}
        s = self.service
        if finder_name in s.trackers:
            tracker, logic = s.trackers[finder_name], s.logic.get(finder_name)
        elif finder_name in self.trackers:
            tracker, logic = self.trackers[finder_name], self.logic.get(finder_name)
        else:
            reason = ("slot non suivi : le suivi des autres joueurs est désactivé (page Configuration)"
                      if not s.config.hints_foreign_logic else
                      f"slot non suivi : au plus {FOREIGN_MAX} autres slots sont suivis" if finder_name in self.capped
                      else "slot non suivi")
            return {"state": "unknown", "reason": reason}
        if location in tracker.state.checked:
            return {"state": "found"}
        if tracker.state.status != "connected":
            return {"state": "pending", "reason": "connexion au slot…"}
        if logic is None or logic.state == "pending":
            return {"state": "pending", "reason": "calcul en cours"}
        if logic.state != "ok":
            return {"state": "unknown", "reason": logic.message or "logique indisponible pour ce jeu"}
        if location in logic.in_logic:
            return {"state": "ok"}
        out: dict[str, Any] = {"state": "blocked"}
        if location in logic.blockers:
            out["blockers"] = logic.blockers[location]
        return out

    def table(self) -> dict[str, Any]:
        s = self.service
        rows: dict[tuple[int, int], dict[str, Any]] = {}
        for name, tracker in s.trackers.items():
            st = tracker.state
            for hint in st.hints:
                finder, receiver = hint.get("finding_player"), hint.get("receiving_player")
                location, item = hint.get("location"), hint.get("item")
                key = (finder, location)
                row = rows.get(key)
                if row is None:
                    finder_name = (st.players.get(finder) or {}).get("name")
                    receiver_name = (st.players.get(receiver) or {}).get("name")
                    flags = hint.get("item_flags", 0) or 0
                    found = bool(hint.get("found"))
                    row = rows[key] = {
                        "item": s.datapackage.item_name(s.player_game(st, receiver), item),
                        "item_id": item,
                        "location": s.datapackage.location_name(s.player_game(st, finder), location),
                        "location_id": location,
                        "finder": s.player_name(st, finder),
                        "finder_slot": finder_name,
                        "finder_game": s.player_game(st, finder),
                        "receiver": s.player_name(st, receiver),
                        "receiver_slot": receiver_name,
                        "receiver_game": s.player_game(st, receiver),
                        "found": found,
                        "entrance": hint.get("entrance") or "",
                        "status": HINT_STATUS.get(hint.get("status", 0), "unspecified"),
                        "progression": bool(flags & ITEM_FLAG_PROGRESSION),
                        "useful": bool(flags & ITEM_FLAG_USEFUL),
                        "trap": bool(flags & ITEM_FLAG_TRAP),
                        "finder_tracked": finder_name in s.trackers,
                        "receiver_tracked": receiver_name in s.trackers,
                        "slots": [],
                        "access": self._access(finder_name, location, found),
                    }
                elif hint.get("found") and not row["found"]:  # another slot's copy is fresher
                    row["found"], row["access"] = True, {"state": "found"}
                if name not in row["slots"]:
                    row["slots"].append(name)
        followed = [{"name": n, "game": t.state.game, "status": t.state.status,
                     "logic": self.logic.get(n, LogicResult("pending")).to_json()} for n, t in self.trackers.items()]
        return {"hints": list(rows.values()), "foreign": {"enabled": s.config.hints_foreign_logic,
                                                          "max": FOREIGN_MAX, "followed": followed,
                                                          "capped": sorted(self.capped)},
                "now": time.time()}
