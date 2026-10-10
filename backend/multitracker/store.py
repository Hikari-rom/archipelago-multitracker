"""Local state in SQLite: "last visit" per slot and the datapackage cache."""
from __future__ import annotations

import json
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any

from .apenv import ROOT

DEFAULT_DB = ROOT / "data" / "multitracker.sqlite3"

SCHEMA = """
CREATE TABLE IF NOT EXISTS seen (
    seed_name TEXT NOT NULL,
    slot_name TEXT NOT NULL,
    seen_count INTEGER NOT NULL,
    updated_at REAL NOT NULL,
    PRIMARY KEY (seed_name, slot_name)
);
CREATE TABLE IF NOT EXISTS datapackage (
    game TEXT NOT NULL,
    checksum TEXT NOT NULL,
    data TEXT NOT NULL,
    PRIMARY KEY (game, checksum)
);
"""


class Store:
    def __init__(self, path: Path | str = DEFAULT_DB) -> None:
        self.path = Path(path)
        if str(path) != ":memory:":
            self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._db = sqlite3.connect(str(path), check_same_thread=False)
        self._db.executescript(SCHEMA)
        self._db.commit()

    def close(self) -> None:
        with self._lock:
            self._db.close()

    # -- last visit ----------------------------------------------------------------------
    def seen_count(self, seed_name: str, slot_name: str) -> int | None:
        with self._lock:
            row = self._db.execute("SELECT seen_count FROM seen WHERE seed_name=? AND slot_name=?",
                                   (seed_name, slot_name)).fetchone()
        return None if row is None else int(row[0])

    def set_seen_count(self, seed_name: str, slot_name: str, count: int) -> None:
        with self._lock:
            self._db.execute("INSERT INTO seen(seed_name, slot_name, seen_count, updated_at) VALUES (?,?,?,?) "
                             "ON CONFLICT(seed_name, slot_name) DO UPDATE SET seen_count=excluded.seen_count, "
                             "updated_at=excluded.updated_at", (seed_name, slot_name, int(count), time.time()))
            self._db.commit()

    # -- datapackage ---------------------------------------------------------------------
    def load_datapackages(self) -> dict[tuple[str, str], dict[str, Any]]:
        with self._lock:
            rows = self._db.execute("SELECT game, checksum, data FROM datapackage").fetchall()
        return {(g, c): json.loads(d) for g, c, d in rows}

    def save_datapackage(self, game: str, checksum: str, data: dict[str, Any]) -> None:
        with self._lock:
            self._db.execute("INSERT OR REPLACE INTO datapackage(game, checksum, data) VALUES (?,?,?)",
                             (game, checksum, json.dumps(data)))
            self._db.commit()
