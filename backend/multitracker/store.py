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
CREATE TABLE IF NOT EXISTS tracking (
    seed_name TEXT NOT NULL,
    slot_name TEXT NOT NULL,
    started_at REAL NOT NULL,
    last_check_at REAL,
    PRIMARY KEY (seed_name, slot_name)
);
CREATE TABLE IF NOT EXISTS item_times (
    seed_name TEXT NOT NULL,
    slot_name TEXT NOT NULL,
    idx INTEGER NOT NULL,
    received_at REAL,
    PRIMARY KEY (seed_name, slot_name, idx)
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

    # -- history: when each item arrived, last check of each slot ---------------------------
    def tracking(self, seed_name: str, slot_name: str) -> tuple[float, float | None] | None:
        with self._lock:
            row = self._db.execute("SELECT started_at, last_check_at FROM tracking WHERE seed_name=? AND slot_name=?",
                                   (seed_name, slot_name)).fetchone()
        return None if row is None else (float(row[0]), None if row[1] is None else float(row[1]))

    def start_tracking(self, seed_name: str, slot_name: str, started_at: float) -> None:
        with self._lock:
            self._db.execute("INSERT OR IGNORE INTO tracking(seed_name, slot_name, started_at) VALUES (?,?,?)",
                             (seed_name, slot_name, started_at))
            self._db.commit()

    def set_last_check(self, seed_name: str, slot_name: str, at: float) -> None:
        with self._lock:
            self._db.execute("UPDATE tracking SET last_check_at=? WHERE seed_name=? AND slot_name=?",
                             (at, seed_name, slot_name))
            self._db.commit()

    def item_times(self, seed_name: str, slot_name: str) -> list[float | None]:
        with self._lock:
            rows = self._db.execute("SELECT idx, received_at FROM item_times WHERE seed_name=? AND slot_name=? "
                                    "ORDER BY idx", (seed_name, slot_name)).fetchall()
        return [None if at is None else float(at) for _, at in rows]

    def add_item_times(self, seed_name: str, slot_name: str, start: int, count: int, at: float | None) -> None:
        with self._lock:
            self._db.executemany("INSERT OR IGNORE INTO item_times(seed_name, slot_name, idx, received_at) "
                                 "VALUES (?,?,?,?)", [(seed_name, slot_name, i, at) for i in range(start, start + count)])
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
