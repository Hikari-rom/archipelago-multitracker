# Room-wide dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** An optional ("off" by default) room-wide dashboard: one read-only listener connection + WebHost tracker API
catch-up feed an append-only JSONL check log, served to a new v2 page "Room complète" (leaderboard, live feed,
activity, who is playing).

**Architecture:** New backend package `backend/multitracker/roomfeed/` (players grouping, JSONL log, catch-up,
listener, presence, orchestrator `RoomFeed`) owned by `Service`, started only when `room_dashboard: true`. New
`/api/roomfeed*` endpoints and SSE events. New v2 view `#room` with its own components.

**Tech Stack:** Python 3.13 / FastAPI / websockets / pytest (asyncio_mode=auto); Vue 3 + TypeScript + Tailwind v4 +
vitest (happy-dom) + `@tanstack/vue-virtual` (already a dependency).

**Spec:** `docs/superpowers/specs/2026-10-23-room-dashboard-design.md` (read it: it is the authority).

## Global Constraints

- Zero spoiler: only checks already done (ItemSend broadcasts) and items already received (tracker API). The
  roomfeed code never sends `LocationScouts`, never reads hints, never imports anything from `tests/` or
  `scripts/testenv/`.
- Read-only: the listener may only send `GetDataPackage`, `Connect`, `Get`, `SetNotify` (enforced in `_send`,
  raising `ForbiddenCommand` from `multitracker.ap.tracker`).
- The roomfeed never wakes the room: `fetch_room(..., wake=False)` only, no connection attempt without an address.
- `room_dashboard` is `False` by default; when false: no listener, no HTTP request, no file written, `/api/roomfeed/*`
  data endpoints return 404, `GET /api/roomfeed` returns `{"enabled": false, ...}`.
- Files: `data/room_feed/<safe seed>/checks-YYYY-MM-DD.jsonl`, `presence.jsonl`, `state.json`; plus
  `data/room_feed/rooms.json` (room id → seed). Never delete files.
- Players override file: `config/room_players.yaml` (gitignored; add it to `.gitignore`).
- Code, comments, commit messages in English; UI text and docs in French; game/item/location names never translated.
- Backend tests: `scripts/test.sh -q tests/<file>` (sets `PYTHONHASHSEED=0`). Front: `cd frontend && npm test` and
  `npm run build` (if the rtk hook breaks npm, prefix with `rtk proxy`).
- New local test-server port for integration tests: **38283** (38281/38284-38289 are taken, 38290 is the mock vite).
- Pi rules: no sudo/apt/global installs, kill only your own processes (check the command line; never `pkill -f`).
  Never connect tests or the bot to the real room (`config/room.yaml`).
- Commit after each task with the trailers:
  `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>` and
  `Claude-Session: https://claude.ai/code/session_0158GQtzHfEWz7d15p2mTqYa`. Do not push (the controller pushes).
- v2 UI: phone = `max-width: 699px`, touch targets ≥ 44 px (`max-[699px]:min-h-11`), no horizontal page scroll; use
  the v2 tokens (`text-logic`, `text-done`, `bg-warn text-warn-foreground`, `bg-card`, `text-muted-foreground`) and
  `CATEGORY_CLASS` from `frontend/src/v2/lib/days.ts` for PROG/UTILE/PIÈGE badges.

## Review Focus

1. A listener reconnect during heavy traffic must not duplicate entries (live after catch-up, catch-up after live):
   dedup by `(sender, location)` everywhere — tested in Tasks 3, 4 and 6.
2. The room sleeping / no address / tracker API down: the feed must stay quiet (no tight loop, no wake), report the
   state, and the rest of the app must be unaffected — tested in Task 6.
3. Corrupted or partial JSONL lines (power cut on the Pi) must not prevent loading — tested in Task 3.
4. Disabled module = zero side effects (no files, no requests) — tested in Tasks 6 and 7.
5. Phone width on the Room page (long slot/game/item names) must not scroll horizontally — checked in Tasks 10/11
   with `min-w-0`/`truncate`/`break-words`, and by the controller's screenshots.

---

### Task 1: Config flag `room_dashboard` and the tracker id in `RoomInfo`

**Files:**
- Modify: `backend/multitracker/config.py` (dataclass field, `load`, `save`)
- Modify: `backend/multitracker/room.py` (`RoomInfo.tracker`, `fetch_room`)
- Modify: `backend/multitracker/api.py` (`ConfigBody.room_dashboard`, GET/PUT config, `/api/slots`)
- Modify: `.gitignore` (add `config/room_players.yaml`)
- Test: `tests/test_config_m9.py`, `tests/test_room_discovery.py` (append tests)

**Interfaces:**
- Produces: `RoomConfig.room_dashboard: bool = False`; `RoomInfo.tracker: str | None = None`;
  `GET /api/config` → `"room_dashboard": bool`; `PUT /api/config` body `room_dashboard: bool | None` (None = keep);
  `GET /api/slots` → `"room_dashboard": bool`.

- [ ] **Step 1: Write failing tests.** Read both test files first and follow their style (they already build
  configs in `tmp_path`, and `test_room_discovery.py` already fakes the HTTP layer — reuse its helper). Add:
  - `load()` of a yaml without the key → `room_dashboard is False`; with `room_dashboard: true` → `True`;
    `save()` then `load()` round-trips both values; the saved file contains `room_dashboard: false` by default.
  - the API: `GET /api/config` includes `room_dashboard`; `PUT /api/config` with `room_dashboard: true` stores it;
    a later PUT without the field keeps it (same pattern as the existing `wake_room`/`scout_checked` tests);
    `GET /api/slots` includes `room_dashboard`.
  - `fetch_room` parses `"tracker": "yQdtVUWGRFaaMCu14kdq8A"` into `info.tracker`; missing or non-string → `None`.
- [ ] **Step 2: Run them, expect failures.** `scripts/test.sh -q tests/test_config_m9.py tests/test_room_discovery.py`
- [ ] **Step 3: Implement.**
  - `config.py`: field `room_dashboard: bool = False  # room-wide dashboard (roomfeed): extra listener + check log`;
    in `load`: `room_dashboard=raw.get("room_dashboard") is True`; in `save`: `data["room_dashboard"] =
    cfg.room_dashboard` right after `scout_checked`.
  - `room.py`: `tracker: str | None = None  # WebHost tracker id (public tracker API)` as the last `RoomInfo` field;
    in `fetch_room`: `tracker = data.get("tracker")` and pass `tracker=tracker if isinstance(tracker, str) and
    tracker else None`.
  - `api.py`: `ConfigBody.room_dashboard: bool | None = None`; `get_config` adds `"room_dashboard":
    cfg.room_dashboard`; `put_config` builds `RoomConfig(..., room_dashboard=current.room_dashboard if
    body.room_dashboard is None else body.room_dashboard)`; `/api/slots` adds `"room_dashboard":
    service.config.room_dashboard`.
  - `.gitignore`: add `config/room_players.yaml` next to the other `config/room*.yaml` lines.
