"""Regeneration adapters for the games of the 2026-10 room (M24, same contract as adapters.py)."""
from __future__ import annotations

import contextlib
import dataclasses
import importlib
import logging
from typing import Any, Callable, ContextManager

from .adapters import patch_attr

log = logging.getLogger("multitracker.logic")


@contextlib.contextmanager
def _archipelacode(world_cls: type, slot_data: dict[str, Any], location_ids: set[int]):
    """ArchipelaCode: generate_early draws the problems (the locations) at random; slot_data["regions"] holds them,
    batch by batch in order, never read back. Replay them (the batches are consecutive slices of that list, so the
    regions come out the same). Also give each world its own included_languages: it is a class attribute every
    generation appends to, so a second regeneration in the worker would see the languages of the first."""
    try:
        regions = slot_data["regions"]
        batches = [[int(i) for i in regions[k]] for k in sorted(regions, key=int)]
    except (KeyError, AttributeError, TypeError, ValueError):
        log.warning("ArchipelaCode: no readable regions in slot_data, the problems may be wrong")
        batches = None
    locations_mod = importlib.import_module(f"{world_cls.__module__}.Locations")
    types_mod = importlib.import_module(f"{world_cls.__module__}.Types")
    original_early, original_pick = world_cls.generate_early, world_cls.generate_included_locations_v2

    def generate_early(self) -> None:
        self.included_languages, self.precollected_items = [], []
        original_early(self)

    def generate_included_locations_v2(self) -> None:
        if batches is None:
            original_pick(self)
            return
        table = {int(d.id): d for d in locations_mod.get_location_table().values()}
        slugs = {s for lang in self.included_languages for s in lang.langSlugs}
        self.included_locations = [
            types_mod.LocData(d.id, d.name, d.title_slug, d.difficulty, [s for s in d.lang_slugs if s in slugs],
                              d.required_features)
            for d in (table[i] for batch in batches for i in batch)]

    with patch_attr(world_cls, "generate_early", generate_early), \
            patch_attr(world_cls, "generate_included_locations_v2", generate_included_locations_v2):
        yield


@contextlib.contextmanager
def _peak(world_cls: type, slot_data: dict[str, Any], location_ids: set[int]):
    """PEAK: with loot_sanity, set_rules shuffles the biome of every "Acquire …" location with world.random;
    slot_data["loot_biome_assignments"] holds the result, never read back. Replay it."""
    assignments = slot_data.get("loot_biome_assignments")
    if not isinstance(assignments, dict):
        log.warning("PEAK: no loot_biome_assignments in slot_data, Acquire locations may be wrong")
        yield
        return
    rules_mod = importlib.import_module(f"{world_cls.__module__}.Rules")
    original = rules_mod.generate_loot_biome_assignments

    def generate_loot_biome_assignments(acquire_locations, random_source, loot_sanity_mode):
        result = original(acquire_locations, random_source, loot_sanity_mode)
        result.update({name: int(level) for name, level in assignments.items() if name in result})
        return result

    with patch_attr(rules_mod, "generate_loot_biome_assignments", generate_loot_biome_assignments):
        yield


@contextlib.contextmanager
def _trackmania(world_cls: type, slot_data: dict[str, Any], location_ids: set[int]):
    """Trackmania: generate_early draws the map count of every series (the locations and the medal requirements);
    slot_data["SeriesData"] holds the result. Replay it."""
    series = slot_data.get("SeriesData")
    if not isinstance(series, list):
        log.warning("Trackmania: no SeriesData in slot_data, the series may be wrong")
        yield
        return
    original = world_cls.generate_early

    def generate_early(self) -> None:
        original(self)
        self.series_data = [dict(s) for s in series]

    with patch_attr(world_cls, "generate_early", generate_early):
        yield


@contextlib.contextmanager
def _slime_rancher_2(world_cls: type, slot_data: dict[str, Any], location_ids: set[int]):
    """Slime Rancher 2: generate_early draws the Polestar Provisions shop checks (a random subset, split into catalog
    waves) and the plort goal amount. The slot's locations give the subset, slot_data the waves and the amount."""
    locations_mod = importlib.import_module(f"{world_cls.__module__}.locations")
    original = world_cls.generate_early

    def generate_early(self) -> None:
        original(self)
        if self._shop_check_locations:
            self._shop_check_locations = [loc for loc in locations_mod.POLESTAR_SHOP_LOCATIONS
                                          if loc.code in location_ids]
            by_id = {str(loc.code): loc.name for loc in self._shop_check_locations}
            waves = slot_data.get("shop_catalog_waves") or {}
            self._shop_catalog_waves = {by_id[k]: int(w) for k, w in waves.items() if k in by_id}
            self._shop_catalog_items = int(slot_data.get("shop_catalog_items", 0)) if self._shop_catalog_waves else 0
        if "plort_goal_amount" in slot_data:
            self._plort_goal_amount = int(slot_data["plort_goal_amount"])

    with patch_attr(world_cls, "generate_early", generate_early):
        yield


