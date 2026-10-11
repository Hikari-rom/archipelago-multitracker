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
        log.warning("Subnautica: no creatures_to_scan in slot_data, creature scans may be wrong")
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
        log.warning("VVVVVV: no readable AreaRando/AreaCostRando in slot_data, areas may be wrong")
        yield
        return
    original_early, original = world_cls.generate_early, world_cls.set_rules
    n = len(conn) - 1  # key 0 is the menu

    class _Replay:
        def __init__(self, real) -> None:
            self.real, self.orders = real, [[conn[i + 1] - 1 for i in range(n)], [cost[i + 1] - 1 for i in range(n)]]

        def shuffle(self, items: list) -> None:
            items[:] = self.orders.pop(0)

        def __getattr__(self, name: str):
            return getattr(self.real, name)

    def generate_early(self) -> None:
        apply_options(self, {"door_cost": slot_data.get("DoorCost")}, ["door_cost"])  # before create_items
        original_early(self)

    def set_rules(self) -> None:
        options = self.options
        saved = (options.area_rando.value, options.area_cost.value, self.multiworld.random)
        options.area_rando.value = options.area_cost.value = 1
        self.multiworld.random = _Replay(saved[2])
        try:
            original(self)
        finally:
            options.area_rando.value, options.area_cost.value, self.multiworld.random = saved

    with patch_attr(world_cls, "generate_early", generate_early), patch_attr(world_cls, "set_rules", set_rules):
        yield


@contextlib.contextmanager
def _overcooked2(world_cls: type, slot_data: dict[str, Any], location_ids: set[int]):
    """Overcooked! 2: with shuffle_level_order, generate_early assigns a random kitchen to each overworld level
    (level_mapping, which sets the star requirements); slot_data["CustomLevelOrder"]["Story"] holds the result
    but is never read back. Rebuild the mapping from it."""
    try:
        story = slot_data["CustomLevelOrder"]["Story"]
        order = {int(k): (str(v["DLC"]), int(v["LevelID"])) for k, v in story.items()}
    except (KeyError, AttributeError, TypeError, ValueError):
        log.warning("Overcooked! 2: no readable CustomLevelOrder in slot_data, kitchens may be wrong")
        order = {}
    if not order:  # level order not shuffled (or unreadable)
        yield
        return
    levels = importlib.import_module(f"{world_cls.__module__}.Overcooked2Levels")
    original = world_cls.generate_early

    def generate_early(self) -> None:
        original(self)
        self.level_mapping = {level_id: levels.Overcooked2GenericLevel(number, levels.Overcooked2Dlc(dlc))
                              for level_id, (dlc, number) in order.items()}

    with patch_attr(world_cls, "generate_early", generate_early):
        yield


@contextlib.contextmanager
def _hollow_knight(world_cls: type, slot_data: dict[str, Any], location_ids: set[int]):
    """Hollow Knight: charm notch costs (generate_early) and, with CostSanity, shop/location costs (create_items)
    are drawn at random; slot_data["notch_costs"] / ["location_costs"] hold them but are never read back."""
    notch_costs = slot_data.get("notch_costs")
    location_costs = slot_data.get("location_costs")
    if not isinstance(notch_costs, list) or not isinstance(location_costs, dict):
        log.warning("Hollow Knight: no notch_costs/location_costs in slot_data, costs may be wrong")
        yield
        return
    original_early, original_items = world_cls.generate_early, world_cls.create_items

    def generate_early(self) -> None:
        original_early(self)
        self.charm_costs = [int(c) for c in notch_costs]

    def create_items(self) -> None:
        original_items(self)
        for region in self.multiworld.get_regions(self.player):
            for location in region.locations:
                costs = location_costs.get(location.name)
                if isinstance(costs, dict) and getattr(location, "costs", None) is not None:
                    location.costs = {str(term): int(value) for term, value in costs.items()}
                    location.sort_costs()

    with patch_attr(world_cls, "generate_early", generate_early), \
            patch_attr(world_cls, "create_items", create_items):
        yield


ADAPTERS: dict[str, Callable[[type, dict[str, Any], set[int]], ContextManager]] = {
    "The Wind Waker HD": _twwhd,
    "Super Mario 64": _sm64ex,
    "Ori and the Will of the Wisps": _ori_wotw,
    "Mario Kart Wii": _mkwii,
    "Subnautica": _subnautica,
    "VVVVVV": _v6,
    "Overcooked! 2": _overcooked2,
    "Hollow Knight": _hollow_knight,
}


