"""Logic computation with Universal Tracker's TrackerCore, headless, in a dedicated process.

Only uses what a classic tracker has: the slot's `slot_data` (sent by the server on Connect),
the player's own yaml (optional), the items received and the missing locations.
Never reads a spoiler, multidata or generation zip.

The functions here run inside the worker process (see engine.py). `SlotLogic` is also used
directly by the tests.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os

import tempfile
import time
import traceback
from pathlib import Path
from typing import Any

from .. import apenv

log = logging.getLogger("multitracker.logic")

_ap_ready = False


def setup_ap() -> None:
    """Import Archipelago and its worlds (once per process)."""
    global _ap_ready
    if _ap_ready:
        return
    apenv.setup()
    os.chdir(apenv.AP_DIR)  # AP resolves host.yaml, Players/ etc. relative to its own folder
    import worlds  # noqa: F401  (registers every world, custom ones included)
    _ap_ready = True


class LogicUnavailable(Exception):
    """Logic cannot be computed for this slot (no yaml for a world that needs one, UT disabled...)."""


def _yaml_documents(text: str) -> list[dict[str, Any]]:
    import yaml
    return [d for d in yaml.safe_load_all(text) if isinstance(d, dict)]


def prepare_player_yaml(yaml_path: Path, slot_name: str, game: str, out_dir: Path) -> Path:
    """Copy the player's yaml for this game into out_dir, with `name` forced to the slot name.

    A yaml file may hold several documents (one per game): keep the one for this game.
    """
    import yaml
    docs = _yaml_documents(yaml_path.read_text(encoding="utf-8-sig"))
    if not docs:
        raise LogicUnavailable(f"yaml vide ou invalide : {yaml_path.name}")

    def game_of(doc: dict[str, Any]) -> list[str]:
        g = doc.get("game")
        if isinstance(g, dict):
            return [k for k, w in g.items() if w]
        return [g] if g else []

    matching = [d for d in docs if game in game_of(d)] or (docs if len(docs) == 1 else [])
    if not matching:
        raise LogicUnavailable(f"aucun document du yaml {yaml_path.name} ne concerne {game}")
    doc = dict(matching[0])
    doc["name"] = slot_name
    if isinstance(doc.get("game"), dict):  # weighted game choice: pin the slot's actual game
        doc["game"] = game
    out = out_dir / "player.yaml"
    out.write_text(yaml.safe_dump(doc, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return out


class SlotLogic:
    """One slot's regenerated world, kept between updates."""

    def __init__(self, slot_name: str, game: str, team: int, slot: int, slot_data: dict[str, Any],
                 yaml_path: Path | None, location_ids: set[int] | None = None) -> None:
        setup_ap()
        from worlds.AutoWorld import AutoWorldRegister
        from worlds.tracker.TrackerCore import TrackerCore

        self.slot_name, self.game, self.team, self.slot = slot_name, game, team, slot
        world_cls = AutoWorldRegister.world_types.get(game)
        if world_cls is None:
            raise LogicUnavailable(f"apworld non installé pour « {game} »")
        if getattr(world_cls, "disable_ut", False):
            raise LogicUnavailable("l'auteur de l'apworld a désactivé Universal Tracker pour ce jeu")

        core = TrackerCore(logging.getLogger(f"ut.{slot_name}"), False, False)
        # TrackerCore caches multiworlds per slot_data at class level: keep the cache per slot.
        core.cached_multiworlds = []
        core.cached_slot_data = []
        core.set_slot_params(game, slot, slot_name, team)
        started = time.perf_counter()
        from .adapters import regeneration_patch
        with regeneration_patch(game, world_cls, slot_data, set(location_ids or ())):
            self._regenerate(core, world_cls, slot_name, game, slot_data, yaml_path)
        if core.multiworld is None or core.player_id is None:
            tail = (core.gen_error or "").strip().splitlines()[-1:] or ["raison inconnue"]
            raise RuntimeError(f"régénération du monde impossible : {tail[0][:300]}")
        self.core = core
        self.init_seconds = round(time.perf_counter() - started, 2)

    def _regenerate(self, core, world_cls, slot_name: str, game: str, slot_data: dict[str, Any],
                    yaml_path: Path | None) -> None:
        if getattr(world_cls, "ut_can_gen_without_yaml", False):
            core.initalize_tracker_core(world_cls, slot_data)
            self.mode = "slot_data"
        elif yaml_path is not None:
            if not Path(yaml_path).is_file():
                raise LogicUnavailable(f"yaml introuvable : {yaml_path}")
            with tempfile.TemporaryDirectory(prefix="mt-yaml-") as tmp:
                prepare_player_yaml(Path(yaml_path), slot_name, game, Path(tmp))
                core.player_id = 1
                core.run_generator(None, tmp)  # single-player regeneration from the yaml
                if core.multiworld is not None:
                    core.regen_slots(core.get_current_world(), slot_data, tmp)  # interpret_slot_data hook
            self.mode = "yaml"
        else:
            raise LogicUnavailable("ce jeu a besoin du yaml du joueur (clé `yaml` du slot dans config/room.yaml)")

    def in_logic(self, items: list[dict[str, Any]], missing: set[int]) -> dict[str, Any]:
        """Locations of `missing` reachable with `items`.

        Same sweep as UT's `updateTracker`, with one difference: each received item gets the exact
        classification the server sent (NetworkItem.flags). UT only ORs the flags onto the default
        classification of `create_item`, so items the generator demoted to filler (e.g. Celeste's
        excess Strawberries) would still count as progression and over-estimate the logic.
        Items without a real location (start inventory, server cheats) carry no flags: for those the
        world's default classification is kept.
        """
        from BaseClasses import CollectionState, ItemClassification
        core = self.core
        mw, pid = core.multiworld, core.player_id
        world = mw.worlds[pid]
        state = CollectionState(mw, core.enforce_deferred_connections != _deferred_disabled())
        unknown, errors = [], []
        own_locations = mw.regions.location_cache[pid]
        for net in items:
            code = int(net["item"])
            if code <= 0:
                continue
            name = world.item_id_to_name.get(code)
            if name is None:
                unknown.append(code)
                continue
            try:
                item = mw.create_item(name, pid)
            except Exception:
                errors.append(f"item {name} ne peut pas être créé")
                continue
            loc_id, sender = int(net.get("location", -1)), int(net.get("player", 0))
            if loc_id > 0 and sender == self.slot:
                loc_name = world.location_id_to_name.get(loc_id)
                if loc_name in own_locations:
                    item.location = mw.get_location(loc_name, pid)
            flags = int(net.get("flags", 0))
            if loc_id < 0:
                # Start inventory (-2) and server-given items (-1) are sent with flags 0 whatever the
                # item is: keep the world's own classification for them (like UT does).
                item.classification |= flags
            else:
                item.classification = exact_classification(item.classification, flags, ItemClassification)
            state.collect(item, True)
        if unknown:
            raise RuntimeError(f"datapackage incohérent avec l'apworld installé ({len(unknown)} items inconnus)")
        state.sweep_for_advancements(locations=[loc for loc in mw.get_locations(pid) if not loc.address])
        reachable = sorted({loc.address for loc in mw.get_reachable_locations(state, pid)
                            if isinstance(loc.address, int) and loc.address in missing})
        return {"in_logic": reachable, "errors": errors[:5]}