- [ ] **Step 4: Run the tests, expect PASS.** Also run `scripts/test.sh -q tests/test_config_m9.py
  tests/test_room_discovery.py tests/test_room_target.py`.
- [ ] **Step 5: Update `docs/API.md`** (French): in `GET /api/config` add `"room_dashboard": false, // tableau de
  bord de la room complète (désactivé par défaut)`; in `PUT /api/config` add `"room_dashboard": false, // omis =
  garder le réglage actuel`; in "Champs ajoutés à `GET /api/slots`" add `room_dashboard`.
- [ ] **Step 6: Commit** `git commit -m "Config: room_dashboard flag (off by default), tracker id from room status"`.

---

### Task 2: Player grouping (`roomfeed/players.py`)

**Files:**
- Create: `backend/multitracker/roomfeed/__init__.py` (docstring only:
  `"""Room-wide dashboard: listener, catch-up and check log for every slot of the room (optional module)."""`)
- Create: `backend/multitracker/roomfeed/players.py`
- Test: `tests/test_roomfeed_players.py`

**Interfaces:**
- Produces: `OVERRIDES_PATH: Path` (= `ROOT / "config" / "room_players.yaml"`),
  `group_players(names: list[str], overrides: dict[str, str] | None = None) -> dict[str, str]` (slot name → player),
  `load_overrides(path: Path = OVERRIDES_PATH) -> dict[str, str]`.

- [ ] **Step 1: Write the failing test.**

```python
from pathlib import Path

from multitracker.roomfeed.players import group_players, load_overrides

NAMES = ["romain_bw", "romain_kh2", "balatrom", "MaxFez", "MaxTD6", "MaxTruck", "MaxAccurate", "dashxcel",
         "dashxori_blind", "dashxportal", "experts@miami", "kuro_33", "kuro_TUNIC", "mathcroft_mc", "mariemme_dome",
         "menthe_isaac", "big_walkies", "Discapelago", "ash_tunic", "ash_paint"]


def test_auto_groups():
    g = group_players(NAMES)
    assert g["romain_bw"] == g["romain_kh2"] == "romain"
    assert g["MaxFez"] == g["MaxTD6"] == g["MaxTruck"] == g["MaxAccurate"] == "Max"
    assert g["dashxcel"] == g["dashxori_blind"] == g["dashxportal"] == "dashx"
    assert g["kuro_33"] == g["kuro_TUNIC"] == "kuro"
    assert g["ash_tunic"] == g["ash_paint"] == "ash"
    # different people sharing only one or two letters stay apart
    assert len({g["mathcroft_mc"], g["mariemme_dome"], g["menthe_isaac"], g["MaxFez"]}) == 4
    assert g["experts@miami"] == "experts@miami"
    assert g["balatrom"] == "balatrom"
    assert g["big_walkies"] == "big"
    assert g["Discapelago"] == "Discapelago"


def test_overrides_win():
    g = group_players(NAMES, {"balatrom": "romain", "unknown_slot": "x"})
    assert g["balatrom"] == "romain"
    assert "unknown_slot" not in g


def test_load_overrides(tmp_path: Path):
    p = tmp_path / "room_players.yaml"
    assert load_overrides(p) == {}
    p.write_text("# slot: joueur\nbalatrom: romain\nbad: [1, 2]\n", encoding="utf-8")
    assert load_overrides(p) == {"balatrom": "romain"}
    p.write_text(":::not yaml", encoding="utf-8")
    assert load_overrides(p) == {}
```

- [ ] **Step 2: Run, expect ImportError.** `scripts/test.sh -q tests/test_roomfeed_players.py`
- [ ] **Step 3: Implement.**

```python
"""Group the room's slots into players: automatic rule from the slot names, then manual corrections
(config/room_players.yaml, `slot: player`)."""
from __future__ import annotations

import logging
from pathlib import Path

import yaml

from ..apenv import ROOT

log = logging.getLogger(__name__)

OVERRIDES_PATH = ROOT / "config" / "room_players.yaml"
MIN_PREFIX = 3  # bases sharing this many first letters belong to the same player


def _base(name: str) -> str:
    return name.split("_", 1)[0] or name


def _common_prefix(words: list[str]) -> str:
    first, last = min(words), max(words)
    i = 0
    while i < min(len(first), len(last)) and first[i] == last[i]:
        i += 1
    return first[:i]


def group_players(names: list[str], overrides: dict[str, str] | None = None) -> dict[str, str]:
    """Slot name -> player. Base = text before the first "_"; bases sharing their first MIN_PREFIX letters
    (case-insensitive) form one player, named after their longest common prefix (casing of the first name)."""
    bases = {n: _base(n) for n in names}
    clusters: dict[str, list[str]] = {}
    for base in dict.fromkeys(b.lower() for b in bases.values()):
        clusters.setdefault(base[:MIN_PREFIX], []).append(base)
    label: dict[str, str] = {}  # lowered base -> player
    for members in clusters.values():
        prefix = _common_prefix(members)
        original = next(b for b in bases.values() if b.lower().startswith(prefix))
        for m in members:
            label[m] = original[:len(prefix)]
    result = {n: label[b.lower()] for n, b in bases.items()}
    for slot, player in (overrides or {}).items():
        if slot in result:
            result[slot] = player
    return result


def load_overrides(path: Path = OVERRIDES_PATH) -> dict[str, str]:
    """`slot: player` pairs; a missing or unreadable file means no correction."""
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    except (OSError, yaml.YAMLError) as exc:
        log.warning("room players file %s ignored: %s", path, exc)
        return {}
    if not isinstance(raw, dict):
        return {}
    return {str(k): str(v) for k, v in raw.items() if isinstance(v, (str, int)) and str(v).strip()}
```

  Note: with a single distinct base in a cluster the prefix is the base itself (`romain`, `experts@miami`).
- [ ] **Step 4: Run the test, expect PASS.**
- [ ] **Step 5: Commit** `git commit -m "Roomfeed: group the room's slots into players"`.

