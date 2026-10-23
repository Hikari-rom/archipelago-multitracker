"""Who-is-playing model: per-slot presence derived from client statuses, joins/parts and recent checks. Pure, no I/O."""
from __future__ import annotations

NON_GAME_TAGS = frozenset({"Tracker", "TextOnly", "HintGame"})
RECENT_SECONDS = 600

# AP ClientStatus values
_UNKNOWN, _CONNECTED, _READY, _PLAYING, _GOAL = 0, 5, 10, 20, 30


class Presence:
    """`tracked` = slots followed by the app: our own connections keep their server status >= 5, so it says nothing."""

    def __init__(self, tracked: set[int]) -> None:
        self._tracked = set(tracked)
        self._base: dict[int, str] = {}
        self._statuses: dict[int, int] = {}
        self._checks: dict[int, float] = {}

    def session_start(self, statuses: dict[int, int]) -> None:
        self._statuses = dict(statuses)
        self._base = {}
        for slot, value in statuses.items():
            if slot in self._tracked:
                continue
            if value in (_READY, _PLAYING):
                self._base[slot] = "playing"
            elif value == _CONNECTED:
                self._base[slot] = "connected"
            elif value == _UNKNOWN:
                self._base[slot] = "offline"

    def status(self, slot: int, value: int) -> None:
        if slot in self._tracked:
            return
        self._statuses[slot] = value
        if value == _UNKNOWN:
            self._base[slot] = "offline"
        elif value in (_READY, _PLAYING):
            self._base[slot] = "playing"
        elif value == _CONNECTED:
            if self._base.get(slot) != "playing":
                self._base[slot] = "connected"

    def join(self, slot: int, tags: list[str]) -> None:
        if not NON_GAME_TAGS.intersection(tags):
            self._base[slot] = "playing"
        elif slot not in self._tracked and self._base.get(slot, "unknown") in ("offline", "unknown"):
            self._base[slot] = "connected"

    def part(self, slot: int) -> None:
        if slot in self._tracked:
            self._base[slot] = "offline"
            return
        last = self._statuses.get(slot, _UNKNOWN)
        self._base[slot] = "connected" if last >= _CONNECTED and last != _GOAL else "offline"

    def check(self, slot: int, at: float) -> None:
        prev = self._checks.get(slot)
        self._checks[slot] = at if prev is None else max(prev, at)

    def state(self, slot: int, now: float) -> str:
        last = self._checks.get(slot)
        if last is not None and now - last <= RECENT_SECONDS:
            return "playing"
        return self._base.get(slot, "unknown")

    def last_check(self, slot: int) -> float | None:
        return self._checks.get(slot)
