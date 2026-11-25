"""Append-only check log on disk, one directory per seed (data/room_feed/<seed>/checks-<day>.jsonl)."""
from __future__ import annotations

import json
import logging
import re
import time
from collections import defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path

from ..apenv import ROOT

log = logging.getLogger(__name__)

ROOT_DIR = ROOT / "data" / "room_feed"
NAME_FIELDS = ("sender_name", "sender_game", "receiver_name", "receiver_game", "item_name", "location_name")
# Checks heard before the feed tagged collects and releases: a collect validates, in the same instant, the checks of
# every world that holds the collecting player's items. A run of checks to one receiver, each within BURST_GAP
# seconds of the previous one, from at least BURST_SENDERS worlds, is taken for one.
BURST_GAP = 1.0
BURST_SENDERS = 3
# A collect nobody heard (the app or the room feed was down) comes back in one catch-up poll: at least
# CATCHUP_SENDERS worlds' checks for one receiver, in a gap of at most CATCHUP_GAP seconds.
CATCHUP_SENDERS = 10
CATCHUP_GAP = 3600.0


@dataclass(frozen=True, slots=True)
class CheckEntry:
    recorded_at: float
    at: float | None
    after: float | None
    before: float | None
    src: str  # "live" | "catchup"
    sender: int
    receiver: int
    item: int
    location: int
    flags: int
    # "collect" | "release": validated by the server for a collect of the receiver or a release of the sender, not
    # done in the game (None: done, or not known)
    via: str | None = None

    @property
    def key(self) -> tuple[int, int]:
        return (self.sender, self.location)

    @property
    def when(self) -> float:
        if self.at is not None:
            return self.at
        if self.before is not None:
            return self.before
        return self.recorded_at


def safe_dir_name(seed: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]", "_", seed)[:80] or "_"


def _opt_float(value) -> float | None:
    return None if value is None else float(value)


def _parse_entry(row) -> CheckEntry:
    """Raise KeyError/TypeError/ValueError/AttributeError when the row is not a valid entry."""
    return CheckEntry(
        recorded_at=float(row["recorded_at"]), at=_opt_float(row.get("at")), after=_opt_float(row.get("after")),
        before=_opt_float(row.get("before")), src=str(row["src"]), sender=int(row["sender"]),
        receiver=int(row["receiver"]), item=int(row["item"]), location=int(row["location"]),
        flags=int(row["flags"]), via=row["via"] if row.get("via") in ("collect", "release") else None)


def _bursts(entries: list[CheckEntry]) -> set[tuple[int, int]]:
    """Keys of the checks that came in a collect burst (see BURST_GAP and CATCHUP_SENDERS)."""
    by_receiver: dict[int, list[CheckEntry]] = defaultdict(list)
    polls: dict[tuple, list[CheckEntry]] = defaultdict(list)
    for e in entries:
        if e.src == "live" and e.at is not None:
            by_receiver[e.receiver].append(e)
        elif e.src == "catchup" and e.after is not None and e.before is not None and e.before - e.after <= CATCHUP_GAP:
            polls[(e.receiver, e.after, e.before)].append(e)
    keys: set[tuple[int, int]] = set()
    for found in polls.values():
        if len({e.sender for e in found}) >= CATCHUP_SENDERS:
            keys |= {e.key for e in found}
    for runs in by_receiver.values():
        runs.sort(key=lambda e: e.at)
        run: list[CheckEntry] = []
        for e in [*runs, None]:
            if e is None or (run and e.at - run[-1].at > BURST_GAP):
                if len({r.sender for r in run}) >= BURST_SENDERS:
                    keys |= {r.key for r in run}
                run = []
            if e is not None:
                run.append(e)
    return keys