---

### Task 3: Check log on disk (`roomfeed/log.py`)

**Files:**
- Create: `backend/multitracker/roomfeed/log.py`
- Test: `tests/test_roomfeed_log.py`

**Interfaces:**
- Produces:
  - `CheckEntry` (frozen dataclass, `slots=True`): `recorded_at: float, at: float | None, after: float | None,
    before: float | None, src: str ("live"|"catchup"), sender: int, receiver: int, item: int, location: int,
    flags: int`; property `key -> tuple[int, int]` = `(sender, location)`; property `when -> float` =
    `at if at is not None else before if before is not None else recorded_at`.
  - `ROOT_DIR = ROOT / "data" / "room_feed"`; `safe_dir_name(seed: str) -> str` (`re.sub(r"[^A-Za-z0-9_.-]", "_",
    seed)[:80] or "_"`).
  - `RoomLog(root: Path = ROOT_DIR)`: attributes `seed: str | None`, `entries: list[CheckEntry]` (recording order),
    `keys: set[tuple[int, int]]`, `unreadable_lines: int`, `write_error: str | None`; methods
    `open_seed(seed: str) -> None` (no-op if same seed; otherwise resets memory and loads every
    `checks-*.jsonl` of that seed dir, sorted by file name), `add(entry: CheckEntry, names: dict[str, str | None])
    -> bool` (False if the key is known or no seed is open; else appends to memory and to
    `checks-<local date of recorded_at>.jsonl`), `add_presence(at: float, slot: int, event: str, tags: list[str])
    -> None`, `load_state() -> dict`, `save_state(**values) -> None` (merge into `state.json`, atomic write),
    `remember_room(room_id: str, seed: str) -> None` / `seed_for_room(room_id: str) -> str | None`
    (`rooms.json` at the root), `dir -> Path | None` property.
  - JSON line format (one object per line, `ensure_ascii=False`, compact separators): the ten `CheckEntry`
    fields plus `sender_name, sender_game, receiver_name, receiver_game, item_name, location_name` from `names`
    (missing keys → null).

- [ ] **Step 1: Write the failing tests** covering:
  - add → file `checks-<date>.jsonl` exists in `root/<safe seed>/` with one parseable line holding the fields and
    the names; a second add with the same `(sender, location)` returns False and writes nothing.
  - two entries recorded on two different local days (`recorded_at` = noon of 2026-10-22 and 2026-10-23 local time,
    built with `time.mktime`) go to two files.
  - a new `RoomLog` on the same root, `open_seed(same)` → reloads both entries in order, with `keys` filled;
    an entry with `at=None, after=None, before=123.0` round-trips with `when == 123.0`.
  - a file with one valid line, one truncated line (`{"recorded_at": 1,`) and one blank line → 1 entry loaded,
    `unreadable_lines == 1`, nothing raised.
  - another seed → separate directory, memory reset; seed `"a/b c"` → dir `a_b_c`.
  - `add` before `open_seed` → False, nothing written.
  - `add_presence` appends to `presence.jsonl`; `save_state(last_live_at=5.0)` then `save_state(listening_since=1.0)`
    → `load_state() == {"last_live_at": 5.0, "listening_since": 1.0}`; missing/corrupt `state.json` → `{}`.
  - `remember_room("wVAe", "123")` then a new `RoomLog(root).seed_for_room("wVAe") == "123"`; unknown → None.
  - write failure: make the seed dir read-only (`chmod 0o500`), `add` → returns True (kept in memory),
    `write_error` set (string); restore permissions in a `finally`.
- [ ] **Step 2: Run, expect ImportError.** `scripts/test.sh -q tests/test_roomfeed_log.py`
- [ ] **Step 3: Implement** with `pathlib`, `json`, `time.localtime(recorded_at)` + `time.strftime("%Y-%m-%d", …)`
  for the file name, append mode `"a"` + `encoding="utf-8"` + one `write(line + "\n")` per entry (flush after each
  write), atomic `state.json`/`rooms.json` via `tmp.write_text` + `tmp.replace(path)`. Wrap every disk write in
  `try/except OSError as exc: self.write_error = f"{type(exc).__name__}: {exc}"[:300]; log.warning(...)`, and reset
  `write_error = None` after a successful write. When loading, skip lines that are blank; count lines that fail to
  parse or miss a required field in `unreadable_lines`; skip duplicate keys silently.
- [ ] **Step 4: Run, expect PASS.**
- [ ] **Step 5: Commit** `git commit -m "Roomfeed: append-only JSONL check log per seed"`.

---

### Task 4: Tracker API and catch-up merge (`roomfeed/catchup.py`)

**Files:**
- Create: `backend/multitracker/roomfeed/catchup.py`
- Test: `tests/test_roomfeed_catchup.py`

**Interfaces:**
- Consumes: `CheckEntry` (Task 3); `room._check_target`, `room._NoRedirect`, `room.USER_AGENT`,
  `room.parse_room_url`, `room._parse_time`, `room.RoomError`.
- Produces:
  - `TrackerSnapshot` dataclass: `received: dict[int, list[tuple[int, int, int, int]]]` (receiver slot →
    `(item, location, sender, flags)`), `checks_done: dict[int, int]` (slot → count of `player_checks_done`
    locations), `activity: dict[int, float | None]` (from `activity_timers`), `status: dict[int, int]` (from
    `player_status`), `total_done: int` (team 0 of `total_checks_done`, 0 if absent).
  - `StaticInfo` dataclass: `totals: dict[int, int]`, `games: dict[int, str]`.
  - `parse_tracker(data: dict, team: int = 0) -> TrackerSnapshot`, `parse_static(data: dict, team: int = 0) ->
    StaticInfo` (entries of other teams ignored; malformed entries skipped; received items accepted as list
    `[item, location, player, flags]` or dict `{"item","location","player","flags"}`).
  - `api_urls(room_url: str, tracker_id: str) -> tuple[str, str]` → (`<base>/api/tracker/<id>`,
    `<base>/api/static_tracker/<id>`); raises `RoomError` on a bad URL or an id not matching
    `^[A-Za-z0-9_-]{8,40}$`.
  - `fetch_json(url: str, timeout: float = 30.0, max_bytes: int = 64 * 1024 * 1024) -> dict` (same host checks as
    `room.py`, no redirects; raises `RoomError` with a French message on HTTP/network/JSON errors or a body larger
    than `max_bytes`).
  - `missing_entries(snapshot: TrackerSnapshot, known: set[tuple[int, int]], polled_at: float, after: float | None)
    -> list[CheckEntry]`: one `CheckEntry(recorded_at=polled_at, at=None, after=after, before=polled_at,
    src="catchup", sender, receiver, item, location, flags)` per received item whose sender ≠ 0, location > 0 and
    key `(sender, location)` not in `known` (and not already produced in this call), ordered by receiver then list
    order.