@contextlib.contextmanager
def _lethal_company(world_cls: type, slot_data: dict[str, Any], location_ids: set[int],
                    start_items: list[str]):
    """Lethal Company: with the "randomize" starting moon, the moon is drawn in generate_early and only
    given to the player as start inventory; with modify_scrap_spawns, the scrap -> moons map is a random
    shuffle sent in slot_data (`moon_to_scrap_map`). Replay both."""
    regions = importlib.import_module(f"{world_cls.__module__}.regions")
    moons = set(world_cls.item_name_groups.get("Moons", ()))
    start_moons = [name for name in start_items if name in moons]
    scrap_map = slot_data.get("moon_to_scrap_map")
    if len(start_moons) != 1:
        log.warning("Lethal Company: starting moon not found in the start inventory (%s)", start_moons)
    original_early = world_cls.generate_early
    original_alt = regions.generate_scrap_moons_alt

    def generate_early(self) -> None:
        if len(start_moons) != 1:
            original_early(self)
            return
        self.options.starting_moon.value = start_moons[0]
        # A single-player generation re-rolls some starting moons: the regeneration is always single-player,
        # the moon it must keep is already known.
        players = self.multiworld.players
        self.multiworld.players = max(players, 2)
        try:
            original_early(self)
        finally:
            self.multiworld.players = players
        if self.initial_world != start_moons[0]:
            from .ut_worker import LogicUnavailable
            raise LogicUnavailable(f"Lethal Company : lune de départ {start_moons[0]} non rejouée")

    def generate_scrap_moons_alt(world):
        if not isinstance(scrap_map, dict):
            log.warning("Lethal Company: no moon_to_scrap_map in slot_data, scrap locations may be wrong")
            return original_alt(world)
        world.scrap_map = {scrap: list(moons) for scrap, moons in scrap_map.items()}
        return world.scrap_map

    with patch_attr(world_cls, "generate_early", generate_early), \
            patch_attr(regions, "generate_scrap_moons_alt", generate_scrap_moons_alt):
        yield


START_ADAPTERS: dict[str, Callable[[type, dict[str, Any], set[int], list[str]], ContextManager]] = {
    "Lethal Company": _lethal_company,
}


def _stardew_received(world: Any, items: list) -> None:
    """Stardew Valley counts "received progression items" (months lived, progression percent) only for the
    items that were progression *before* the fill: the last Progressive Trash Can is created useful and
    turned into progression after the fill. A received item is rebuilt from its name, so give each
    received progression copy the count of a generated copy of that name that is progression after the
    fill (regenerated item pool), lowest first when they differ: the logic never runs ahead. Other copies
    (filler, useful) count nothing anyway; copies beyond the pool (start inventory, which the regeneration
    does not keep) keep the world's default.
    """
    try:
        event = importlib.import_module(f"{type(world).__module__}.strings.ap_names.event_names") \
            .Event.received_progression_item
    except (ImportError, AttributeError):
        log.warning("Stardew Valley: event names not found, received progression items left as created")
        return
    # Computed once per regenerated world: its item pool does not change afterwards.
    counts = getattr(world, "_mt_prefill_progress", None)
    if counts is None:
        from BaseClasses import ItemClassification
        post_fill = {id(item): classification for item, classification
                     in getattr(world, "classifications_to_override_post_fill", ())}
        counts = {}
        for item in world.multiworld.itempool:
            final = post_fill.get(id(item), item.classification)
            if item.player == world.player and item.code is not None and final & ItemClassification.progression:
                counts.setdefault(item.name, []).append(item.events_to_collect.get(event, 0))
        for values in counts.values():
            values.sort()
        world._mt_prefill_progress = counts
    seen: dict[str, int] = {}
    for item in items:
        if not item.advancement:
            continue
        index = seen[item.name] = seen.get(item.name, -1) + 1
        values = counts.get(item.name, ())
        if index >= len(values):
            continue
        if values[index]:
            item.events_to_collect[event] = values[index]
        else:
            item.events_to_collect.pop(event, None)


RECEIVED_HOOKS: dict[str, Callable[[Any, list], None]] = {
    "Stardew Valley": _stardew_received,
}


def adjust_received(game: str, world: Any, items: list) -> None:
    """Per-game fix of the received items (rebuilt from their names) before they are collected."""
    hook = RECEIVED_HOOKS.get(game)
    if hook:
        hook(world, items)


from .adapters_m7 import ADAPTERS_M7  # noqa: E402

ADAPTERS.update(ADAPTERS_M7)


def needs_start_items(game: str) -> bool:
    return game in START_ADAPTERS


def regeneration_patch(game: str, world_cls: type, slot_data: dict[str, Any],
                       location_ids: set[int], start_items: list[str] = ()) -> ContextManager:
    """location_ids: every location of the slot as known by the server (checked + missing);
    start_items: names of the items received from the start inventory (location -2)."""
    if game in START_ADAPTERS:
        return START_ADAPTERS[game](world_cls, slot_data, location_ids, list(start_items))
    adapter = ADAPTERS.get(game)
    return adapter(world_cls, slot_data, location_ids) if adapter else contextlib.nullcontext()