NETWORK_FLAGS = 0b111  # progression | useful | trap: what NetworkItem.flags carries


def exact_classification(default, flags: int, cls):
    """Classification of a received item from the server's flags.

    The network bits (progression/useful/trap) come from the server; the extra bits of the
    world's default classification (skip_balancing, deprioritized...) are kept only for items
    that really are progression.
    """
    extra = int(default) & ~NETWORK_FLAGS if flags & cls.progression else 0
    return cls(flags & NETWORK_FLAGS | extra)


def _deferred_disabled():
    from worlds.tracker import DeferredEntranceMode
    return DeferredEntranceMode.disabled


def request_key(req: dict[str, Any]) -> str:
    """What makes a regenerated world reusable: same slot, game, slot_data and yaml content."""
    yaml_digest = ""
    if req.get("yaml"):
        try:
            yaml_digest = hashlib.sha256(Path(req["yaml"]).read_bytes()).hexdigest()
        except OSError:
            yaml_digest = "missing"
    payload = json.dumps([req["game"], req["team"], req["slot"], req.get("slot_data"), yaml_digest],
                         sort_keys=True, default=str)
    return hashlib.sha256(payload.encode()).hexdigest()


class Worker:
    """Request handler living in the worker process. One SlotLogic per slot name."""

    def __init__(self) -> None:
        self.slots: dict[str, tuple[str, SlotLogic | Exception]] = {}

    def handle(self, req: dict[str, Any]) -> dict[str, Any]:
        if req.get("op") == "ping":
            setup_ap()
            return {"state": "ok"}
        if req.get("op") == "forget":
            self.slots.pop(req["slot_name"], None)
            return {"state": "ok"}
        name = req["slot_name"]
        key = request_key(req)
        cached = self.slots.get(name)
        if cached is None or cached[0] != key:
            try:
                logic: SlotLogic | Exception = SlotLogic(
                    name, req["game"], req["team"], req["slot"], req.get("slot_data") or {},
                    Path(req["yaml"]) if req.get("yaml") else None,
                    set(req.get("missing", [])) | set(req.get("checked", [])))
            except LogicUnavailable as exc:
                logic = exc
            except Exception as exc:
                log.warning("logic init failed for %s: %s", name, traceback.format_exc())
                logic = exc
            self.slots[name] = (key, logic)
        logic = self.slots[name][1]
        if isinstance(logic, LogicUnavailable):
            return {"state": "unavailable", "message": str(logic)}
        if isinstance(logic, Exception):
            return {"state": "error", "message": f"{type(logic).__name__}: {logic}"[:400]}
        try:
            result = logic.in_logic(req.get("items", []), set(req.get("missing", [])))
        except Exception as exc:
            log.warning("logic update failed for %s: %s", name, traceback.format_exc())
            return {"state": "error", "message": f"{type(exc).__name__}: {exc}"[:400]}
        return {"state": "ok", "mode": logic.mode, **result}


def worker_main(conn) -> None:
    """Entry point of the worker process: answer requests from the pipe until None is received."""
    logging.basicConfig(level=logging.WARNING, format="%(asctime)s logic-worker %(levelname)s %(message)s")
    worker = Worker()
    while True:
        try:
            req = conn.recv()
        except (EOFError, OSError):
            break
        if req is None:
            break
        try:
            res = worker.handle(req)
        except BaseException as exc:  # never let the worker die on a bad request
            res = {"state": "error", "message": f"{type(exc).__name__}: {exc}"[:400]}
        conn.send(res)


