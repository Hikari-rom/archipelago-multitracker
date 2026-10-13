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
    last_seen_at REAL,
    PRIMARY KEY (seed_name, slot_name)
);
CREATE TABLE IF NOT EXISTS item_times (
    seed_name TEXT NOT NULL,
    slot_name TEXT NOT NULL,
    idx INTEGER NOT NULL,
    received_at REAL,
    received_after REAL,
    PRIMARY KEY (seed_name, slot_name, idx)
);
CREATE TABLE IF NOT EXISTS check_log (
    seed_name TEXT NOT NULL,
    slot_name TEXT NOT NULL,
    location INTEGER NOT NULL,
    checked_at REAL,
    checked_after REAL,
    item INTEGER,
    receiver INTEGER,
    flags INTEGER,
    PRIMARY KEY (seed_name, slot_name, location)
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
        self._migrate()
        self._db.commit()

    def _migrate(self) -> None:
        """Columns added after the first release of a table (CREATE TABLE IF NOT EXISTS keeps old tables)."""
        for table, column in (("tracking", "last_seen_at"), ("item_times", "received_after"),
                              ("tracking", "checks_started_at")):
            columns = {row[1] for row in self._db.execute(f"PRAGMA table_info({table})")}
            if column not in columns:
                self._db.execute(f"ALTER TABLE {table} ADD COLUMN {column} REAL")

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
    def tracking(self, seed_name: str, slot_name: str) -> dict[str, float | None] | None:
        """{started_at, last_check_at, last_seen_at} or None if the app never synced this slot."""
        with self._lock:
            row = self._db.execute("SELECT started_at, last_check_at, last_seen_at FROM tracking "
                                   "WHERE seed_name=? AND slot_name=?", (seed_name, slot_name)).fetchone()
        if row is None:
            return None
        return dict(zip(("started_at", "last_check_at", "last_seen_at"), (None if v is None else float(v) for v in row)))

    def start_tracking(self, seed_name: str, slot_name: str, started_at: float, count: int) -> None:
        """First sync: the `count` items already received have no known time (one transaction)."""
        with self._lock, self._db:
            self._db.execute("INSERT OR IGNORE INTO tracking(seed_name, slot_name, started_at, last_seen_at) "
                             "VALUES (?,?,?,?)", (seed_name, slot_name, started_at, started_at))
            self._db.executemany("INSERT OR IGNORE INTO item_times(seed_name, slot_name, idx, received_at) "
                                 "VALUES (?,?,?,NULL)", [(seed_name, slot_name, i) for i in range(count)])

    def set_tracking_times(self, seed_name: str, slot_name: str, *, last_check_at: float | None = None,
                           last_seen_at: float | None = None) -> None:
        with self._lock, self._db:
            if last_check_at is not None:
                self._db.execute("UPDATE tracking SET last_check_at=? WHERE seed_name=? AND slot_name=?",
                                 (last_check_at, seed_name, slot_name))
            if last_seen_at is not None:
                self._db.execute("UPDATE tracking SET last_seen_at=? WHERE seed_name=? AND slot_name=?",
                                 (last_seen_at, seed_name, slot_name))

    def item_times(self, seed_name: str, slot_name: str) -> list[tuple[float | None, float | None]]:
        """[(received_at, received_after)] by item index; received_after is set when the time is only a range."""
        with self._lock:
            rows = self._db.execute("SELECT received_at, received_after FROM item_times "
                                    "WHERE seed_name=? AND slot_name=? ORDER BY idx", (seed_name, slot_name)).fetchall()
        return [tuple(None if v is None else float(v) for v in row) for row in rows]

    def add_item_times(self, seed_name: str, slot_name: str, start: int, count: int, at: float | None,
                       after: float | None = None) -> None:
        with self._lock, self._db:
            self._db.executemany("INSERT OR IGNORE INTO item_times(seed_name, slot_name, idx, received_at, "
                                 "received_after) VALUES (?,?,?,?,?)",
                                 [(seed_name, slot_name, i, at, after) for i in range(start, start + count)])

    # -- history: when each location was checked, and what it held -------------------------
    def checks_started_at(self, seed_name: str, slot_name: str) -> float | None:
        """When the app started recording the slot's check times (None: not yet)."""
        with self._lock:
            row = self._db.execute("SELECT checks_started_at FROM tracking WHERE seed_name=? AND slot_name=?",
                                   (seed_name, slot_name)).fetchone()
        return None if row is None or row[0] is None else float(row[0])

    def check_log(self, seed_name: str, slot_name: str) -> dict[int, dict[str, Any]]:
        """{location: {checked_at, checked_after, item, receiver, flags}}"""
        with self._lock:
            rows = self._db.execute("SELECT location, checked_at, checked_after, item, receiver, flags FROM check_log "
                                    "WHERE seed_name=? AND slot_name=?", (seed_name, slot_name)).fetchall()
        keys = ("checked_at", "checked_after", "item", "receiver", "flags")
        return {int(row[0]): dict(zip(keys, row[1:])) for row in rows}

    def add_checks(self, seed_name: str, slot_name: str, locations: list[int], at: float | None,
                   after: float | None = None, started_at: float | None = None) -> None:
        """Locations newly seen checked, at `at` (None: before the app recorded check times). `started_at`: first
        recording for this slot (the locations are the ones checked before)."""
        with self._lock, self._db:
            self._db.executemany("INSERT INTO check_log(seed_name, slot_name, location, checked_at, checked_after) "
                                 "VALUES (?,?,?,?,?) ON CONFLICT(seed_name, slot_name, location) DO NOTHING",
                                 [(seed_name, slot_name, int(loc), at, after) for loc in locations])
            if started_at is not None:
                self._db.execute("UPDATE tracking SET checks_started_at=? WHERE seed_name=? AND slot_name=?",
                                 (started_at, seed_name, slot_name))

    def set_check_contents(self, seed_name: str, slot_name: str,
                           contents: list[tuple[int, int, int, int]]) -> None:
        """What checked locations held: [(location, item, receiving slot, flags)] (from LocationScouts)."""
        with self._lock, self._db:
            self._db.executemany(
                "INSERT INTO check_log(seed_name, slot_name, location, item, receiver, flags) VALUES (?,?,?,?,?,?) "
                "ON CONFLICT(seed_name, slot_name, location) DO UPDATE SET item=excluded.item, "
                "receiver=excluded.receiver, flags=excluded.flags",
                [(seed_name, slot_name, int(loc), int(item), int(receiver), int(flags))
                 for loc, item, receiver, flags in contents])

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