@contextlib.contextmanager
def _deep_rock_galactic(world_cls: type, slot_data: dict[str, Any], location_ids: set[int]):
    """Deep Rock Galactic: create_regions removes a number of locations drawn with the global random (traps off,
    classes…). Remove only the ones the options remove for sure, then keep the slot's locations."""
    regions_mod = importlib.import_module(f"{world_cls.__module__}.regions")
    original = regions_mod.remove_locations

    def remove_locations(all_locations, location_difference, *args, **kwargs):
        kept = original(all_locations, 0, *args, **kwargs)
        return {name: code for name, code in kept.items() if code in location_ids}

    with patch_attr(regions_mod, "remove_locations", remove_locations):
        yield


@contextlib.contextmanager
def _tfwr(world_cls: type, slot_data: dict[str, Any], location_ids: set[int]):
    """The Farmer Was Replaced: __init__ draws the cost of every crop (and writes it into the shared crop table);
    slot_data["crops.<name>"] holds them. Use those, on copies of the table."""
    crops_mod = importlib.import_module(f"{world_cls.__module__.rsplit('.', 1)[0]}.Data.Crops")
    if not any(key.startswith("crops.") for key in slot_data):
        log.warning("The Farmer Was Replaced: no crop costs in slot_data, the costs may be wrong")
        yield
        return

    def randomize_crop_cost(self) -> list:
        return [dataclasses.replace(crop, cost=list(slot_data.get(f"crops.{crop.name}", crop.cost)))
                for crop in crops_mod.ALL_CROPS]

    with patch_attr(world_cls, "randomize_crop_cost", randomize_crop_cost):
        yield


@contextlib.contextmanager
def _dont_starve_together(world_cls: type, slot_data: dict[str, Any], location_ids: set[int]):
    """Don't Starve Together: with a "Random" boss goal, generate_early draws the required boss (which also decides
    the cave and ocean regions); slot_data["goal_locations"] holds it. Give it to the options before the draw.
    create_regions also draws which research locations exist (shuffled lists of names, popped from the end): order
    those lists so that the slot's locations come out first."""
    name_to_id = world_cls.location_name_to_id
    names = {code: name for name, code in name_to_id.items()}
    bosses = {names[code] for code in slot_data.get("goal_locations") or [] if code in names}
    original_early, original_regions = world_cls.generate_early, world_cls.create_regions

    def generate_early(self) -> None:
        if bosses:
            self.options.required_bosses.value = set(bosses)
        original_early(self)

    def create_regions(self) -> None:
        shuffle = self.random.shuffle

        def slot_last(seq) -> None:
            if seq and all(isinstance(name, str) and name in name_to_id for name in seq):
                seq.sort(key=lambda name: (name_to_id[name] in location_ids, name))
            else:
                shuffle(seq)

        self.random.shuffle = slot_last
        try:
            original_regions(self)
        finally:
            del self.random.shuffle

    with patch_attr(world_cls, "generate_early", generate_early), \
            patch_attr(world_cls, "create_regions", create_regions):
        yield


@contextlib.contextmanager
def _cuphead(world_cls: type, slot_data: dict[str, Any], location_ids: set[int]):
    """Cuphead: its regeneration (re_gen_setup) takes the options from slot_data, which lacks
    dlc_kingdice_chalice_checks (the King Dice mini-boss checks as Ms. Chalice). The slot's locations tell whether
    it is on (its two "on" values only differ in game)."""
    defs = importlib.import_module(f"{world_cls.__module__}.world.locations.locationdefs")
    chaliced = {world_cls.location_name_to_id[name] for name in defs.location_level_dicepalace_dlc_chaliced
                if name in world_cls.location_name_to_id}
    original = world_cls.re_gen_setup

    def re_gen_setup(self) -> None:
        original(self)
        if chaliced & location_ids and not self.options.dlc_kingdice_chalice_checks.value:
            self.options.dlc_kingdice_chalice_checks.value = self.options.dlc_kingdice_chalice_checks.option_enabled

    with patch_attr(world_cls, "re_gen_setup", re_gen_setup):
        yield


