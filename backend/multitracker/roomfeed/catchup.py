"""WebHost tracker API: parse the public tracker payloads and derive the checks the listener missed.

Only already-done information is read (items received, locations checked); nothing here talks to the game server.
"""
from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from urllib.parse import urlparse

from ..room import USER_AGENT, RoomError, _check_target, _NoRedirect, _parse_time, parse_room_url
from .log import CheckEntry

TRACKER_ID = re.compile(r"^[A-Za-z0-9_-]{8,40}$")

@dataclass
class TrackerSnapshot:
    received: dict[int, list[tuple[int, int, int, int]]] = field(default_factory=dict)  # receiver -> (item, loc, sender, flags)
    checks_done: dict[int, int] = field(default_factory=dict)
    activity: dict[int, float | None] = field(default_factory=dict)
    status: dict[int, int] = field(default_factory=dict)
    total_done: int = 0

@dataclass
class StaticInfo:
    totals: dict[int, int] = field(default_factory=dict)
    games: dict[int, str] = field(default_factory=dict)

def _int(value) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None

def _rows(data: dict, key: str, team: int):
    """Yield (player, row) for the well-formed rows of `data[key]` that belong to `team`."""
    rows = data.get(key)
    if not isinstance(rows, list):
        return
    for row in rows:
        if not isinstance(row, dict) or _int(row.get("team")) != team:
            continue
        player = _int(row.get("player"))
        if player is not None:
            yield player, row

def _received_item(raw) -> tuple[int, int, int, int] | None:
    if isinstance(raw, dict):
        raw = [raw.get("item"), raw.get("location"), raw.get("player"), raw.get("flags")]
    if not isinstance(raw, (list, tuple)) or len(raw) != 4:
        return None
    values = [_int(v) for v in raw]
    if any(v is None for v in values):
        return None
    return (values[0], values[1], values[2], values[3])

def parse_tracker(data: dict, team: int = 0) -> TrackerSnapshot:
    snap = TrackerSnapshot()
    for player, row in _rows(data, "player_items_received", team):
        items = row.get("items")
        if not isinstance(items, list):
            continue
        parsed = [item for item in map(_received_item, items) if item is not None]
        if parsed:
            snap.received[player] = parsed
    for player, row in _rows(data, "player_checks_done", team):
        locations = row.get("locations")
        if isinstance(locations, list):
            snap.checks_done[player] = len(locations)
    for player, row in _rows(data, "activity_timers", team):
        snap.activity[player] = _parse_time(row.get("time"))
    for player, row in _rows(data, "player_status", team):
        status = _int(row.get("status"))
        if status is not None:
            snap.status[player] = status
    totals = data.get("total_checks_done")
    if isinstance(totals, list):
        for row in totals:
            if isinstance(row, dict) and _int(row.get("team")) == team and _int(row.get("checks_done")) is not None:
                snap.total_done = row["checks_done"]
                break
    return snap

def parse_static(data: dict, team: int = 0) -> StaticInfo:
    info = StaticInfo()
    for player, row in _rows(data, "player_locations_total", team):
        total = _int(row.get("total_locations"))
        if total is not None:
            info.totals[player] = total
    for player, row in _rows(data, "player_game", team):
        game = row.get("game")
        if isinstance(game, str):
            info.games[player] = game
    return info

def api_urls(room_url: str, tracker_id: str) -> tuple[str, str]:
    base, _host, _room_id = parse_room_url(room_url)
    if not isinstance(tracker_id, str) or not TRACKER_ID.match(tracker_id):
        raise RoomError("identifiant de tracker invalide")
    return f"{base}/api/tracker/{tracker_id}", f"{base}/api/static_tracker/{tracker_id}"

def _open(url: str, timeout: float, max_bytes: int) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    opener = urllib.request.build_opener(_NoRedirect)
    with opener.open(req, timeout=timeout) as resp:
        body = resp.read(max_bytes + 1)
    if len(body) > max_bytes:
        raise RoomError("réponse trop grande")
    return body

def fetch_json(url: str, timeout: float = 30.0, max_bytes: int = 64 * 1024 * 1024) -> dict:
    parsed = urlparse(url)
    host = parsed.hostname or ""
    _check_target(parsed.scheme, host)
    try:
        data = json.loads(_open(url, timeout, max_bytes))
    except RoomError:
        raise
    except urllib.error.HTTPError as exc:
        raise RoomError(f"le site a répondu {exc.code}") from exc
    except (urllib.error.URLError, OSError) as exc:
        raise RoomError(f"impossible de joindre {host} : {exc}") from exc
    except ValueError as exc:  # JSONDecodeError and UnicodeDecodeError
        raise RoomError("réponse illisible du site") from exc
    if not isinstance(data, dict):
        raise RoomError("réponse illisible du site")
    return data

def missing_entries(snapshot: TrackerSnapshot, known: set[tuple[int, int]], polled_at: float,
                    after: float | None) -> list[CheckEntry]:
    """Checks received by some slot that the log does not know yet (the listener was not there to see them)."""
    seen = set(known)
    out: list[CheckEntry] = []
    for receiver in sorted(snapshot.received):
        for item, location, sender, flags in snapshot.received[receiver]:
            key = (sender, location)
            if sender == 0 or location <= 0 or key in seen:
                continue
            seen.add(key)
            out.append(CheckEntry(recorded_at=polled_at, at=None, after=after, before=polled_at, src="catchup",
                                  sender=sender, receiver=receiver, item=item, location=location, flags=flags))
    return out
