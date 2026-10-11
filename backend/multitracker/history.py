"""Item history and slot activity, as seen by the app (the server does not timestamp anything).

- Items: the server's received-items list of a slot is append-only, so an item is identified by its index. The
  first time the app syncs a slot (per seed), the items already there are recorded as "before tracking"
  (time unknown). While the app is connected, every new index gets the time the app received it. Items that
  arrive while the app is not connected (app stopped, room asleep, network down) only show up at the next sync:
  they get a range, from the last moment the app was watching the slot (`last_seen_at`) to that sync.
- Activity: the time of the last location check made by the slot while the app was watching ("active" slots).
  Big bursts of checks (`!release`, `!collect`, another game's goal) are not activity.

Writes are throttled (SD card): `last_seen_at` and `last_check_at` live in memory and reach SQLite at most every
WRITE_INTERVAL seconds, on disconnection and in `flush()`. Losing them in a crash only widens a range.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field

from .store import Store

WRITE_INTERVAL = 30.0
EXACT_GAP = 120.0  # items found at a sync less than this after the app last watched the slot keep an exact time
ACTIVITY_MAX_BURST = 10  # more new checks than this in one update: release/collect, not someone playing

ItemTime = tuple[float | None, float | None]  # (received_at, received_after)


@dataclass
class _Slot:
    times: list[ItemTime]
    started_at: float
    last_check: float | None
    last_seen: float
    live: bool = False  # connected and synced: the app sees items as they arrive
    written: dict[str, float | None] = field(default_factory=dict)  # last values persisted
    written_at: float = 0.0


class History:
    def __init__(self, store: Store) -> None:
        self.store = store
        self._slots: dict[tuple[str, str], _Slot] = {}
        self._untracked: set[tuple[str, str]] = set()  # known not to be in the database (only History adds rows)

    def _load(self, seed: str, slot: str) -> _Slot | None:
        key = (seed, slot)
        if key in self._slots:
            return self._slots[key]
        if key in self._untracked:
            return None
        row = self.store.tracking(seed, slot)
        if row is None:
            self._untracked.add(key)
            return None
        started = row["started_at"] or 0.0
        last_seen = row["last_seen_at"] or row["last_check_at"] or started  # rows from before last_seen_at existed
        s = _Slot(self.store.item_times(seed, slot), started, row["last_check_at"], last_seen)
        s.written = {"last_check": s.last_check, "last_seen": s.last_seen}
        self._slots[key] = s
        return s

    def on_items(self, seed: str, slot: str, count: int, fresh: bool = False, now: float | None = None) -> None:
        """The slot's item list (complete for this session) now has `count` items. `fresh`: first complete list
        after a (re)connection, so new items may have arrived while the app was not watching."""
        now = time.time() if now is None else now
        key = (seed, slot)
        s = self._load(seed, slot)
        if s is None:  # first sync ever: what is already there arrived before the app watched this slot
            self.store.start_tracking(seed, slot, now, count)
            self._untracked.discard(key)
            s = self._slots[key] = _Slot([(None, None)] * count, now, None, now, live=True)
            s.written = {"last_check": None, "last_seen": now}
            s.written_at = now
            return
        if count > len(s.times):
            new = count - len(s.times)
            after = s.last_seen if fresh and now - s.last_seen > EXACT_GAP else None
            self.store.add_item_times(seed, slot, len(s.times), new, now, after)
            s.times.extend([(now, after)] * new)
        if fresh:
            s.live = True
        self.seen(seed, slot, now)

    def on_checks(self, seed: str, slot: str, new_checks: int = 1, now: float | None = None) -> None:
        """The slot checked `new_checks` new locations while the app was connected (call on_items first)."""
        now = time.time() if now is None else now
        s = self._load(seed, slot)
        if s is None or new_checks > ACTIVITY_MAX_BURST:
            return  # not synced yet (initial state), or a release/collect
        s.last_check = now
        self._write(seed, slot, s, now)

    def seen(self, seed: str, slot: str, now: float | None = None) -> None:
        """The app is watching this slot (connected and synced) at `now`."""
        s = self._slots.get((seed, slot))
        if s is None or not s.live:
            return
        s.last_seen = time.time() if now is None else now
        self._write(seed, slot, s, s.last_seen)

    def lost(self, seed: str, slot: str, now: float | None = None) -> None:
        """The connection to this slot ended: what arrives from now on is only found at the next sync."""
        s = self._slots.get((seed, slot))
        if s is None or not s.live:
            return
        s.last_seen = time.time() if now is None else now
        s.live = False
        self._write(seed, slot, s, s.last_seen, force=True)

    def flush(self, now: float | None = None) -> None:
        """Persist everything (trackers stopping): live slots were watched until now."""
        now = time.time() if now is None else now
        for (seed, slot), s in self._slots.items():
            if s.live:
                s.last_seen, s.live = now, False
            self._write(seed, slot, s, now, force=True)

    def _write(self, seed: str, slot: str, s: _Slot, now: float, force: bool = False) -> None:
        values = {"last_check": s.last_check, "last_seen": s.last_seen}
        if values == s.written or (not force and now - s.written_at < WRITE_INTERVAL):
            return
        self.store.set_tracking_times(seed, slot, last_check_at=s.last_check, last_seen_at=s.last_seen)
        s.written, s.written_at = values, now

    def times(self, seed: str, slot: str) -> list[ItemTime]:
        s = self._load(seed, slot)
        return s.times if s else []

    def last_check(self, seed: str, slot: str) -> float | None:
        s = self._load(seed, slot)
        return s.last_check if s else None