@contextlib.contextmanager
def _tloz_st(world_cls: type, slot_data: dict[str, Any], location_ids: set[int]):
    """Spirit Tracks, like Phantom Hourglass: Universal Tracker leaves the shuffled entrances and the "UT events"
    (stamp stations, passengers, bosses...) disconnected until the game client reports them in the data storage.
    The world reconnects all of them (pairings in slot_data["er_pairings"], no spoiler) when
    `multiworld.enforce_deferred_connections == "off"`, which gives the generator's own logic.
    The regeneration also keeps the default section count (slot_data["section_count"] is never read back), and
    slot_data lacks tear_size: a slot only has tears of one size, so let the tear rules accept both sizes.
    Last, fill_slot_data rewrites two Lost at Sea pairings for the game client (redirect_boss_warps): the dungeon's
    one-way loop entrance (never shuffled) and the exit that leads into the loop. Put back what the generation had."""
    from rule_builder.options import OptionFilter

    entrances = importlib.import_module(f"{world_cls.__module__}.data.Entrances").ENTRANCES
    las_entrance, las_exit, las_loop, las_spawn = (entrances[name].id for name in (
        "Lost at Sea Lobby Enter Dungeon", "Lost at Sea Dungeon Reward Room Warp",
        "Lost at Sea Lobby Enter Dungeon One-Way", "Lost at Sea Dungeon Plain Phantom Spawn"))
    tear_size = world_cls.options_dataclass.type_hints["tear_size"]
    original_early, original_check = world_cls.generate_early, OptionFilter.check

    def generate_early(self) -> None:
        self.multiworld.enforce_deferred_connections = "off"
        original_early(self)
        pairings = {int(k): int(v) for k, v in self.ut_pairings.items()}
        if las_entrance in pairings:
            pairings.pop(las_loop, None)
            into_loop = pairings.get(las_exit)
            # With coupled entrances the exit into the loop was paired back with the loop's warp.
            if pairings.get(into_loop) == las_spawn and not self.options.decouple_shuffled_entrances:
                pairings[into_loop] = las_exit
            self.ut_pairings = pairings
        if "section_count" in slot_data:
            count = min(int(slot_data["section_count"]), 5)
            self.sections_included = int(slot_data["section_count"])
            self.tears_included_small, self.tears_included_big = count * 3 + 1, count + 1

    def check(self, options) -> bool:
        return self.option is tear_size or original_check(self, options)

    with patch_attr(world_cls, "generate_early", generate_early), patch_attr(OptionFilter, "check", check):
        yield


@contextlib.contextmanager
def _mm_recomp(world_cls: type, slot_data: dict[str, Any], location_ids: set[int]):
    """Majora's Mask Recompiled: with shop prices other than vanilla, generate_early draws every shop price (the
    rules check the wallet against them); slot_data["shop_prices_ints"] holds them. Replay them."""
    prices = slot_data.get("shop_prices_ints")
    if not isinstance(prices, list):
        yield
        return
    original = world_cls.generate_early

    def generate_early(self) -> None:
        original(self)
        if self.prices_ints:
            self.prices_ints = [int(price) for price in prices]
            self.prices = " ".join(str(price) for price in self.prices_ints)

    with patch_attr(world_cls, "generate_early", generate_early):
        yield


@contextlib.contextmanager
def _wikipelago(world_cls: type, slot_data: dict[str, Any], location_ids: set[int]):
    """Wikipelago: generate_early draws the main round each branch forks from (its entrance needs that round's
    Round Access); slot_data["crossroads"] holds them. Replay them."""
    crossroads = slot_data.get("crossroads")
    if not isinstance(crossroads, list):
        yield
        return
    original = world_cls.generate_early

    def generate_early(self) -> None:
        original(self)
        self.crossroads = [{"main_round": int(cr["main_round"]), "branch_id": int(cr["branch_id"])}
                           for cr in crossroads]

    with patch_attr(world_cls, "generate_early", generate_early):
        yield


def _dont_starve_together_received(world: Any, items: list, start: list) -> None:
    """Don't Starve Together: World.create_item makes every item progression, but the items that do not fit in the
    locations go to the start inventory with their pool classification (often useful), which the real generation's
    logic never counts. Give those their pool classification back; the start_inventory of the options was created by
    create_item (progression) and stays so."""
    pool = getattr(world, "dst_itempool", None)
    if pool is None or not start:
        return
    from_options: dict[str, int] = {}
    for option in ("start_inventory", "start_inventory_from_pool"):
        for name, count in getattr(getattr(world.options, option, None), "value", {}).items():
            from_options[name] = from_options.get(name, 0) + int(count)
    for item in start:
        if from_options.get(item.name, 0) > 0:
            from_options[item.name] -= 1
        else:
            item.classification = pool.create_item(world, item.name).classification


RECEIVED_HOOKS_M24: dict[str, Callable[[Any, list, list], None]] = {
    "Don't Starve Together": _dont_starve_together_received,
}


ADAPTERS_M24: dict[str, Callable[[type, dict[str, Any], set[int]], ContextManager]] = {
    "ArchipelaCode": _archipelacode,
    "Cuphead": _cuphead,
    "Don't Starve Together": _dont_starve_together,
    "The Farmer Was Replaced": _tfwr,
    "Deep Rock Galactic": _deep_rock_galactic,
    "Majora's Mask Recompiled": _mm_recomp,
    "PEAK": _peak,
    "Slime Rancher 2": _slime_rancher_2,
    "Spirit Tracks": _tloz_st,
    "Trackmania": _trackmania,
    "Wikipelago": _wikipelago,
}
