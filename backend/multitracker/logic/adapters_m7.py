"""More per-game regeneration adapters (same contract as adapters.py)."""
from __future__ import annotations

import contextlib
import importlib
import logging
from typing import Any, Callable, ContextManager

log = logging.getLogger("multitracker.logic")


@contextlib.contextmanager
def _balatro(world_cls: type, slot_data: dict[str, Any], location_ids: set[int]):
    """Balatro: generate_early shuffles the stake order / picks random decks and stakes / shuffles the joker
    bundles. The result is in slot_data (included_decks, included_stakes in generation order, required_stake,
    jokerbundles, goal numbers): replay it after the original generate_early."""
    if "included_stakes" not in slot_data or "included_decks" not in slot_data:
        yield
        return
    pkg = world_cls.__module__
    decks_mod = importlib.import_module(f"{pkg}.BalatroDecks")
    items_mod = importlib.import_module(f"{pkg}.Items")
    key_to_deck = {v: k for k, v in decks_mod.deck_name_to_key.items()}
    original = world_cls.generate_early

    def generate_early(self) -> None:
        try:
            original(self)
        except Exception as exc:  # random yaml values may break the original; the slot_data state is enough
            log.warning("Balatro: generate_early failed (%s), replaying from slot_data", exc)
        decks = [key_to_deck[k] for k in slot_data["included_decks"] if k in key_to_deck]
        stakes = [items_mod.number_to_stake[int(n)] for n in slot_data["included_stakes"]
                  if int(n) in items_mod.number_to_stake]
        self.playable_decks = decks
        self.playable_stakes = stakes
        if slot_data.get("required_stake") in items_mod.number_to_stake:
            self.required_stake = items_mod.number_to_stake[slot_data["required_stake"]]
        elif stakes:
            self.required_stake = stakes[0]
        if slot_data.get("jokerbundles"):
            self.joker_bundles = [list(b) for b in slot_data["jokerbundles"]]
        for opt in ("decks_win_goal", "unique_deck_win_goal", "ante_win_goal", "jokers_unlock_goal"):
            if slot_data.get(opt) is not None:
                getattr(self.options, opt).value = int(slot_data[opt])

    world_cls.generate_early = generate_early
    try:
        yield
    finally:
        world_cls.generate_early = original


@contextlib.contextmanager
def _tloz_ph(world_cls: type, slot_data: dict[str, Any], location_ids: set[int]):
    """Phantom Hourglass: in a Universal Tracker regeneration the world's key rules (Mountain Passage...) assume
    the player may waste small keys unless the `ut_smart_keys` option is on, whereas the generator's own logic
    (the one that decided the seed is beatable) assumes keys are spent smartly. Force it on so the tool
    agrees with the generator (it is a tracker display option, not a seed property)."""
    original = world_cls.generate_early

    def generate_early(self) -> None:
        original(self)
        self.options.ut_smart_keys.value = 1

    world_cls.generate_early = generate_early
    try:
        yield
    finally:
        world_cls.generate_early = original


ADAPTERS_M7: dict[str, Callable[[type, dict[str, Any], set[int]], ContextManager]] = {
    "Balatro": _balatro,
    "The Legend of Zelda - Phantom Hourglass": _tloz_ph,
}
