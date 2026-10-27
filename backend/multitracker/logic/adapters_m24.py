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


@contextlib.contextmanager
def _tunic(world_cls: type, slot_data: dict[str, Any], location_ids: set[int]):
    """TUNIC, like Phantom Hourglass: with entrance rando, Universal Tracker disconnects every shuffled entrance
    until the game client reports it in the data storage (connect_entrances). The pairings come from slot_data (no
    spoiler) and stay connected when `multiworld.enforce_deferred_connections == "off"`: the generator's logic."""
    original = world_cls.generate_early

    def generate_early(self) -> None:
        self.multiworld.enforce_deferred_connections = "off"
        original(self)

    with patch_attr(world_cls, "generate_early", generate_early):
        yield


@contextlib.contextmanager
def _pokemon_emerald(world_cls: type, slot_data: dict[str, Any], location_ids: set[int]):
    """Pokemon Emerald: with wild Pokemon randomized, create_regions draws which species lives where; each wild slot
    carries a CATCH_<species> event. Neither slot_data nor the server tell where a species is, so "Pokedex - X"
    (needs CATCH_X) and the Regi seal (needs CATCH Wailord and Relicanth) cannot be known: never count them in logic
    (late, never early). Every other rule is exact."""
    original = world_cls.set_rules

    def set_rules(self) -> None:
        original(self)
        if self.options.wild_pokemon.value == self.options.wild_pokemon.option_vanilla:
            return
        for location in self.multiworld.get_locations(self.player):
            if location.name.startswith("Pokedex - ") or location.name == "EVENT_UNDO_REGI_SEAL":
                location.access_rule = lambda state: False

    with patch_attr(world_cls, "set_rules", set_rules):
        yield


class _SlotSample:
    """Stands for a world's random generator: `sample` returns the slot's own locations out of the population,
    everything else draws as usual. A second sample of the same population (the world rejected the first one and
    draws again) is a real draw: the world then misses some of the slot's locations, which the worker reports."""

    def __init__(self, random: Any, names: set[str]) -> None:
        self._random = random
        self._names = names
        self._drawn: list[list] = []

    def sample(self, population: list, k: int) -> list:
        if any(population is drawn for drawn in self._drawn):
            return self._random.sample(population, k)
        self._drawn.append(population)
        return [name for name in population if name in self._names]

    def __getattr__(self, name: str) -> Any:
        return getattr(self._random, name)


@contextlib.contextmanager
def _factorio(world_cls: type, slot_data: dict[str, Any], location_ids: set[int]):
    """Factorio has no slot_data and draws at generation what its rules depend on: which "AP-<pack>-<cost>" research
    and "Craft <item>" locations exist (the slot's location list says), the lower science packs mixed into each
    research (tech_cost_mix), the prerequisites between researches (tech_tree_layout) and, depending on the options,
    the recipes of the science packs, the silo, the satellite and always the rocket part. Only the game's mod knows
    them. Use rules that are always sufficient, never early, sometimes late:
    - a research of pack N needs every pack up to N automated (its prerequisites are researches of packs <= N);
    - a randomized recipe counts as made of every item it could have been drawn from, in any of its possible
      crafting machines;
    - a pack is also automated once a research of that pack is checked (`_factorio_state`): every "AP-N-..."
      research needs pack N whatever the draw, so the player already makes it, and technologies are never lost.
    Exact when nothing is randomized (single layout, tech_cost_mix 0 or 100, recipes as in the game)."""
    module = importlib.import_module(world_cls.__module__)
    technologies = importlib.import_module(f"{world_cls.__module__}.Technologies")
    names = {world_cls.location_id_to_name[i] for i in location_ids if i in world_cls.location_id_to_name}
    original_regions, original_recipes, original_rules = \
        world_cls.create_regions, world_cls.set_custom_recipes, world_cls.set_rules

    def create_regions(self) -> None:
        if not names:
            return original_regions(self)
        self.random, random = _SlotSample(self.random, names), self.random
        try:
            original_regions(self)
        finally:
            self.random = random

    def every_ingredient(name: str, pool: set[str], machines: bool = False) -> Any:
        original = technologies.recipes[name]
        ingredients = dict.fromkeys(sorted(pool & technologies.valid_ingredients), 1)
        if machines:  # a pack recipe with 1 or 2 fluids moves to another crafting category (make_quick_recipe)
            fluids = len(pool & technologies.fluids)
            categories = {original.category} | ({"crafting-with-fluid"} if fluids else set()) | \
                ({"chemistry"} if fluids > 1 else set())
            ingredients |= dict.fromkeys(sorted(technologies.machine_per_category[c] for c in categories), 1)
        return technologies.Recipe(name, original.category, ingredients, original.products, original.energy)

    def set_custom_recipes(self) -> None:
        original_recipes(self)
        options, pools = self.options, technologies.get_science_pack_pools()
        self.custom_recipes["rocket-part"] = every_ingredient("rocket-part", pools[options.max_science_pack.get_max_pack()])
        if options.recipe_ingredients:
            pool: set[str] = set()
            for pack in options.max_science_pack.get_ordered_science_packs():
                pool |= pools[pack]
                if pack in technologies.recipes:
                    self.custom_recipes[pack] = every_ingredient(pack, pool, machines=True)
        allowed = set().union(*(pools[pack] for pack in options.max_science_pack.get_allowed_packs()))
        if options.silo.value == options.silo.option_randomize_recipe:
            self.custom_recipes["rocket-silo"] = every_ingredient("rocket-silo", allowed)
        if options.satellite.value == options.satellite.option_randomize_recipe:
            self.custom_recipes["satellite"] = every_ingredient("satellite", allowed)
        # The original computed the progression technologies from the drawn recipes: from these ones instead.
        for recipe in self.custom_recipes.values():
            self.advancement_technologies |= {tech.name for tech in recipe.recursive_unlocking_technologies}
        self.advancement_technologies |= {technologies.tech_to_progressive_lookup[tech]
                                          for tech in self.advancement_technologies
                                          if tech in technologies.tech_to_progressive_lookup}

    def set_rules(self) -> None:
        original_rules(self)
        if _factorio_exact_researches(self):
            return
        packs = module.Factorio.ordered_science_packs
        for location in self.science_locations:
            needed = frozenset(f"Automated {pack}" for pack in packs[:location.complexity + 1])
            location.access_rule = lambda state, needed=needed: state.has_all(needed, self.player)

    with patch_attr(world_cls, "create_regions", create_regions), \
            patch_attr(world_cls, "set_custom_recipes", set_custom_recipes), \
            patch_attr(world_cls, "set_rules", set_rules):
        yield


