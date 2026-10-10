"""Item history and slot activity, as seen by the app (the server does not timestamp anything).

- Items: the server's received-items list of a slot is append-only, so an item is identified by its index. The
  first time the app syncs a slot (per seed), the items already there are recorded as "before tracking"
  (time unknown); every later index gets the time the app received it.
- Activity: the time of the last location check made by the slot while the app was watching ("active" slots).
"""
from __future__ import annotations

import time

from .store import Store


class History:
    def __init__(self, store: Store) -> None:
        self.store = store
        self._times: dict[tuple[str, str], list[float | None]] = {}
        self._last_check: dict[tuple[str, str], float | None] = {}

    def _load(self, seed: str, slot: str) -> list[float | None] | None:
        key = (seed, slot)
        if key not in self._times:
            tracking = self.store.tracking(seed, slot)
            if tracking is None:
                return None
            self._times[key] = self.store.item_times(seed, slot)
            self._last_check[key] = tracking[1]
        return self._times[key]

    def on_items(self, seed: str, slot: str, count: int, now: float | None = None) -> None:
        """The slot's item list (complete for this session) now has `count` items."""
        now = time.time() if now is None else now
        times = self._load(seed, slot)
        if times is None:  # first sync ever: what is already there arrived before the app watched this slot
            self.store.start_tracking(seed, slot, now)
            self.store.add_item_times(seed, slot, 0, count, None)
            self._times[(seed, slot)] = [None] * count
            self._last_check[(seed, slot)] = None
            return
        if count > len(times):
            self.store.add_item_times(seed, slot, len(times), count - len(times), now)
            times.extend([now] * (count - len(times)))

    def on_checks(self, seed: str, slot: str, now: float | None = None) -> None:
        """The slot checked new locations while the app was connected (call on_items first)."""
        now = time.time() if now is None else now
        if self._load(seed, slot) is None:
            return  # not synced yet: these checks are the initial state, not activity
        self.store.set_last_check(seed, slot, now)
        self._last_check[(seed, slot)] = now

    def item_time(self, seed: str, slot: str, index: int) -> float | None:
        times = self._load(seed, slot) or []
        return times[index] if index < len(times) else None

    def last_check(self, seed: str, slot: str) -> float | None:
        self._load(seed, slot)
        return self._last_check.get((seed, slot))
