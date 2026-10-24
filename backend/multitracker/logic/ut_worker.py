"""Logic computation with Universal Tracker's TrackerCore, headless, in a dedicated process.

Only uses what a classic tracker has: the slot's `slot_data` (sent by the server on Connect),
the player's own yaml (optional), the items received and the missing locations.
Never reads a spoiler, multidata or generation zip.

The functions here run inside the worker process (see engine.py). `SlotLogic` is also used
directly by the tests.
"""
from __future__ import annotations

import contextlib
import gc
import hashlib
import json
import logging
import os
import re
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
    with world_loading_summary():
        import worlds  # noqa: F401  (registers every world, custom ones included)
    _ap_ready = True


WORLD_NOT_LOADED = re.compile(r"Could not load world WorldSource\(([^,)]+)")
NO_MANIFEST = re.compile(r"Invalid or missing manifest file for .*?([^/\\]+)\.apworld")
MANIFEST_NOTES = ("compatible_version - This might be", "There is no item named 'archipelago.json'")


@contextlib.contextmanager
def world_loading_summary():
    """Archipelago logs a traceback for every core world whose dependencies are not installed here and
    warnings for apworlds without a manifest: hundreds of harmless lines at each worker start. Log one
    summary line instead (with the names), and pass every other message through."""
    root = logging.getLogger()
    records: list[logging.LogRecord] = []

    class Collect(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            records.append(record)

    saved = root.handlers[:]
    root.handlers = [Collect()]
    try:
        yield
    finally:
        root.handlers = saved
        not_loaded, no_manifest = [], []
        for record in records:
            message = record.getMessage()
            if (m := WORLD_NOT_LOADED.search(message)):
                not_loaded.append(m.group(1))
            elif (m := NO_MANIFEST.search(message)):
                no_manifest.append(m.group(1))
            elif not message.startswith(MANIFEST_NOTES):
                root.handle(record)
        if not_loaded or no_manifest:
            log.warning("Archipelago worlds: %d not loaded (missing dependencies): %s; "
                        "%d apworlds without manifest (AP 0.7 warning, harmless on 0.6.7): %s",
                        len(not_loaded), ", ".join(sorted(not_loaded)) or "-",
                        len(no_manifest), ", ".join(sorted(no_manifest)) or "-")


class LogicUnavailable(Exception):
    """Logic cannot be computed for this slot (no yaml for a world that needs one, UT disabled...)."""


def adapter_refusal(gen_error: str) -> str | None:
    """Universal Tracker catches what an adapter raises during the generation and keeps only the traceback:
    the message of the last LogicUnavailable in it, if any."""
    refused = [line.split("LogicUnavailable: ", 1)[1] for line in gen_error.splitlines() if "LogicUnavailable: " in line]
    return refused[-1].strip() if refused else None


def _yaml_documents(text: str) -> list[dict[str, Any]]:
    import yaml
    return [d for d in yaml.safe_load_all(text) if isinstance(d, dict)]


def _is_random(value: Any) -> bool:
    """A yaml option value that is rolled at generation time (so possibly not what the seed got)."""
    if isinstance(value, str):
        return value.strip().lower().startswith("random")
    if isinstance(value, dict) and value:
        weighted = [k for k, w in value.items() if isinstance(w, (int, float)) and w > 0]
        if len(weighted) == len(value):  # a weights table, not a plain dict option
            return len(weighted) > 1 or any(_is_random(k) for k in weighted)
    return False


def prepare_player_yaml(yaml_path: Path, slot_name: str, game: str, out_dir: Path,
                        slot_data: dict[str, Any] | None = None,
                        option_names: set[str] | None = None) -> tuple[Path, list[str]]:
    """Copy the player's yaml for this game into out_dir, with `name` forced to the slot name.

    A yaml file may hold several documents (one per game): keep the one for this game.
    Options left to chance in the yaml (`random`, weights) are replaced by the value the seed really
    got when the world puts it in slot_data under the option's name. Returns (path, options still random).
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
    still_random: list[str] = []
    section = doc.get(game)
    if isinstance(section, dict):
        section = dict(section)
        for option, value in section.items():
            if option == "progression_balancing" or not _is_random(value):
                continue
            real = (slot_data or {}).get(option)
            if option in (option_names or set()) and isinstance(real, (bool, int, str)):
                section[option] = real
            else:
                still_random.append(option)
        doc[game] = section
    out = out_dir / "player.yaml"
    out.write_text(yaml.safe_dump(doc, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return out, still_random


# Worlds that can regenerate from slot_data alone, but whose slot_data misses options that change the
# logic: when the player's yaml is configured, regenerate from it with slot_data applied on top.
YAML_PLUS_SLOT_DATA = {"Ori and the Will of the Wisps", "Satisfactory"}
# ... and among them, those whose slot_data alone gives a wrong logic (Satisfactory: building placements).
YAML_REQUIRED = {"Satisfactory"}


class SlotLogic:
    """One slot's regenerated world, kept between updates."""

    def __init__(self, slot_name: str, game: str, team: int, slot: int, slot_data: dict[str, Any],
                 yaml_path: Path | None, location_ids: set[int] | None = None,
                 room_checksum: str | None = None, start_items: list[int] | None = None) -> None:
        setup_ap()
        import worlds
        from worlds.AutoWorld import AutoWorldRegister
        from worlds.tracker.TrackerCore import TrackerCore

        self.slot_name, self.game, self.team, self.slot = slot_name, game, team, slot
        self.random_options: list[str] = []
        world_cls = AutoWorldRegister.world_types.get(game)
        if world_cls is None:
            raise LogicUnavailable(f"apworld non installé pour « {game} »")
        if getattr(world_cls, "disable_ut", False):
            raise LogicUnavailable("l'auteur de l'apworld a désactivé Universal Tracker pour ce jeu")
        local_checksum = worlds.network_data_package["games"].get(game, {}).get("checksum")
        if room_checksum is not None and room_checksum != local_checksum:  # D12 (None: caller does not check)
            raise LogicUnavailable("la room utilise une autre version de l'apworld que celle installée ici : "
                                   "logique désactivée pour ne pas se tromper" if room_checksum else
                                   "la room n'indique pas la version de ce jeu : logique désactivée")

        core = TrackerCore(logging.getLogger(f"ut.{slot_name}"), False, False)
        # TrackerCore caches multiworlds per slot_data at class level: keep the cache per slot.
        core.cached_multiworlds = []
        core.cached_slot_data = []
        core.set_slot_params(game, slot, slot_name, team)
        started = time.perf_counter()
        from .adapters import regeneration_patch
        start_names = [world_cls.item_id_to_name[code] for code in start_items or ()
                       if code in world_cls.item_id_to_name]
        with regeneration_patch(game, world_cls, slot_data, set(location_ids or ()), start_names):
            self._regenerate(core, world_cls, slot_name, game, slot_data, yaml_path)
        if core.multiworld is None or core.player_id is None:
            refused = adapter_refusal(core.gen_error or "")
            if refused:
                raise LogicUnavailable(refused)
            tail = (core.gen_error or "").strip().splitlines()[-1:] or ["raison inconnue"]
            raise RuntimeError(f"régénération du monde impossible : {tail[0][:300]}")
        self.core = core
        self.init_seconds = round(time.perf_counter() - started, 2)
        # Locations the server lists for the slot but the regenerated world does not have: the world was built
        # with other options than the room's (typically the yaml of another generation). Its logic misses them.
        own = {loc.address for loc in core.multiworld.get_locations(core.player_id) if isinstance(loc.address, int)}
        foreign = set(location_ids or ()) - own
        self.foreign_locations = len(foreign)
        if foreign:
            names = sorted(world_cls.location_id_to_name.get(i, str(i)) for i in foreign)
            log.warning("%s: %d locations of the slot are not in the regenerated world (mode %s): %s",
                        slot_name, len(foreign), self.mode, ", ".join(names[:10]) + (" ..." if len(names) > 10 else ""))

    def _regenerate(self, core, world_cls, slot_name: str, game: str, slot_data: dict[str, Any],
                    yaml_path: Path | None) -> None:
        if game in YAML_PLUS_SLOT_DATA and yaml_path is not None and Path(yaml_path).is_file() \
                and getattr(world_cls, "ut_can_gen_without_yaml", False):
            # UT's slot_data-only path writes an empty yaml (all defaults) then applies slot_data on top:
            # give it the player's yaml instead, for the options slot_data lacks.
            def write_player_yaml(game_name: str, player_name: str, tempdir: str) -> None:
                _, self.random_options = prepare_player_yaml(
                    Path(yaml_path), player_name, game_name, Path(tempdir), slot_data,
                    set(world_cls.options_dataclass.type_hints))
            core.write_empty_yaml = write_player_yaml
            core.initalize_tracker_core(world_cls, slot_data)
            self.mode = "yaml+slot_data"
            return
        if game in YAML_REQUIRED:
            raise LogicUnavailable("ce jeu a besoin du yaml du joueur (clé `yaml` du slot dans config/room.yaml)"
                                   if yaml_path is None else f"yaml introuvable : {yaml_path}")
        if getattr(world_cls, "ut_can_gen_without_yaml", False):
            core.initalize_tracker_core(world_cls, slot_data)
            self.mode = "slot_data"
        elif yaml_path is not None:
            if not Path(yaml_path).is_file():
                raise LogicUnavailable(f"yaml introuvable : {yaml_path}")
            with tempfile.TemporaryDirectory(prefix="mt-yaml-") as tmp:
                _, self.random_options = prepare_player_yaml(
                    Path(yaml_path), slot_name, game, Path(tmp), slot_data,
                    set(world_cls.options_dataclass.type_hints))
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
        unknown, errors, received = [], [], []
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
            received.append(item)
        if unknown:
            raise RuntimeError(f"datapackage incohérent avec l'apworld installé ({len(unknown)} items inconnus)")
        from .adapters import adjust_received
        adjust_received(world.game, world, received)
        for item in received:
            state.collect(item, True)
        state.sweep_for_advancements(locations=[loc for loc in mw.get_locations(pid) if not loc.address])
        reachable_locations = [loc for loc in mw.get_reachable_locations(state, pid)
                               if isinstance(loc.address, int) and loc.address in missing]
        reachable = sorted({loc.address for loc in reachable_locations})
        regions = {int(loc.address): plain_name(loc.parent_region.name) for loc in reachable_locations
                   if loc.parent_region is not None}
        return {"in_logic": reachable, "regions": regions, "errors": errors[:5]}


def plain_name(name: Any) -> str:
    """A region name as a plain str: some worlds use str enums (AEMinecraft's MCRegion), which the app
    process could not unpickle (it does not import `worlds`)."""
    from enum import Enum
    return str(name.value) if isinstance(name, Enum) else str(name)


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


def start_items(req: dict[str, Any]) -> list[int]:
    """The slot's start inventory (items received from location -2), for the adapters that need it."""
    from .adapters import needs_start_items
    if not needs_start_items(req["game"]):
        return []
    return sorted(int(net["item"]) for net in req.get("items", []) if int(net.get("location", 0)) == -2)


def request_key(req: dict[str, Any]) -> str:
    """What makes a regenerated world reusable: same slot, game, slot_data, yaml content (and start
    inventory for the games whose adapter replays it)."""
    yaml_digest = ""
    if req.get("yaml"):
        try:
            yaml_digest = hashlib.sha256(Path(req["yaml"]).read_bytes()).hexdigest()
        except OSError:
            yaml_digest = "missing"
    payload = json.dumps([req.get("seed_name"), req["game"], req["team"], req["slot"], req.get("slot_data"),
                          yaml_digest, req.get("checksum"), start_items(req)],
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
        if req.get("op") == "checksums":  # versions of the loaded worlds (imported apworlds, D27)
            setup_ap()
            import worlds
            packages = worlds.network_data_package["games"]
            return {"state": "ok", "checksums": {g: packages.get(g, {}).get("checksum") for g in req.get("games", [])}}
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
                    set(req.get("missing", [])) | set(req.get("checked", [])), req.get("checksum"),
                    start_items(req))
            except LogicUnavailable as exc:
                logic = LogicUnavailable(str(exc))  # no traceback: it would keep the half-built world alive
            except Exception as exc:
                log.warning("logic init failed for %s: %s", name, traceback.format_exc())
                logic = RuntimeError(f"{type(exc).__name__}: {exc}")
            had_previous = cached is not None
            self.slots[name] = (key, logic)
            if had_previous:
                del cached
                gc.collect()  # regenerated multiworlds are cyclic: free the replaced one now
        logic = self.slots[name][1]
        if isinstance(logic, LogicUnavailable):
            return {"state": "unavailable", "message": str(logic)}
        if isinstance(logic, Exception):
            return {"state": "error", "message": str(logic)[:400]}
        try:
            result = logic.in_logic(req.get("items", []), set(req.get("missing", [])))
        except Exception as exc:
            log.warning("logic update failed for %s: %s", name, traceback.format_exc())
            return {"state": "error", "message": f"{type(exc).__name__}: {exc}"[:400]}
        if logic.foreign_locations:
            result["errors"] = [f"{logic.foreign_locations} locations du slot manquent au monde recalculé : le yaml ne "
                                f"correspond sans doute pas à cette room, logique sous-estimée"] + result.get("errors", [])
        if logic.random_options:
            result["errors"] = [f"options aléatoires dans le yaml, logique peut-être approximative : "
                                f"{', '.join(logic.random_options[:5])}"] + result.get("errors", [])
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