- [ ] **Step 1: Write the failing tests** with an inline payload shaped like the real API (see spec) — 3 slots,
  team 0, plus one team-1 entry that must be ignored:
  - `parse_tracker`: received lists (list and dict forms), checks_done counts, activity times (RFC 1123 string →
    epoch; null → None), status, total_done; garbage entries (`{"team": 0}` without player, items that are not
    4-long) skipped.
  - `parse_static`: totals and games.
  - `missing_entries`: skips sender 0 and location ≤ 0, skips known keys, does not duplicate a key that appears twice
    in the payload, sets `after`/`before`/`src`.
  - `api_urls("https://archipelago.gg/room/wVAe_qVET2qit1wc2Kzj6A", "yQdtVUWGRFaaMCu14kdq8A")` → the two URLs; bad
    id (`"../x"`) → `RoomError`.
  - `fetch_json`: monkeypatch `catchup._open` (a module-level `_open(url, timeout, max_bytes) -> bytes` helper that
    you create to wrap urllib) to return bytes → dict; too-large / invalid JSON / `urllib.error.URLError` →
    `RoomError`. A non-allowed host (`http://127.0.0.1/...` while `MT_ALLOWED_HOSTS` is unset) → `RoomError`
    (check how `test_room_target.py` exercises `_check_target` and mirror it).
- [ ] **Step 2: Run, expect ImportError.** `scripts/test.sh -q tests/test_roomfeed_catchup.py`
- [ ] **Step 3: Implement.** `_open` reads `max_bytes + 1` and raises `RoomError("réponse trop grande")` if
  longer. Error messages: `"le site a répondu {code}"`, `"impossible de joindre {host} : {exc}"`,
  `"réponse illisible du site"`.
- [ ] **Step 4: Run, expect PASS.**
- [ ] **Step 5: Commit** `git commit -m "Roomfeed: tracker API parsing and catch-up of missed checks"`.

---

### Task 5: Presence model (`roomfeed/presence.py`)

**Files:**
- Create: `backend/multitracker/roomfeed/presence.py`
- Test: `tests/test_roomfeed_presence.py`

**Interfaces:**
- Produces: `NON_GAME_TAGS = frozenset({"Tracker", "TextOnly", "HintGame"})`, `RECENT_SECONDS = 600`,
  `class Presence(tracked: set[int])` with `session_start(statuses: dict[int, int]) -> None`,
  `status(slot: int, value: int) -> None`, `join(slot: int, tags: list[str]) -> None`, `part(slot: int) -> None`,
  `check(slot: int, at: float) -> None`, `state(slot: int, now: float) -> str` (`"playing" | "connected" |
  "offline" | "unknown"`), `last_check(slot: int) -> float | None`.

Rules (spec "Qui joue"): `tracked` = slot ids followed by the app (their server status is held ≥ 5 by our own
connections). Base state per slot, default `"unknown"`.
- `session_start`: tracked → `"unknown"`; else status 10/20 → `"playing"`, 5 → `"connected"`, 0 → `"offline"`,
  30 or absent → `"unknown"`. Remembers the statuses.
- `status` (untracked only, tracked ignored): remember it; 0 → `"offline"`; 10/20 → `"playing"`; 5 → keep
  `"playing"` if already, else `"connected"`; 30 → unchanged.
- `join`: no tag in `NON_GAME_TAGS` → `"playing"`; else (tool client) untracked and base in
  {`"offline"`, `"unknown"`} → `"connected"`.
- `part`: tracked → `"offline"`; untracked → `"connected"` if the last known status ≥ 5 (and ≠ 30) else
  `"offline"`.
- `check` stores the latest check time; `state()` returns `"playing"` when `now - last_check <= RECENT_SECONDS`,
  else the base state.

- [ ] **Step 1: Write failing tests** for each rule above (one test per bullet, plus the recent-check override and
  "tracked slot ignores status").
- [ ] **Step 2: Run, expect ImportError.** `scripts/test.sh -q tests/test_roomfeed_presence.py`
- [ ] **Step 3: Implement** (plain dicts, no I/O).
- [ ] **Step 4: Run, expect PASS.**
- [ ] **Step 5: Commit** `git commit -m "Roomfeed: who-is-playing model"`.

---

### Task 6: Listener connection (`roomfeed/listener.py`) + live integration test

**Files:**
- Create: `backend/multitracker/roomfeed/listener.py`
- Test: `tests/test_roomfeed_listener.py` (unit, fake socket) and `tests/test_roomfeed_live.py` (local server)

**Interfaces:**
- Consumes: `multitracker.ap.net` (`open_socket`, `encode`, `decode`, `AP_VERSION`), `ForbiddenCommand`,
  `FATAL_REFUSALS` from `multitracker.ap.tracker`, `DataPackageCache` (`missing(checksums)`, `add(games)`).
- Produces: `LISTENER_COMMANDS = frozenset({"GetDataPackage", "Connect", "Get", "SetNotify"})` and

```python
class RoomListener:
    def __init__(self, server: Callable[[], str], password: str, slot_name: str, datapackage,
                 on_session: Callable[["RoomListener"], None] | None = None,
                 on_check: Callable[[int, int, int, int, int, float], None] | None = None,  # sender, receiver, item, location, flags, at
                 on_join: Callable[[int, list[str]], None] | None = None,
                 on_part: Callable[[int], None] | None = None,
                 on_status: Callable[[int, int], None] | None = None,  # slot, client status
                 on_state: Callable[["RoomListener"], None] | None = None,
                 min_delay: float = 2.0, max_delay: float = 60.0) -> None: ...
    status: str            # "idle" | "connecting" | "listening" | "disconnected" | "error"
    error: str | None
    seed_name: str | None
    team: int | None
    slot: int | None
    players: dict[int, dict[str, str | None]]   # slot id -> {"name", "game"} (from Connected players + slot_info)
    listening_since: float | None
    statuses: dict[int, int]                    # last client status per slot
    def start(self) -> None
    async def stop(self) -> None
```

