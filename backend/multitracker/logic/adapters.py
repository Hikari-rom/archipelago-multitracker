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
def patch_attr(owner: Any, name: str, value: Any):
    """Temporarily replace owner.name; restores exactly (deletes it if it was only inherited)."""
    own = name in vars(owner)
    original = vars(owner).get(name)
    setattr(owner, name, value)
    try:
        yield
    finally:
        if own:
            setattr(owner, name, original)
        else:
            delattr(owner, name)


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
        try:
            return self.__dict__["spawn_region_name"]
        except KeyError:
            raise AttributeError("spawn_region_name") from None

    def _set(self, value):
        self.__dict__["spawn_region_name"] = value
        self.__dict__["spawn_area"] = str(value).split(".")[0]

    world_cls.spawn_region_name = property(_get, _set)
    # With UT's passthrough the world already creates "Spawn item 1..10"; with a non-vanilla `spawn`
    # option (from the player's yaml) it would create them a second time and crash.
    original_create_regions = world_cls.create_regions

    def create_regions(self) -> None:
        if getattr(self.multiworld, "re_gen_passthrough", {}).get(self.game) is None:
            return original_create_regions(self)
        spawn = self.options.spawn.value
        self.options.spawn.value = type(self.options.spawn).option_vanilla
        try:
            original_create_regions(self)
        finally:
            self.options.spawn.value = spawn

    try:
        with patch_attr(world_cls, "create_regions", create_regions):
            yield
    finally:
        del world_cls.spawn_region_name  # instances keep their values in __dict__


def apply_options(world, slot_data: dict[str, Any], names: list[str]) -> None:
    """Set world options from slot_data entries named like the options (values the seed really used)."""
    for name in names:
        option = getattr(world.options, name, None)
        if option is not None and name in slot_data and slot_data[name] is not None:
            try:
                setattr(world.options, name, type(option).from_any(slot_data[name]))
            except Exception as exc:  # unknown format: keep the yaml/default value
                log.warning("%s: cannot apply option %s=%r from slot_data: %s", world.game, name, slot_data[name], exc)


@contextlib.contextmanager
def _mkwii(world_cls: type, slot_data: dict[str, Any], location_ids: set[int]):
    """Mario Kart Wii: its interpret_slot_data only runs after the regions/rules were built from freshly
    rolled starting cups/characters/vehicles, and the slot_data options are never re-applied. Apply both
    during generate_early instead."""
    if "starting_cups" not in slot_data:
        yield
        return
    original = world_cls.generate_early

    def generate_early(self) -> None:
        apply_options(self, slot_data, ["enabled_ccs", "enabled_cup_check_tiers", "include_race_checks",
                                        "lock_default_characters", "lock_default_vehicles",
                                        "enable_item_randomization", "enable_traps", "starting_items",
                                        "cups_required_for_goal", "goal_difficulty", "goal_cc"])
        original(self)
        self.starting_cups = dict(slot_data["starting_cups"])
        self.starting_characters = list(slot_data.get("starting_characters") or [])
        self.starting_kart = slot_data.get("starting_kart")
        self.starting_bike = slot_data.get("starting_bike")

    with patch_attr(world_cls, "generate_early", generate_early):
        yield


@contextlib.contextmanager
def _subnautica(world_cls: type, slot_data: dict[str, Any], location_ids: set[int]):
    """Subnautica: the creatures to scan are a random sample drawn in generate_early, sent in slot_data but
    never read back (no interpret_slot_data). Replay them, and the options slot_data carries."""
    if not isinstance(slot_data.get("creatures_to_scan"), list):
        yield
        return
    original = world_cls.generate_early

    def generate_early(self) -> None:
        apply_options(self, slot_data, ["goal", "swim_rule", "free_samples", "empty_tanks"])
        original(self)
        self.creatures_to_scan = [str(c) for c in slot_data["creatures_to_scan"]]
        self.options.creature_scans.value = len(self.creatures_to_scan)

    with patch_attr(world_cls, "generate_early", generate_early):
        yield


@contextlib.contextmanager
def _v6(world_cls: type, slot_data: dict[str, Any], location_ids: set[int]):
    """VVVVVV: set_rules shuffles the area connections then the area costs with multiworld.random (each only if
    its option is on), and slot_data["AreaRando"/"AreaCostRando"] holds the result, never read back. Replay both
    permutations: shuffle() returns them in that order (the options are forced on so both calls happen)."""
    try:
        conn = {int(k): int(v) for k, v in slot_data["AreaRando"].items()}
        cost = {int(k): int(v) for k, v in slot_data["AreaCostRando"].items()}
    except (KeyError, AttributeError, TypeError, ValueError):
        yield
        return
    original = world_cls.set_rules
    n = len(conn) - 1  # key 0 is the menu

    class _Replay:
        def __init__(self, real) -> None:
            self.real, self.orders = real, [[conn[i + 1] - 1 for i in range(n)], [cost[i + 1] - 1 for i in range(n)]]

        def shuffle(self, items: list) -> None:
            items[:] = self.orders.pop(0)

        def __getattr__(self, name: str):
            return getattr(self.real, name)

    def set_rules(self) -> None:
        apply_options(self, {"door_cost": slot_data.get("DoorCost")}, ["door_cost"])
        options = self.options
        saved = (options.area_rando.value, options.area_cost.value, self.multiworld.random)
        options.area_rando.value = options.area_cost.value = 1
        self.multiworld.random = _Replay(saved[2])
        try:
            original(self)
        finally:
            options.area_rando.value, options.area_cost.value, self.multiworld.random = saved

    with patch_attr(world_cls, "set_rules", set_rules):
        yield


ADAPTERS: dict[str, Callable[[type, dict[str, Any], set[int]], ContextManager]] = {
    "The Wind Waker HD": _twwhd,
    "Super Mario 64": _sm64ex,
    "Ori and the Will of the Wisps": _ori_wotw,
    "Mario Kart Wii": _mkwii,
    "Subnautica": _subnautica,
    "VVVVVV": _v6,
}


from .adapters_m7 import ADAPTERS_M7  # noqa: E402

ADAPTERS.update(ADAPTERS_M7)


def regeneration_patch(game: str, world_cls: type, slot_data: dict[str, Any],
                       location_ids: set[int]) -> ContextManager:
    """location_ids: every location of the slot as known by the server (checked + missing)."""
    adapter = ADAPTERS.get(game)
    return adapter(world_cls, slot_data, location_ids) if adapter else contextlib.nullcontext()