class RoomLog:
    def __init__(self, root: Path = ROOT_DIR):
        self.root = root
        self.seed: str | None = None
        self.entries: list[CheckEntry] = []
        self.keys: set[tuple[int, int]] = set()
        # slot id -> (name, game) as stored in the rows: the fallback when the room's slot table is unknown
        self.slot_names: dict[int, tuple[str | None, str | None]] = {}
        self.unreadable_lines = 0
        self.write_error: str | None = None
        self.tags_since: float | None = None  # since when live checks carry `via` (before: bursts, see _bursts)
        self._bulk: tuple[int, dict[int, set[int]]] | None = None  # (entries count, sender -> locations)

    @property
    def dir(self) -> Path | None:
        return None if self.seed is None else self.root / safe_dir_name(self.seed)

    def open_seed(self, seed: str) -> None:
        if seed == self.seed:
            return
        self.seed = seed
        self.entries = []
        self.keys = set()
        self.slot_names = {}
        self.unreadable_lines = 0
        self._bulk = None
        since = self.load_state().get("bulk_tags_since")
        self.tags_since = float(since) if isinstance(since, (int, float)) else None
        d = self.dir
        if d is None or not d.is_dir():
            return
        for path in sorted(d.glob("checks-*.jsonl")):
            self._load_file(path)

    def _load_file(self, path: Path) -> None:
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            log.warning("room feed: cannot read %s: %s", path, exc)
            return
        for line in text.split("\n"):  # not splitlines(): names may hold U+2028 and friends, left unescaped
            if not line.strip():
                continue
            try:
                row = json.loads(line)
                entry = _parse_entry(row)
            except (ValueError, KeyError, TypeError, AttributeError):
                self.unreadable_lines += 1
                continue
            self._remember_slots(entry, row)
            if entry.key in self.keys:
                continue
            self.keys.add(entry.key)
            self.entries.append(entry)

    def _remember_slots(self, entry: CheckEntry, names: dict) -> None:
        for slot, role in ((entry.sender, "sender"), (entry.receiver, "receiver")):
            name, game = names.get(f"{role}_name"), names.get(f"{role}_game")
            if isinstance(name, str) and name:
                self.slot_names[slot] = (name, game if isinstance(game, str) else None)

    def start_tags(self, now: float) -> None:
        """From now on, live checks carry `via` (first session that tags them; kept afterwards)."""
        if self.tags_since is None and self.dir is not None:
            self.tags_since = now
            self._bulk = None
            self.save_state(bulk_tags_since=now)

    def bulk_locations(self, sender: int) -> set[int]:
        """Locations of the `sender` slot validated by a collect or a release, not done in the game."""
        if self._bulk is None or self._bulk[0] != len(self.entries):
            since = self.tags_since
            bulk: dict[int, set[int]] = defaultdict(set)
            for e in self.entries:
                if e.via is not None:
                    bulk[e.sender].add(e.location)
            # live checks heard before the tags, and the catch-up ones (never tagged)
            for sender_slot, location in _bursts([e for e in self.entries if e.via is None and (
                    e.src == "catchup" or since is None or e.recorded_at < since)]):
                bulk[sender_slot].add(location)
            self._bulk = (len(self.entries), dict(bulk))
        return set(self._bulk[1].get(sender, ()))

    def _row(self, entry: CheckEntry, names: dict[str, str | None]) -> dict:
        row = asdict(entry)
        if row["via"] is None:
            del row["via"]
        for field in NAME_FIELDS:
            row[field] = names.get(field)
        return row

    @staticmethod
    def _day_file(d: Path, entry: CheckEntry) -> Path:
        return d / f"checks-{time.strftime('%Y-%m-%d', time.localtime(entry.recorded_at))}.jsonl"

    def add(self, entry: CheckEntry, names: dict[str, str | None]) -> bool:
        d = self.dir
        if d is None or entry.key in self.keys:
            return False
        self.entries.append(entry)
        self.keys.add(entry.key)
        row = self._row(entry, names)
        self._remember_slots(entry, row)
        self._append(self._day_file(d, entry), row)
        return True

    def add_many(self, batch: list[tuple[CheckEntry, dict[str, str | None]]]) -> list[CheckEntry]:
        """`add` for many entries at once (history import): one write per day file. Returns the entries added."""
        d = self.dir
        if d is None:
            return []
        added: list[CheckEntry] = []
        per_file: dict[Path, list[dict]] = {}
        for entry, names in batch:
            if entry.key in self.keys:
                continue
            self.entries.append(entry)
            self.keys.add(entry.key)
            row = self._row(entry, names)
            self._remember_slots(entry, row)
            per_file.setdefault(self._day_file(d, entry), []).append(row)
            added.append(entry)
        for path, rows in per_file.items():
            self._append(path, *rows)
        return added

    def add_presence(self, at: float, slot: int, event: str, tags: list[str]) -> None:
        d = self.dir
        if d is None:
            return
        self._append(d / "presence.jsonl", {"at": at, "slot": slot, "event": event, "tags": tags})

    def load_state(self) -> dict:
        d = self.dir
        return {} if d is None else self._read_json(d / "state.json")

    def save_state(self, **values) -> None:
        d = self.dir
        if d is None:
            return
        path = d / "state.json"
        self._write_json(path, {**self._read_json(path), **values})

    def remember_room(self, room_id: str, seed: str) -> None:
        path = self.root / "rooms.json"
        self._write_json(path, {**self._read_json(path), room_id: seed})

    def seed_for_room(self, room_id: str) -> str | None:
        seed = self._read_json(self.root / "rooms.json").get(room_id)
        return seed if isinstance(seed, str) else None

    @staticmethod
    def _read_json(path: Path) -> dict:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}
        return data if isinstance(data, dict) else {}

    def _fail(self, exc: OSError) -> None:
        self.write_error = f"{type(exc).__name__}: {exc}"[:300]
        log.warning("room feed: disk write failed: %s", self.write_error)

    def _append(self, path: Path, *rows: dict) -> None:
        data = "".join(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n" for row in rows).encode("utf-8")
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("a+b") as fh:
                if fh.seek(0, 2):  # a crash mid-write may have left a partial line: start a fresh one
                    fh.seek(-1, 2)
                    if fh.read(1) != b"\n":
                        data = b"\n" + data
                fh.write(data)
                fh.flush()
        except OSError as exc:
            self._fail(exc)
            return
        self.write_error = None

    def _write_json(self, path: Path, data: dict) -> None:
        tmp = path.with_name(path.name + ".tmp")
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            tmp.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
            tmp.replace(path)
        except OSError as exc:
            self._fail(exc)
            return
        self.write_error = None