Behaviour (model it on `SlotTracker._run/_session/_handle`, copy its reconnect loop and backoff):
- Empty address from `server()` → status `"disconnected"`, error `"adresse du serveur inconnue (room endormie ?)"`,
  wait `max_delay` (no wake-up, no `on_connect_error`).
- `RoomInfo` → `seed_name`; `GetDataPackage` for `datapackage.missing(checksums)` if any; `Connect` with
  `{"cmd": "Connect", "password": password or None, "game": "", "name": slot_name, "uuid": <uuid4 hex>,
  "version": net.AP_VERSION, "items_handling": 0, "tags": ["Tracker"], "slot_data": False}`.
- `DataPackage` → `datapackage.add(msg["data"]["games"])`.
- `ConnectionRefused` → status `"error"` with `"connexion refusée : <errors>"`; fatal refusal → wait `max_delay`.
- `Connected` → `team`, `slot`, `players` (from `players` + `slot_info`, like `SlotTracker`), status `"listening"`,
  `listening_since = time.time()`, then send `Get` and `SetNotify` for
  `[f"_read_client_status_{team}_{s}" for s in players]` (one packet each), then `on_session(self)` and `on_state`.
- `Retrieved`/`SetReply` on those keys → `statuses[slot] = int(value or 0)` and `on_status(slot, value)`.
- `PrintJSON` with `type == "ItemSend"`: `item = msg["item"]` (dict with `item, location, player, flags`, or a
  list in that order) and `receiver = msg["receiving"]` → `on_check(player, receiver, item, location, flags,
  time.time())`. Malformed → ignored with a debug log.
- `PrintJSON` `Join` → `on_join(msg["slot"], msg.get("tags") or [])` when `msg.get("team") == self.team`;
  `Part` → `on_part(msg["slot"])` likewise. Every other message ignored.
- `_send` raises `ForbiddenCommand` for any cmd outside `LISTENER_COMMANDS`.
- Callback exceptions are caught and logged (`log.exception`), never break the session.

- [ ] **Step 1: Unit tests (`test_roomfeed_listener.py`)** with a fake socket object (async iterator over prepared
  frames + `send` recording + `close`), monkeypatching `net.open_socket`:
  RoomInfo → Connect sent with `tags == ["Tracker"]`, `items_handling == 0`; Connected → Get/SetNotify with all
  status keys; ItemSend (dict form and list form) → `on_check` args; Join/Part of the right team only; Retrieved
  status → `on_status`; `_send({"cmd": "LocationScouts", ...})` and `Say`/`LocationChecks` → `ForbiddenCommand`;
  empty address → status `"disconnected"` and no `open_socket` call.
- [ ] **Step 2: Live test (`test_roomfeed_live.py`)**, port 38283, reusing the multi5 seed and helpers:

```python
PORT = 38283
SERVER = f"ws://127.0.0.1:{PORT}"
# fixtures: seed_zip = generated_seed("multi5") (module scope); server = start_server(seed_zip, PORT) / stop_server
```
  Test A — live: start a `RoomListener(lambda: f"127.0.0.1:{PORT}", "test", "Celeste", DataPackageCache(Store(tmp)))`,
  wait for `"listening"`; with `GameBot(SERVER, "KH2", "Kingdom Hearts 2")` check 5 random locations; assert 5
  `on_check` calls with sender = KH2's slot id and those locations, `at` within the test's time range; the bot's
  join produces `on_join` with tags not containing `"Tracker"`.
  Test B — no replay: listener stopped; the bot checks 4 more locations; a new listener starts and listens for 3 s
  after `"listening"` → zero `on_check` calls for those 4 locations (this is the "est-ce que ça rattrape ?" answer:
  the server does not replay).
  Use `eventually` from `test_backend_level1` (import it like `test_history_checks.py` does).
- [ ] **Step 3: Run, expect failures**, implement, run again:
  `scripts/test.sh -q tests/test_roomfeed_listener.py tests/test_roomfeed_live.py`.
- [ ] **Step 4: Commit** `git commit -m "Roomfeed: read-only listener connection (ItemSend, Join/Part, statuses)"`.

---

### Task 7: `RoomFeed` orchestrator + `Service` integration + catch-up integration test

**Files:**
- Create: `backend/multitracker/roomfeed/feed.py`
- Modify: `backend/multitracker/service.py` (create/start/stop the feed, `bk_of`)
- Test: `tests/test_roomfeed_feed.py` (unit, fake listener/fetch) and extend `tests/test_roomfeed_live.py`
  (Test C — catch-up)

**Interfaces:**
- Consumes: Tasks 2–6, `room.fetch_room`, `room.parse_room_url`.
- Produces:

```python
class RoomFeed:
    def __init__(self, *, server: Callable[[], str], password: str, slot_name: str | None, room_url: str | None,
                 tracked: set[str], datapackage, publish: Callable[[dict], None],
                 bk_of: Callable[[str], bool | None], room_sleeping: Callable[[], bool] = lambda: False,
                 root: Path = ROOT_DIR, overrides_path: Path = OVERRIDES_PATH,
                 fetch: Callable[[str], dict] = catchup.fetch_json,
                 fetch_room: Callable[[str], RoomInfo] = lambda url: room.fetch_room(url, 15.0, False),
                 listener_factory: Callable[..., RoomListener] = RoomListener,
                 poll_interval: float = 300.0, sleeping_interval: float = 600.0, static_interval: float = 1800.0,
                 heartbeat: float = 60.0, flush_delay: float = 0.5, state_throttle: float = 2.0,
                 reconnect_delays: tuple[float, float] = (2.0, 60.0)) -> None
    def start(self) -> None                   # creates its tasks and returns (Service._start_trackers is sync)
    async def stop(self) -> None
    async def poll_now(self) -> None          # one tracker (+ static if due) poll and merge; used by tests
    def status(self) -> dict                   # GET /api/roomfeed (see spec)
    def summary(self) -> dict                  # GET /api/roomfeed/summary
    def checks(self, limit: int = 50, offset: int = 0, player: str | None = None, slot: str | None = None,
               game: str | None = None) -> dict   # {"total", "offset", "items": [...]}
    def activity(self, bucket: str = "hour", player: str | None = None, now: float | None = None) -> dict
```

Behaviour:
- **Slots table.** Slot id → `{"name", "game"}` from the listener's `players` when connected, else from
  `room_status` players (index + 1 = slot id), refreshed with the static poll. Player of a slot from
  `group_players(names, load_overrides(overrides_path))` (recomputed when the slot table changes and on each static
  poll so file edits apply without restart). `me` = player owning any slot whose name is in `tracked`.
