"""Per-game adapters for the single-player regeneration (worker process only).

Some worlds make random choices during generation that change the logic (entrance shuffle...)
and do not implement Universal Tracker's hooks (`interpret_slot_data` / `re_gen_passthrough`).
When the result of those choices is in `slot_data` — sent by the server to every client, so no
spoiler — an adapter replays it during the regeneration instead of rolling new random values.

An adapter may also use the slot's list of locations (checked + missing), which the server sends
on Connect. An adapter is a context manager factory, active only while that slot's world is
regenerated.
"""
from __future__ import annotations

import contextlib
import importlib
import logging
from typing import Any, Callable, ContextManager

log = logging.getLogger("multitracker.logic")


@contextlib.contextmanager
def _twwhd(world_cls: type, slot_data: dict[str, Any], location_ids: set[int]):
    with _twwhd_entrances(world_cls, slot_data), _twwhd_required_bosses(world_cls, location_ids):
        yield


@contextlib.contextmanager
def _twwhd_required_bosses(world_cls: type, location_ids: set[int]):
    """The Wind Waker HD, required bosses mode: the generator picks the required dungeons at random and
    does not create the locations of the other ("banned") dungeons. The slot's location list, which the
    server sends to every client (checked + missing), tells which dungeons are required: force them.
    """
    module = importlib.import_module(f"{world_cls.__module__}.randomizers.RequiredBosses")
    names = {world_cls.location_id_to_name[i] for i in location_ids if i in world_cls.location_id_to_name}
    zones = {module.split_location_name_by_zone(name)[0] for name in names
             if module.TWWHDFlag.DUNGEON in module.LOCATION_TABLE[name].flags}
    required = zones & set(module.DUNGEON_NAMES)  # the dungeons the generator chooses from
    randomizer = module.RequiredBossesRandomizer
    original = randomizer.randomize_required_bosses

    def randomize_required_bosses(self) -> None:
        options = self.world.options
        if not (required and len(required) == options.num_required_bosses.value):
            from .ut_worker import LogicUnavailable
            raise LogicUnavailable("TWWHD : impossible de déduire les donjons requis (options required bosses)")
        options.included_dungeons.value = set(required)  # nothing left to sample at random
        original(self)

    randomizer.randomize_required_bosses = randomize_required_bosses
    try:
        yield
    finally:
        randomizer.randomize_required_bosses = original


@contextlib.contextmanager
def _twwhd_entrances(world_cls: type, slot_data: dict[str, Any]):
    """The Wind Waker HD: apply slot_data["entrances"] (entrance name -> exit name) instead of shuffling."""
    mapping = slot_data.get("entrances")
    if not mapping:
        yield
        return
    module = importlib.import_module(f"{world_cls.__module__}.randomizers.Entrances")
    randomizer = module.EntranceRandomizer
    original = randomizer.randomize_entrances

    def randomize_entrances(self) -> None:
        done, done_reverse = dict(self.done_entrances_to_exits), dict(self.done_exits_to_entrances)
        for entrance_name, exit_name in mapping.items():
            zone_entrance = module.ZoneEntrance.all[entrance_name]
            zone_exit = module.ZoneExit.all[exit_name]
            done[zone_entrance] = zone_exit
            done_reverse[zone_exit] = zone_entrance
        self.done_entrances_to_exits, self.done_exits_to_entrances = done, done_reverse
        try:
            self.finalize_all_randomized_sets_of_entrances()
        except AssertionError as exc:
            # Debug-only consistency check (banned vs required boss islands) at the very end, after every
            # connection has been made; with the slot_data entrances it cannot fail for a real seed.
            log.warning("TWWHD entrance consistency check failed during regeneration: %s", exc)

    randomizer.randomize_entrances = randomize_entrances
    try:
        yield
    finally:
        randomizer.randomize_entrances = original


@contextlib.contextmanager
def _sm64ex(world_cls: type, slot_data: dict[str, Any], location_ids: set[int]):
    """Super Mario 64: replay slot_data["AreaRando"] ({entrance level: destination level}) instead of the
    painting / secret shuffle. The shuffles are replaced by a lookup of the final mapping and the
    "fix" swaps become no-ops (the final mapping already satisfies them)."""
    area = slot_data.get("AreaRando") or {}
    module = importlib.import_module(f"{world_cls.__module__}.Rules")
    regions = importlib.import_module(f"{world_cls.__module__}.Regions")
    level_to_name = {int(v): k for k, v in regions.sm64_entrances_to_level.items()}
    target = {int(k): level_to_name[int(v)] for k, v in area.items() if int(v) in level_to_name}
    if not target:
        yield
        return
    original_shuffle, original_fix = module.shuffle_dict_keys, module.fix_reg

    def shuffle_dict_keys(world, dictionary: dict) -> dict:
        if all(int(k) in target for k in dictionary) and \
                sorted(target[int(k)] for k in dictionary) == sorted(dictionary.values()):
            return {k: target[int(k)] for k in dictionary}
        return original_shuffle(world, dictionary)

    def fix_reg(entrance_map, entrance, invalid_regions, swapdict, world):
        swapdict.pop(entrance)

    module.shuffle_dict_keys, module.fix_reg = shuffle_dict_keys, fix_reg
    try:
        yield
    finally:
        module.shuffle_dict_keys, module.fix_reg = original_shuffle, original_fix


@contextlib.contextmanager
def _ori_wotw(world_cls: type, slot_data: dict[str, Any], location_ids: set[int]):
    """Ori and the Will of the Wisps (apworld bug, also affects Universal Tracker): its UT path sets
    `spawn_region_name` from slot_data["spawn_anchor"] but leaves `spawn_area` at the randomly rolled
    spawn, and keystone door costs depend on `spawn_area`. Keep both consistent while regenerating."""
    if "spawn_region_name" in vars(world_cls):
        yield  # the world changed its implementation: do nothing
        return

    def _get(self):
        return self.__dict__["spawn_region_name"]

    def _set(self, value):
        self.__dict__["spawn_region_name"] = value
        self.__dict__["spawn_area"] = str(value).split(".")[0]

    world_cls.spawn_region_name = property(_get, _set)
    try:
        yield
    finally:
        del world_cls.spawn_region_name  # instances keep their values in __dict__


ADAPTERS: dict[str, Callable[[type, dict[str, Any], set[int]], ContextManager]] = {
    "The Wind Waker HD": _twwhd,
    "Super Mario 64": _sm64ex,
    "Ori and the Will of the Wisps": _ori_wotw,
}


def regeneration_patch(game: str, world_cls: type, slot_data: dict[str, Any],
                       location_ids: set[int]) -> ContextManager:
    """location_ids: every location of the slot as known by the server (checked + missing)."""
    adapter = ADAPTERS.get(game)
    return adapter(world_cls, slot_data, location_ids) if adapter else contextlib.nullcontext()
