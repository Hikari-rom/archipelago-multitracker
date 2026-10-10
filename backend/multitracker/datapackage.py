"""Shared datapackage cache (id <-> name per game), persisted in SQLite and keyed by checksum."""
from __future__ import annotations

import time
from typing import Any

from .ap.tracker import DataPackageProvider
from .store import Store


class GameNames:
    def __init__(self, data: dict[str, Any]) -> None:
        self.items = {int(v): k for k, v in data.get("item_name_to_id", {}).items()}
        self.locations = {int(v): k for k, v in data.get("location_name_to_id", {}).items()}


class DataPackageCache(DataPackageProvider):
    def __init__(self, store: Store) -> None:
        self.store = store
        self._raw = store.load_datapackages()  # (game, checksum) -> data
        self._names: dict[str, GameNames] = {}  # game -> names of the checksum the server announced
        self._current: dict[str, str] = {}  # game -> checksum announced by the server
        self._inflight: dict[tuple[str, str], float] = {}  # requested by one tracker, not received yet

    def missing(self, checksums: dict[str, str]) -> list[str]:
        missing = []
        now = time.monotonic()
        for game, checksum in checksums.items():
            if self._current.get(game) != checksum:
                self._current[game] = checksum
                self._names.pop(game, None)
            key = (game, checksum)
            if key not in self._raw and now - self._inflight.get(key, -1e9) > 60:
                self._inflight[key] = now  # another tracker will not ask again for a minute
                missing.append(game)
        return missing

    def add(self, games: dict[str, dict[str, Any]]) -> None:
        for game, data in games.items():
            checksum = data.get("checksum") or self._current.get(game) or ""
            self._inflight.pop((game, checksum), None)
            if (game, checksum) in self._raw:
                continue
            self._raw[(game, checksum)] = data
            self.store.save_datapackage(game, checksum, data)
            if self._current.get(game) in (None, checksum):
                self._current[game] = checksum
                self._names.pop(game, None)

    def names(self, game: str | None) -> GameNames | None:
        if game is None:
            return None
        if game not in self._names:
            checksum = self._current.get(game)
            data = self._raw.get((game, checksum)) if checksum is not None else None
            if data is None:  # no checksum announced yet: any cached version is better than nothing
                data = next((d for (g, _), d in self._raw.items() if g == game), None)
            if data is None:
                return None
            self._names[game] = GameNames(data)
        return self._names[game]

    def item_name(self, game: str | None, item_id: int) -> str:
        names = self.names(game)
        return names.items.get(item_id, f"Item #{item_id}") if names else f"Item #{item_id}"

    def location_name(self, game: str | None, location_id: int) -> str:
        names = self.names(game)
        return names.locations.get(location_id, f"Location #{location_id}") if names else f"Location #{location_id}"