- **Seed and log.** On start, if `room_url`: `seed_for_room(room id)` → `log.open_seed(seed)` right away. When the
  listener reports `seed_name` (on_session): `log.open_seed(seed)` + `remember_room(room id, seed)`. Catch-up
  merges are skipped (state says `"en attente du seed"`) until a seed is open.
- **Live checks.** `on_check` → `CheckEntry(src="live", at=at, after=None, before=None, recorded_at=at, …)`,
  `log.add(entry, names)` (names from `datapackage.item_name/location_name` with the receiver's game for the item and
  the sender's game for the location, player names/games from the slot table), `presence.check(sender, at)`;
  if added, queue for the SSE batch.
- **Heartbeat.** While listening, every `heartbeat` seconds `log.save_state(last_live_at=now)`. On listener
  disconnect (status leaves `"listening"`), record `gap_start = now`. `after` for catch-up entries =
  `gap_start` of the current gap if any; else the saved `last_live_at` from before this app start; else None.
  After a catch-up poll that happens while listening, the gap is closed (`gap_start = None`) only once a poll
  *started after* the reconnection has completed (the API lags: keep the window open one poll longer — document
  this in a comment).
- **Polls.** Need `room_url`: tracker id from `fetch_room(room_url).tracker` (cached, refreshed on failure),
  `api_urls`, `fetch` in `asyncio.to_thread`. Schedule: on start, on every listener session (`on_session`), then
  every `poll_interval` (`sleeping_interval` when `room_sleeping()`); static on start then every `static_interval`.
  Errors → `poll_error` (string, shown in status), next attempt at the normal interval (no tight loop). Store the
  last `TrackerSnapshot`/`StaticInfo` for the summary. Without `room_url`: `catchup_available = False`, no HTTP.
- **Presence.** `Presence(tracked ids)`; `on_session` → `session_start(listener.statuses)` once the statuses
  arrive (call it from `on_status` the first time after a session, or simply on the first `Retrieved`); wire
  `on_join`/`on_part`/`on_status`.
- **status()**: `{"enabled": True, "state": "starting"|"listening"|"disconnected"|"error", "error",
  "seed", "listening_since", "last_poll_at", "poll_error", "catchup_available", "unreadable_lines", "dir",
  "write_error"}` (`dir` relative to the repo root when possible).
- **summary()**: per spec; `done`/`total` from the snapshot/static (fallback: live+catch-up counts per sender for
  `done`, 0 for `total`); `goal` = status 30; `bk` = `bk_of(name)` for tracked slots else None; players sorted by
  `done/total` desc then name; `playing` counts slots whose presence is `"playing"`.
- **checks()**: newest first by `CheckEntry.when`; filters: `player` (sender's player), `slot` (sender name),
  `game` (sender game); item JSON: `{"key": "<sender>:<location>", "at", "after", "before", "src", "sender",
  "sender_game", "sender_player", "receiver", "receiver_game", "receiver_player", "item", "location",
  "category": "PROG"|"UTILE"|"PIÈGE"|null (flags 1/2/4, progression first), "mine": receiver in tracked,
  "self": sender == receiver}`. Names are resolved at read time (ids are the truth).
- **activity()**: `bucket="hour"` → 48 buckets ending at the current local hour; `"day"` → 30 buckets ending today
  (local midnight boundaries via `time.localtime`/`time.mktime`). Entry time: `at`; else window midpoint if
  `after` is set and `before - after <= 7200`; else counted in `undated`. Each bucket `{"start", "count",
  "by_player": {player: count}}`; `player` filter keeps only that player's sent checks.
- **SSE.** Queue added entries; flush after `flush_delay` as `{"type": "roomfeed_check", "checks": [items as in
  checks()]}`; status/summary changes → `{"type": "roomfeed", "status": status()}` at most every
  `state_throttle` seconds (trailing call guaranteed).
- **Isolation.** Every task body wrapped so an exception is logged and the loop continues; `stop()` cancels all
  tasks, stops the listener, flushes nothing pending to SSE.
- **Service.** In `Service.__init__`: `self.roomfeed: RoomFeed | None = None`. In `_start_trackers` (after the
  trackers): if `self.config.room_dashboard`: build the feed with `server=lambda: self.current_server`,
  `password=self.config.password`, `slot_name=self.config.slots[0].name if self.config.slots else None`,
  `room_url=self.config.room_url`, `tracked={s.name for s in self.config.slots}`,
  `datapackage=self.datapackage`, `publish=self._broadcast`, `bk_of=self._bk_of`,
  `room_sleeping=lambda: self.room_sleeping`, then `feed.start()`. In `_stop_trackers`: `await self.roomfeed.stop()` first,
  then `self.roomfeed = None`. With no slot configured: the feed still polls HTTP (summary works) and its status
  says `"aucun slot configuré pour écouter"`. `_bk_of(name)`: summary-based — logic state `"ok"`, count 0, not
  goal, remaining > 0 → True; slot not tracked → None; else False.

- [ ] **Step 1: Unit tests (`test_roomfeed_feed.py`)** with a fake listener factory (an object exposing the
  attributes above and letting the test call the callbacks), fake `fetch`/`fetch_room`, tmp root:
  live check → written + SSE batch event; duplicate (same key via catch-up afterwards) → not written;
  catch-up before any session with no saved state → `after=None`; with saved `last_live_at=100` → `after=100`;
  gap window after a disconnect; poll error → `poll_error` set and no exception; `room_url=None` → no fetch calls,
  `catchup_available False`; summary grouping/me/bk/sort; checks filters + order; activity buckets (hour/day,
  midpoint rule, undated); `stop()` leaves no running task.
- [ ] **Step 2: Live catch-up test (Test C in `test_roomfeed_live.py`)**: run a `RoomFeed` against the local server
  with `room_url="https://archipelago.gg/room/AAAAAAAAAAAA"`, a fake
  `fetch_room` returning a `RoomInfo` with `tracker="BBBBBBBBBBBB"`, and a fake `fetch` that builds the tracker
  payload from the **server's state as seen by read-only `SlotTracker`s** (connect one `SlotTracker` per slot of
  multi5 with `password="test"`; `player_items_received` = each tracker's `state.items` as
  `[item, location, player, flags]`; `player_checks_done` = `state.checked`). Scenario: feed listening; bot checks
  3 locations (live); stop the feed; bot checks 4 more; start a new feed on the same root → after its first poll,
  the log holds exactly the 7 checks once each, the 4 missed ones with `src == "catchup"`, `after` = the old
  feed's last heartbeat (use `heartbeat=0.2`), `before` = poll time.
- [ ] **Step 3: Implement, run until green:** `scripts/test.sh -q tests/test_roomfeed_feed.py
  tests/test_roomfeed_live.py`, then the whole backend suite `scripts/test.sh -q` must still pass (it is long;
  run it once at the end of the task).
- [ ] **Step 4: Commit** `git commit -m "Roomfeed: orchestrator (live + catch-up + presence + stats), wired into the service"`.

---

### Task 8: API endpoints and SSE

**Files:**
- Modify: `backend/multitracker/api.py`
- Modify: `docs/API.md`
- Test: `tests/test_roomfeed_api.py`

**Interfaces:**
- Produces: `GET /api/roomfeed` (always 200: `feed.status()` or `{"enabled": false}`), `GET /api/roomfeed/summary`,
  `GET /api/roomfeed/checks?limit=50&offset=0&player=&slot=&game=` (limit clamped 1–500, offset ≥ 0),
  `GET /api/roomfeed/activity?bucket=hour|day&player=` (400 on another bucket). The last three: 404
  `"tableau de bord de la room désactivé"` when `service.roomfeed is None`. SSE events `roomfeed_check` and
  `roomfeed` pass through the existing `/api/events` loop unchanged (they are broadcast events).
- [ ] **Step 1: Tests** with the app factory and a fake service object (see how existing API tests build one —
  e.g. `tests/test_config_m9.py`) whose `roomfeed` is either None or a stub returning canned dicts: 404s when
  disabled, `enabled: false`, limit clamping, bad bucket 400, params forwarded.
- [ ] **Step 2: Implement** (sync handlers reading in-memory data are fine; no disk I/O in handlers).
- [ ] **Step 3: Document** a new `docs/API.md` section « Tableau de bord de la room complète » (French): the four
  endpoints with example JSON, the two SSE events, the files written (`data/room_feed/…`), the off-by-default flag,
  and the "no replay → catch-up" rule.
- [ ] **Step 4: Run** `scripts/test.sh -q tests/test_roomfeed_api.py`, **commit**
  `git commit -m "API: room-wide dashboard endpoints"`.

---

### Task 9: Front plumbing — types, API, mock, config toggle, menu entry, `#room` view

**Files:**
- Modify: `frontend/src/lib/types.ts`, `frontend/src/lib/api.ts`, `frontend/src/lib/config.ts`,
  `frontend/src/components/ConfigView.vue`, `frontend/src/stores/tracker.ts`, `frontend/src/v2/AppV2.vue`,
  `frontend/src/v2/components/MoreMenu.vue`, `frontend/src/v2/components/BottomNav.vue` (only if it lists views),
  `frontend/src/mock/fixtures.ts`, `frontend/src/mock/install.ts`
- Create: `frontend/src/v2/lib/roomfeed.ts`, `frontend/src/v2/views/RoomV2.vue` (placeholder section with the title
  « Room complète » and the disabled message; Tasks 10–11 fill it)
- Test: `frontend/tests/v2/roomfeed.test.ts`, extend the config tests (`frontend/tests/config*.test.ts` — find the
  one testing `buildPutBody`)

**Interfaces:**
- Produces (TypeScript, in `types.ts`): `RoomFeedStatus`, `RoomFeedSummary` (`room`, `players[]` with `slots[]`),
  `RoomFeedCheck`, `RoomFeedChecksPage` (`total`, `offset`, `items`), `RoomFeedActivity` (`bucket`, `buckets[]` with
  `start`, `count`, `by_player`, plus `undated`) mirroring the spec/Task 7 JSON exactly; `ConfigResponse.room_dashboard?:
  boolean`, `PutConfigBody.room_dashboard?: boolean`, `SlotsResponse.room_dashboard?: boolean`.
- `api.ts`: `getRoomFeed()`, `getRoomFeedSummary()`, `getRoomFeedChecks(params)`, `getRoomFeedActivity(bucket,
  player?)`, each with a `MockApi` optional hook like `history?`.
- `config.ts`: `buildPutBody` gains `roomDashboard?: boolean` → `room_dashboard`.
- `stores/tracker.ts`: `tracker.roomDashboard: boolean` (from `/api/slots` both places it is read);
  `View` gains `'room'`; `viewFromHash` maps `#room`; SSE listeners `roomfeed_check` and `roomfeed` forward the
  parsed data to `roomfeedBus` (imported from `../v2/lib/roomfeed` would create a v1→v2 import; instead export
  `export const roomfeedListeners = { check: new Set<(d: any) => void>(), state: new Set<(d: any) => void>() }`
  from `stores/tracker.ts` and let `v2/lib/roomfeed.ts` register into it).
- `v2/lib/roomfeed.ts`: `useRoomFeed()` composable → `{ status, summary, loading, error, refresh }` (fetch status +
  summary on mount and on every `roomfeed` event, debounced 1 s; unregister on unmount) and
  `onRoomCheck(fn)` helper (register/unregister into `roomfeedListeners.check`, auto-removed on unmount).
- `ConfigView.vue`: checkbox `cfg-roomdash` « Tableau de bord de la room complète » with help text: « Ajoute une
  page « Room complète » (menu Plus de la v2) : classement, fil des checks et activité de toute la room. Une
  connexion d'écoute en plus, en lecture seule ; les checks sont écrits dans data/room_feed/. Désactivé par
  défaut. » — loaded from `c.room_dashboard`, sent in `onSave`.
- `MoreMenu.vue`: item « Room complète » (`setView('room')`) between Configuration and the separator, only when
  `tracker.roomDashboard`.
- `AppV2.vue`: `<RoomV2 v-else-if="view === 'room'" />`.
- Mock (`VITE_MOCK=1`): `room_dashboard: true` in the mock slots response; fixtures for the four endpoints
  (≈ 30 slots in 6 players incl. a « toi » player with 3 slots, one BK slot, presence mix, 300 checks over 3 days
  with 20 catch-up entries of which 5 without window, honouring `limit/offset/player/game`, activity for hour and
  day).
- [ ] **Step 1: Tests**: `buildPutBody({... roomDashboard: true})` → `room_dashboard: true`, omitted → absent;
  `MoreMenu` shows « Room complète » only when `tracker.roomDashboard` (open the menu like existing v2 tests do, or
  test the computed condition if the dropdown portal is awkward in happy-dom); `#room` → `tracker.view === 'room'`;
  `useRoomFeed` refetches after a `roomfeed` event (fake timers).
- [ ] **Step 2: Implement**, `npm test`, `npm run build`.
- [ ] **Step 3: Commit** `git commit -m "v2: room dashboard plumbing (config toggle, menu entry, #room, API client, mock)"`.

---

### Task 10: Room page — header, who is playing, leaderboard

**Files:**
- Modify: `frontend/src/v2/views/RoomV2.vue`
- Create: `frontend/src/v2/components/room/RoomHeader.vue`, `RoomPlaying.vue`, `RoomLeaderboard.vue`
- Test: `frontend/tests/v2/room.test.ts`

Content (French UI, spec « Interface »):
- `RoomV2`: if `!tracker.roomDashboard` → card « Le tableau de bord de la room complète est désactivé. » + button
  « Ouvrir la configuration » (`setView('config')`). Else sections in order: header, « En jeu maintenant »,
  « Classement », then (Task 11) « Activité » and « Fil des checks ». Desktop ≥ 1100 px: header full width, then a
  two-column grid `[minmax(0,1fr)_minmax(0,1fr)]` (leaderboard | activity+feed); below: one column.
- `RoomHeader`: state line (« En écoute depuis 14:02 » / « Déconnecté — les checks manqués seront rattrapés » /
  « Démarrage… » / error in `bg-warn text-warn-foreground`), « Dernier relevé 14:05 » or « Rattrapage indisponible
  sans lien de room », `poll_error`/`write_error` if any; totals: `done / total` checks with %, `goals / slots`
  buts, `playing` en jeu. A help line: « « En jeu » : client de jeu connecté ou check il y a moins de 10 min. Les
  checks faits pendant une coupure sont rattrapés depuis le site, à la minute près ou sans heure. »
- `RoomPlaying`: chips `player · game` for slots with presence `playing` (then `connected` in muted style),
  sorted by player; empty → « Personne pour l'instant. »
- `RoomLeaderboard`: table (desktop) / list (phone) of players: rank, player (« toi » badge for `me`), `done /
  total`, %, a thin progress bar (`bg-done`), buts `n/m`, a dot if any slot playing. Sort toggle « % » / « Checks »
  (aria-pressed buttons). Row click/Enter toggles an expanded list of the player's slots: game, slot name,
  `done / total`, ✓ if goal, BK badge if `bk === true` (same badge style as `BigNumber`), presence text. Use
  `min-w-0`, `truncate` + `title` on names.
- [ ] **Step 1: Tests** (mount with mocked API hooks): disabled message; header texts for listening/disconnected;
  leaderboard order by % then by checks after toggling; « toi » badge; expanding a player lists its slots with ✓
  and BK; playing chips.
- [ ] **Step 2: Implement**, `npm test`, `npm run build`.
- [ ] **Step 3: Commit** `git commit -m "v2: room page header, who is playing, leaderboard"`.

---

### Task 11: Room page — live feed and activity chart

**Files:**
- Create: `frontend/src/v2/components/room/RoomFeedList.vue`, `RoomActivity.vue`
- Modify: `frontend/src/v2/views/RoomV2.vue`
- Test: extend `frontend/tests/v2/room.test.ts`

Content:
- `RoomFeedList`: filters « Joueur » / « Jeu » selects (options from the summary), pages of 50 from
  `getRoomFeedChecks`, auto-loading the next page near the end exactly like `HistoryV2.vue` (window virtualizer from
  `@tanstack/vue-virtual`, `measureElement`, `scrollMargin` re-measured with `useResizeObserver`, fallback button
  « Afficher plus »). Row: time (`hh:mm`, or « ~hh:mm » for a window ≤ 2 h, or « — »), sender player · game
  (bold), location (mono), category badge (`CATEGORY_CLASS`), item, « pour toi » (highlighted `text-logic`) or
  « pour <receiver_player> · <receiver_game> » or « pour lui-même » when `self`; catch-up rows add a muted
  « rattrapé · entre 14:02 et 14:20 » or « rattrapé · heure inconnue ». Live: `onRoomCheck` prepends incoming
  checks that match the current filters (dedup by `key`) and bumps `total`. Day headings like the History page
  (reuse `groupByDay`/`dayLabel` from `v2/lib/days.ts`; undated rows under « Heure inconnue »).
- `RoomActivity`: toggle « 48 h » / « 30 jours » and a « Joueur » select (« toute la room » + players); SVG bar chart
  (`viewBox` width = buckets × 10, bars `fill="currentColor"` in `text-logic`, height scaled to the max, `<title>`
  per bar « 14:00 · 23 checks »), x labels every 6 h / 5 days (`text-[10px]` muted), max value label, and « N
  checks sans heure » under the chart when `undated > 0`. Width 100 % (`preserveAspectRatio="none"` on the bars
  group only, labels in HTML below to avoid stretched text). Refetch on `roomfeed` events (debounced by
  `useRoomFeed`) and when toggles change.
- [ ] **Step 1: Tests**: feed renders rows with category, « pour toi », catch-up mentions; filter change refetches
  with `player`/`game`; a live check is prepended once (twice emitted → once shown); activity renders one bar per
  bucket with titles, the undated line, and refetches on toggle.
- [ ] **Step 2: Implement**, `npm test`, `npm run build`.
- [ ] **Step 3: Commit** `git commit -m "v2: room page live feed and activity chart"`.

---

### Task 12 (controller): docs, activation for Romain, verification on the real room

Done by the controller, not a subagent:
- `DECISIONS.md` D22 (listener + HTTP catch-up, JSONL files, off by default, presence limits), `BACKLOG.md` M21
  (done items + « Nettoyage des fichiers », « BK des autres joueurs », « Page v1 »), `PROGRESS.md`, `CLAUDE.md`
  (one line: roomfeed module, `data/room_feed/`, port 38283 now used by `test_roomfeed_live.py`).
- Read-only checks of the real API format (`/api/room_status`, `/api/tracker`, `/api/static_tracker`) against
  `parse_tracker`/`parse_static`.
- `config/room_players.yaml` with `balatrom: romain`; `PUT /api/config` with `room_dashboard: true`; watch
  `/api/roomfeed` reach `listening`, a catch-up merge of the existing ≈ 8000 checks, then the page in Firefox
  (desktop + phone, both themes) with screenshots.
- Push.