def _factorio_exact_researches(world: Any) -> bool:
    """No prerequisites between researches, and each research's packs do not depend on the draw."""
    options = world.options
    return options.tech_tree_layout.value == options.tech_tree_layout.option_single \
        and options.tech_cost_mix.value in (0, 100)


def _factorio_note(world: Any) -> str | None:
    options = world.options
    rocket = {"Craft rocket-part"} | ({"Craft rocket-silo"} if options.silo.value == options.silo.option_randomize_recipe
                                     else set()) | \
        ({"Craft satellite"} if options.satellite.value == options.satellite.option_randomize_recipe else set())
    if _factorio_exact_researches(world) and not options.recipe_ingredients \
            and not rocket & {loc.name for loc in world.craftsanity_locations}:
        return None
    return ("Logique minorée : le serveur ne transmet ni l'arbre des technologies ni les recettes tirées au hasard. "
            "Ce qui est affiché en logique l'est vraiment, mais certains checks n'y apparaissent que plus tard "
            "(un pack de science compte dès qu'une recherche qui l'utilise a été faite).")


def _pokemon_emerald_note(world: Any) -> str | None:
    if world.options.wild_pokemon.value == world.options.wild_pokemon.option_vanilla:
        return None
    return ("Logique minorée : avec les Pokémon sauvages aléatoires, le serveur ne dit pas où vit chaque espèce. "
            "Les « Pokedex - … » ne sont jamais comptés en logique.")


def _factorio_received(world: Any, items: list, start: list) -> None:
    """Factorio: the server sends each technology with the classification of the real generation, where only the
    technologies of the real (drawn) recipes are progression. The rules of `_factorio` count every technology a
    recipe could need: those must count once received, whatever the real recipe was."""
    from BaseClasses import ItemClassification
    for item in items:
        if item.name in world.advancement_technologies:
            item.classification |= ItemClassification.progression


def _factorio_state(world: Any, state: Any, checked: set[int]) -> None:
    """A checked "AP-<N>-<cost>" research proves pack N is made (see `_factorio`)."""
    packs = world.ordered_science_packs
    for code in checked:
        name = world.location_id_to_name.get(code, "")
        if name.startswith("AP-") and name[3:4].isdigit() and 1 <= int(name[3]) <= len(packs):
            event = f"Automated {packs[int(name[3]) - 1]}"
            state.prog_items[world.player][event] = max(1, state.prog_items[world.player][event])


STATE_HOOKS_M24: dict[str, Callable[[Any, Any, set[int]], None]] = {
    "Factorio": _factorio_state,
}


# Games whose logic is knowingly late (never early) for some options: what to tell the player.
LOGIC_NOTES_M24: dict[str, Callable[[Any], str | None]] = {
    "Factorio": _factorio_note,
    "Pokemon Emerald": _pokemon_emerald_note,
}


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
    "Factorio": _factorio_received,
}


ADAPTERS_M24: dict[str, Callable[[type, dict[str, Any], set[int]], ContextManager]] = {
    "ArchipelaCode": _archipelacode,
    "Cuphead": _cuphead,
    "Don't Starve Together": _dont_starve_together,
    "The Farmer Was Replaced": _tfwr,
    "Deep Rock Galactic": _deep_rock_galactic,
    "Factorio": _factorio,
    "Majora's Mask Recompiled": _mm_recomp,
    "PEAK": _peak,
    "Pokemon Emerald": _pokemon_emerald,
    "Slime Rancher 2": _slime_rancher_2,
    "Spirit Tracks": _tloz_st,
    "Trackmania": _trackmania,
    "TUNIC": _tunic,
    "Wikipelago": _wikipelago,
}
