"""Regeneration adapters for the games of the 2026-10 room (M24, same contract as adapters.py)."""
from __future__ import annotations

import contextlib
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


ADAPTERS_M24: dict[str, Callable[[type, dict[str, Any], set[int]], ContextManager]] = {
    "ArchipelaCode": _archipelacode,
    "PEAK": _peak,
}
