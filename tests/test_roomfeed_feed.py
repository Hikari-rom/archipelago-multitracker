import asyncio
import json
import time
from pathlib import Path

import pytest

from multitracker.room import RoomError, RoomInfo
from multitracker.roomfeed.feed import RoomFeed
from multitracker.roomfeed.log import CheckEntry, RoomLog

ROOM_URL = "https://archipelago.gg/room/AAAAAAAAAAAA"
TRACKER = "BBBBBBBBBBBB"
PLAYERS = {1: {"name": "romain_a", "game": "GameA"}, 2: {"name": "romain_b", "game": "GameB"},
           3: {"name": "bob", "game": "GameA"}, 4: {"name": "bobby_z", "game": "GameB"}}
PROG, USEFUL, TRAP = 1, 2, 4


class FakeDatapackage:
    def names(self, game):
        return object() if game in ("GameA", "GameB") else None

    def item_name(self, game, item):
        return f"{game}/item{item}"

    def location_name(self, game, location):
        return f"{game}/loc{location}"


class FakeListener:
    """Stands in for RoomListener: the test fires the callbacks it was given."""

    def __init__(self, **kwargs):
        self.kw = kwargs
        self.status, self.error, self.seed_name, self.team, self.slot = "connecting", None, None, None, None
        self.players, self.listening_since, self.statuses = {}, None, {}
        self.started = self.stopped = False

    def start(self):
        self.started = True

    async def stop(self):
        self.stopped = True

    def session(self, seed="SEED1", players=PLAYERS):
        self.status, self.seed_name, self.team, self.slot = "listening", seed, 0, 1
        self.players, self.listening_since, self.statuses = dict(players), time.time(), {}
        self.kw["on_session"](self)
        self.kw["on_state"](self)

    def drop(self, status="disconnected", error="gone"):
        self.status, self.error = status, error
        self.kw["on_state"](self)

    def send_status(self, slot, value):
        self.statuses[slot] = value
        self.kw["on_status"](slot, value)

    def check(self, sender, receiver, item, location, flags=0, at=None):
        self.kw["on_check"](sender, receiver, item, location, flags, time.time() if at is None else at)


def payload(received=None, done=None, status=None):
    """A WebHost tracker payload: received = {receiver: [(item, location, sender, flags)]}."""
    return {"player_items_received": [{"team": 0, "player": p, "items": [list(i) for i in items]}
                                      for p, items in (received or {}).items()],
            "player_checks_done": [{"team": 0, "player": p, "locations": list(range(n))}
                                   for p, n in (done or {}).items()],
            "player_status": [{"team": 0, "player": p, "status": s} for p, s in (status or {}).items()],
            "activity_timers": [], "total_checks_done": [{"team": 0, "checks_done": sum((done or {}).values())}]}


STATIC = {"player_locations_total": [{"team": 0, "player": 1, "total_locations": 10},
                                     {"team": 0, "player": 2, "total_locations": 20},
                                     {"team": 0, "player": 3, "total_locations": 10},
                                     {"team": 0, "player": 4, "total_locations": 40}],
          "player_game": [{"team": 0, "player": 1, "game": "GameA"}]}


class Env:
    """A RoomFeed wired to fakes. `tracker_data` is what the fake tracker API answers."""

    def __init__(self, tmp_path: Path, **overrides):
        self.root = tmp_path / "room_feed"
        self.published: list[dict] = []
        self.fetched: list[str] = []
        self.tracker_data = payload()
        self.static_data = STATIC
        self.fetch_error: Exception | None = None
        self.room_fetches = 0
        self.listeners: list[FakeListener] = []
        self.bk = {"romain_a": True}
        kwargs = dict(server=lambda: "127.0.0.1:1", password="pw", slot_name="romain_a", room_url=ROOM_URL,
                      tracked={"romain_a"}, datapackage=FakeDatapackage(), publish=self.published.append,
                      bk_of=lambda name: self.bk.get(name), root=self.root, overrides_path=tmp_path / "players.yaml",
                      fetch=self.fetch, fetch_room=self.fetch_room, listener_factory=self.make_listener,
                      poll_interval=3600, sleeping_interval=3600, static_interval=3600, heartbeat=3600,
                      flush_delay=0.02, state_throttle=0.05)
        kwargs.update(overrides)
        self.feed = RoomFeed(**kwargs)

    @property
    def listener(self) -> FakeListener:
        return self.listeners[-1]

    def make_listener(self, **kwargs):
        listener = FakeListener(**kwargs)
        self.listeners.append(listener)
        return listener

    def fetch(self, url):
        self.fetched.append(url)
        if self.fetch_error is not None:
            raise self.fetch_error
        return self.static_data if "static_tracker" in url else self.tracker_data

    def fetch_room(self, url):
        self.room_fetches += 1
        return RoomInfo(url=url, host="archipelago.gg", port=1234, tracker=TRACKER,
                        players=[(p["name"], p["game"]) for p in PLAYERS.values()])

    def events(self, kind):
        return [e for e in self.published if e["type"] == kind]

    def lines(self, pattern="checks-*.jsonl"):
        out = []
        for path in sorted((self.root / "SEED1").glob(pattern)):
            out += [json.loads(line) for line in path.read_text().splitlines() if line]
        return out

    def log_state(self) -> dict:
        log = RoomLog(self.root)
        log.open_seed("SEED1")
        return log.load_state()

    def presence_rows(self) -> list[dict]:
        path = self.root / "SEED1" / "presence.jsonl"
        return [json.loads(line) for line in path.read_text().splitlines() if line]

    def preset_seed(self, last_live_at=None):
        log = RoomLog(self.root)
        log.remember_room("AAAAAAAAAAAA", "SEED1")
        if last_live_at is not None:
            log.open_seed("SEED1")
            log.save_state(last_live_at=last_live_at)


async def until(predicate, timeout=3.0):
    deadline = asyncio.get_running_loop().time() + timeout
    while asyncio.get_running_loop().time() < deadline:
        if predicate():
            return
        await asyncio.sleep(0.01)
    raise AssertionError("timed out")


@pytest.fixture
def env(tmp_path):
    def make(**overrides):
        return Env(tmp_path, **overrides)  # every test stops its own feed

    return make


async def started(e: Env, poll_loop: bool = False) -> Env:
    """Start the feed. By default its poll loop is cancelled so the test drives the polls with poll_now()."""
    e.feed.start()
    if not poll_loop:
        task = e.feed._tasks[0]
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)
    return e


def local(*ymdhm):
    y, mo, d, h, mi = ymdhm
    return time.mktime((y, mo, d, h, mi, 0, 0, 0, -1))


# -- live checks ---------------------------------------------------------------------------------------------
async def test_live_check_is_written_and_published_in_a_batch(env):
    e = env()
    await started(e)
    try:
        e.listener.session()
        e.listener.check(1, 3, 77, 501, PROG, at=1000.0)
        e.listener.check(3, 1, 78, 502, 0, at=1001.0)
        await until(lambda: e.events("roomfeed_check"))
        rows = e.lines()
        assert [(r["sender"], r["location"], r["src"], r["at"], r["after"], r["before"]) for r in rows] == \
            [(1, 501, "live", 1000.0, None, None), (3, 502, "live", 1001.0, None, None)]
        assert rows[0]["sender_name"] == "romain_a" and rows[0]["item_name"] == "GameA/item77"
        assert rows[0]["location_name"] == "GameA/loc501" and rows[0]["receiver_game"] == "GameA"
        batch = e.events("roomfeed_check")
        assert len(batch) == 1 and [c["key"] for c in batch[0]["checks"]] == ["3:502", "1:501"]  # newest first
        first = batch[0]["checks"][1]
        assert first["sender"] == "romain_a" and first["receiver"] == "bob" and first["item"] == "GameA/item77"
        assert first["location"] == "GameA/loc501" and first["category"] == "PROG" and first["src"] == "live"
    finally:
        await e.feed.stop()


async def test_unknown_names_are_null(env):
    e = env()
    await started(e)
    try:
        e.listener.session(players={1: {"name": "romain_a", "game": "Mystery"}})
        e.listener.check(1, 9, 5, 6, 0, at=10.0)
        item = e.feed.checks()["items"][0]
        assert item["sender"] == "romain_a" and item["item"] is None and item["location"] is None
        assert item["receiver"] is None and item["receiver_game"] is None and item["key"] == "1:6"
        assert e.lines()[0]["receiver_name"] is None and e.lines()[0]["item_name"] is None
    finally:
        await e.feed.stop()


async def test_duplicates_are_not_written_twice(env):
    e = env()
    e.preset_seed()
    await started(e)
    try:
        e.listener.session()
        e.listener.check(1, 3, 77, 501, 0, at=1000.0)
        e.tracker_data = payload(received={3: [(77, 501, 1, 0)], 1: [(80, 600, 3, 0)]})
        await e.feed.poll_now()
        e.listener.check(3, 1, 80, 600, 0, at=2000.0)  # already caught up: the live copy is dropped
        e.listener.check(1, 3, 77, 501, 0, at=2001.0)
        rows = e.lines()
        assert sorted((r["sender"], r["location"], r["src"]) for r in rows) == [(1, 501, "live"), (3, 600, "catchup")]
        await until(lambda: e.events("roomfeed_check"))
        await asyncio.sleep(0.1)
        batches = e.events("roomfeed_check")  # the live check only: a history import is not news
        assert [[c["key"] for c in b["checks"]] for b in batches] == [["1:501"]]
    finally:
        await e.feed.stop()


# -- catch-up --------------------------------------------------------------------------------------------------
async def test_catchup_without_saved_state_has_no_after(env):
    e = env()
    e.preset_seed()
    await started(e)
    try:
        e.tracker_data = payload(received={3: [(77, 501, 1, PROG)]})
        before = time.time()
        await e.feed.poll_now()
        (row,) = e.lines()
        assert (row["src"], row["at"], row["after"], row["sender"], row["receiver"]) == ("catchup", None, None, 1, 3)
        assert before <= row["before"] <= time.time() and row["recorded_at"] == row["before"]
        assert e.fetched[0].endswith(f"/api/static_tracker/{TRACKER}") and e.fetched[1].endswith(f"/api/tracker/{TRACKER}")
        assert e.events("roomfeed_check") == []  # a history import is not news
    finally:
        await e.feed.stop()


async def test_catchup_after_is_the_saved_last_live_at(env):
    e = env()
    e.preset_seed(last_live_at=100.0)
    await started(e)
    try:
        e.tracker_data = payload(received={3: [(77, 501, 1, 0)]})
        await e.feed.poll_now()
        (row,) = e.lines()
        assert row["after"] == 100.0 and row["before"] > 100.0
        await until(lambda: e.events("roomfeed_check"))  # a dated window is news
    finally:
        await e.feed.stop()


async def test_gap_window_opens_on_disconnect_and_closes_after_two_polls(env):
    e = env()
    e.preset_seed(last_live_at=100.0)
    await started(e)
    try:
        e.listener.session()
        e.listener.drop()
        gap = time.time()
        await asyncio.sleep(0.02)
        e.tracker_data = payload(received={3: [(1, 1, 1, 0)]})
        await e.feed.poll_now()  # gap open: the earliest of the old heartbeat and the drop (the app was down before)
        assert e.lines()[-1]["after"] == 100.0
        assert e.log_state()["last_live_at"] == pytest.approx(gap, abs=0.5)
        e.listener.session()
        await asyncio.sleep(0.02)
        e.tracker_data = payload(received={3: [(1, 1, 1, 0), (2, 2, 1, 0)]})
        await e.feed.poll_now()  # first poll after the reconnection: the API lags, the window stays open
        assert e.lines()[-1]["location"] == 2 and e.lines()[-1]["after"] == 100.0
        e.tracker_data = payload(received={3: [(1, 1, 1, 0), (2, 2, 1, 0), (3, 3, 1, 0)]})
        await e.feed.poll_now()  # second one: still merged with the window, which closes afterwards
        assert e.lines()[-1]["location"] == 3 and e.lines()[-1]["after"] == 100.0
        e.tracker_data = payload(received={3: [(1, 1, 1, 0), (2, 2, 1, 0), (3, 3, 1, 0), (4, 4, 1, 0)]})
        await e.feed.poll_now()
        assert e.lines()[-1]["location"] == 4 and e.lines()[-1]["after"] is None
    finally:
        await e.feed.stop()


async def test_gap_window_without_a_prior_run_starts_at_the_drop(env):
    e = env()
    e.preset_seed()
    await started(e)
    try:
        e.listener.session()
        e.listener.drop()
        gap = time.time()
        e.tracker_data = payload(received={3: [(1, 1, 1, 0)]})
        await e.feed.poll_now()
        assert e.lines()[-1]["after"] == pytest.approx(gap, abs=0.5)
    finally:
        await e.feed.stop()


async def test_poll_started_before_the_reconnection_does_not_count(env):
    e = env()
    e.preset_seed()
    await started(e)
    try:
        e.listener.session()
        e.listener.drop()
        gate = asyncio.Event()
        loop = asyncio.get_running_loop()
        original = e.fetch

        def slow(url):
            if "static_tracker" not in url:
                asyncio.run_coroutine_threadsafe(gate.wait(), loop).result(5)
            return original(url)

        e.feed._fetch = slow
        e.tracker_data = payload(received={3: [(1, 1, 1, 0)]})
        poll = asyncio.create_task(e.feed.poll_now())
        await asyncio.sleep(0.05)
        e.listener.session()  # reconnects while the poll is in flight
        gate.set()
        await poll
        assert e.feed._polls_since_reconnect == 0 and e.feed._gap_start is not None
    finally:
        await e.feed.stop()


async def test_poll_error_is_reported_and_does_not_raise(env):
    e = env()
    e.preset_seed()
    await started(e)
    try:
        e.fetch_error = RoomError("le site a répondu 502")
        await e.feed.poll_now()
        assert e.feed.status()["poll_error"] == "le site a répondu 502"
        assert e.feed.status()["last_poll_at"] is None
        e.fetch_error = None
        await e.feed.poll_now()
        assert e.feed.status()["poll_error"] is None and e.feed.status()["last_poll_at"] is not None
    finally:
        await e.feed.stop()


async def test_poll_loop_survives_errors_and_polls_on_session(env):
    e = env(poll_interval=3600)
    e.preset_seed()
    e.fetch_error = RuntimeError("boom")
    await started(e, poll_loop=True)
    try:
        await until(lambda: e.feed.status()["poll_error"] is not None)
        assert e.feed.status()["poll_error"] == "RuntimeError: boom"
        assert all(not t.done() for t in e.feed._tasks)
        e.fetch_error = None
        e.tracker_data = payload(received={3: [(1, 1, 1, 0)]})
        e.listener.session()  # a new session wakes the poll loop up
        await until(lambda: e.lines())
        assert e.feed.status()["poll_error"] is None
    finally:
        await e.feed.stop()


async def test_no_room_url_means_no_http(env):
    e = env(room_url=None)
    await started(e)
    try:
        await e.feed.poll_now()
        await asyncio.sleep(0.05)
        assert e.fetched == [] and e.room_fetches == 0
        assert e.feed.status()["catchup_available"] is False and e.feed.status()["poll_error"] is None
        e.listener.session()
        e.listener.check(1, 3, 77, 501, 0, at=5.0)
        assert len(e.lines()) == 1  # live listening still works
        assert e.feed.summary()["room"]["slots"] == 4
    finally:
        await e.feed.stop()


async def test_catchup_waits_for_the_seed(env):
    e = env()
    await started(e)  # no remembered seed for the room
    try:
        e.tracker_data = payload(received={3: [(1, 1, 1, 0)]})
        await e.feed.poll_now()
        assert e.lines() == [] and e.feed.status()["poll_error"] == "en attente du seed"
        e.listener.session()
        await e.feed.poll_now()
        assert len(e.lines()) == 1 and e.feed.status()["poll_error"] is None
        assert RoomLog(e.root).seed_for_room("AAAAAAAAAAAA") == "SEED1"
    finally:
        await e.feed.stop()


async def test_tracker_id_is_cached_and_looked_up_again_after_a_failure(env):
    e = env()
    e.preset_seed()
    await started(e)
    try:
        await e.feed.poll_now()
        await e.feed.poll_now()
        assert e.room_fetches == 1
        e.fetch_error = RoomError("down")
        await e.feed.poll_now()
        e.fetch_error = None
        await e.feed.poll_now()
        assert e.room_fetches == 2
    finally:
        await e.feed.stop()


# -- status, heartbeat, presence -------------------------------------------------------------------------------------
async def test_status_states(env):
    e = env()
    await started(e)
    try:
        s = e.feed.status()
        assert s["enabled"] is True and s["state"] == "starting" and s["seed"] is None and s["catchup_available"]
        assert s["dir"] is None and s["write_error"] is None and s["unreadable_lines"] == 0
        e.listener.session()
        s = e.feed.status()
        assert s["state"] == "listening" and s["seed"] == "SEED1" and s["listening_since"] == e.listener.listening_since
        assert s["dir"].endswith("SEED1")
        e.listener.drop()
        s = e.feed.status()
        assert s["state"] == "disconnected" and s["error"] == "gone" and s["listening_since"] is None
        e.listener.drop("error", "connexion refusée")
        assert e.feed.status()["state"] == "error"
        e.listener.status = "connecting"
        assert e.feed.status()["state"] == "disconnected"  # was listening before
    finally:
        await e.feed.stop()


async def test_no_slot_configured(env):
    e = env(slot_name=None, tracked=set())
    e.preset_seed()
    await started(e)
    try:
        assert e.listeners == []
        s = e.feed.status()
        assert s["state"] == "error" and s["error"] == "aucun slot configuré pour écouter"
        e.tracker_data = payload(received={3: [(1, 1, 1, 0)]}, done={1: 3})
        await e.feed.poll_now()
        assert len(e.lines()) == 1 and e.feed.summary()["room"]["done"] == 3
    finally:
        await e.feed.stop()


async def test_heartbeat_saves_last_live_at_only_while_listening(env):
    e = env(heartbeat=0.05)
    e.preset_seed(last_live_at=5.0)
    await started(e)
    try:
        await asyncio.sleep(0.2)
        assert e.log_state()["last_live_at"] == 5.0  # not listening: untouched
        e.listener.session()
        await until(lambda: e.log_state()["last_live_at"] > 5.0)
        beat = e.log_state()["last_live_at"]
        assert e.log_state()["listening_since"] == e.listener.listening_since
        e.listener.drop()
        gap = e.log_state()["last_live_at"]
        assert gap >= beat
        await asyncio.sleep(0.2)
        assert e.log_state()["last_live_at"] == gap
    finally:
        await e.feed.stop()


async def test_clean_stop_records_the_gap_start(env):
    e = env()
    e.preset_seed(last_live_at=5.0)
    await started(e)
    e.listener.session()
    await e.feed.stop()
    assert e.log_state()["last_live_at"] > 5.0 and e.listener.stopped


async def test_presence_follows_statuses_joins_and_checks(env):
    e = env()
    await started(e)
    try:
        e.listener.session()
        summary = lambda: {s["name"]: s["presence"] for p in e.feed.summary()["players"] for s in p["slots"]}  # noqa: E731
        e.listener.send_status(1, 5)  # our own slot: its server status says nothing
        e.listener.send_status(2, 5)
        e.listener.send_status(3, 20)
        e.listener.send_status(4, 0)
        assert summary() == {"romain_a": "unknown", "romain_b": "connected", "bob": "playing", "bobby_z": "offline"}
        # the listener's own Join (Tracker tag) marks nothing
        e.listener.kw["on_join"](1, ["Tracker"])
        assert summary()["romain_a"] == "unknown"
        e.listener.kw["on_join"](4, ["AP"])
        assert summary()["bobby_z"] == "playing"
        e.listener.kw["on_part"](4)
        assert summary()["bobby_z"] == "offline"
        e.listener.check(4, 3, 1, 1, 0)  # a check in the last minutes counts as playing
        assert summary()["bobby_z"] == "playing"
        assert [r["event"] for r in e.presence_rows()] == ["join", "join", "part"]
        # a new session forgets the previous one
        e.listener.session()
        e.listener.send_status(3, 0)
        assert summary()["bob"] == "offline"
    finally:
        await e.feed.stop()


# -- views ----------------------------------------------------------------------------------------------------------
async def test_summary_groups_players_marks_me_and_sorts(env):
    e = env()
    e.preset_seed()
    await started(e)
    try:
        e.tracker_data = payload(done={1: 5, 2: 5, 3: 9, 4: 4}, status={3: 30, 2: 10},
                                 received={1: [(1, 1, 3, 0)]})
        await e.feed.poll_now()
        e.listener.session()
        summary = e.feed.summary()
        assert summary["room"] == {"done": 23, "total": 80, "slots": 4, "goals": 1, "playing": 0}
        assert [p["player"] for p in summary["players"]] == ["romain", "bob"]  # 10/30 beats 13/50
        romain, bob = summary["players"]
        assert romain["me"] is True and romain["done"] == 10 and romain["total"] == 30 and romain["goals"] == 0
        assert [s["name"] for s in romain["slots"]] == ["romain_a", "romain_b"]  # 5/10 beats 5/20
        assert romain["slots"][0] == {"name": "romain_a", "game": "GameA", "done": 5, "total": 10, "goal": False,
                                      "presence": "unknown", "last_check_at": None, "active_at": None,
                                      "bk": True}
        assert romain["slots"][1]["bk"] is None  # not tracked
        assert bob["me"] is False and bob["done"] == 13 and bob["total"] == 50 and bob["goals"] == 1
        assert [(s["name"], s["goal"], s["total"], s["bk"]) for s in bob["slots"]] == \
            [("bob", True, 10, None), ("bobby_z", False, 40, None)]
    finally:
        await e.feed.stop()


async def test_summary_sort_and_override_file(env, tmp_path):
    e = env()
    (tmp_path / "players.yaml").write_text("bobby_z: zed\n")
    e.preset_seed()
    await started(e)
    try:
        e.tracker_data = payload(done={1: 1, 2: 1, 3: 9, 4: 20})
        await e.feed.poll_now()
        players = e.feed.summary()["players"]
        assert [(p["player"], p["done"], p["total"]) for p in players] == \
            [("bob", 9, 10), ("zed", 20, 40), ("romain", 2, 30)]  # by done/total, the players file applied
    finally:
        await e.feed.stop()


async def test_summary_falls_back_to_log_counts(env):
    e = env()
    e.preset_seed()
    await started(e)
    try:
        e.listener.session()
        e.listener.check(3, 1, 1, 1, 0, at=10.0)
        e.listener.check(3, 1, 1, 2, 0, at=20.0)
        slots = {s["name"]: s for p in e.feed.summary()["players"] for s in p["slots"]}
        assert slots["bob"]["done"] == 2 and slots["bob"]["total"] == 0 and slots["bob"]["last_check_at"] == 20.0
    finally:
        await e.feed.stop()


async def test_checks_order_filters_and_paging(env):
    e = env()
    await started(e)
    try:
        e.listener.session()
        e.listener.check(1, 3, 10, 1, PROG, at=100.0)
        e.listener.check(3, 3, 11, 2, USEFUL, at=300.0)
        e.listener.check(2, 1, 12, 3, TRAP, at=200.0)
        e.listener.check(4, 2, 13, 4, 0, at=400.0)
        all_ = e.feed.checks()
        assert all_["total"] == 4 and all_["offset"] == 0
        assert [c["key"] for c in all_["items"]] == ["4:4", "3:2", "2:3", "1:1"]
        by_key = {c["key"]: c for c in all_["items"]}
        assert [by_key[k]["category"] for k in ("1:1", "3:2", "2:3", "4:4")] == ["PROG", "UTILE", "PIÈGE", None]
        assert by_key["3:2"]["self"] is True and by_key["1:1"]["self"] is False
        assert by_key["2:3"]["mine"] is True and by_key["1:1"]["mine"] is False
        assert by_key["1:1"]["sender_player"] == "romain" and by_key["1:1"]["receiver_player"] == "bob"
        assert by_key["1:1"]["sender_game"] == "GameA" and by_key["1:1"]["receiver_game"] == "GameA"
        assert [c["key"] for c in e.feed.checks(player="romain")["items"]] == ["2:3", "1:1"]
        assert [c["key"] for c in e.feed.checks(slot="bob")["items"]] == ["3:2"]
        assert [c["key"] for c in e.feed.checks(game="GameB")["items"]] == ["4:4", "2:3"]
        assert e.feed.checks(player="romain", game="GameB")["total"] == 1
        page = e.feed.checks(limit=2, offset=1)
        assert page["total"] == 4 and page["offset"] == 1 and [c["key"] for c in page["items"]] == ["3:2", "2:3"]
        assert e.feed.checks(limit=2, offset=10)["items"] == []
        assert e.feed.checks(player="nobody")["total"] == 0
    finally:
        await e.feed.stop()


async def test_checks_sort_uses_before_then_recorded_at_for_undated_ones(env):
    e = env()
    e.preset_seed()
    await started(e)
    try:
        e.listener.session()
        e.listener.check(1, 3, 1, 1, 0, at=500.0)
        e.tracker_data = payload(received={3: [(9, 9, 1, 0)]})
        await e.feed.poll_now()  # catch-up, before = now (far later than 500)
        assert [c["key"] for c in e.feed.checks()["items"]] == ["1:9", "1:1"]
        assert e.feed.checks()["items"][0]["at"] is None and e.feed.checks()["items"][0]["src"] == "catchup"
    finally:
        await e.feed.stop()


def add(e, sender, at=None, after=None, before=None, location=None, src="live"):
    location = location if location is not None else len(e.feed.log.entries) + 1
    entry = CheckEntry(recorded_at=at or before or 1.0, at=at, after=after, before=before, src=src, sender=sender,
                       receiver=3, item=1, location=location, flags=0)
    assert e.feed.log.add(entry, {})
    e.feed._index(entry)


async def test_activity_hour_buckets(env):
    e = env()
    e.preset_seed()
    await started(e)
    try:
        e.listener.session()
        now = local(2026, 10, 23, 15, 30)
        add(e, 1, at=local(2026, 10, 23, 15, 5))
        add(e, 1, at=local(2026, 10, 23, 14, 59))
        add(e, 3, at=local(2026, 10, 23, 14, 0))
        add(e, 3, at=local(2026, 10, 21, 16, 0))  # 47 hours back: first bucket
        add(e, 3, at=local(2026, 10, 21, 15, 59))  # one second too old
        add(e, 3, at=now + 7200)  # in the future: ignored
        add(e, 4, after=local(2026, 10, 23, 12, 0), before=local(2026, 10, 23, 13, 30))  # midpoint 12:45
        add(e, 4, after=local(2026, 10, 23, 9, 0), before=local(2026, 10, 23, 13, 0))  # 4 h wide: undated
        add(e, 4, before=local(2026, 10, 23, 13, 0))  # no start: undated
        result = e.feed.activity("hour", now=now)
        buckets = result["buckets"]
        assert result["bucket"] == "hour" and len(buckets) == 48 and result["undated"] == 2
        assert buckets[-1]["start"] == local(2026, 10, 23, 15, 0) and buckets[0]["start"] == local(2026, 10, 21, 16, 0)
        assert buckets[-1]["count"] == 1 and buckets[-1]["by_player"] == {"romain": 1}
        assert buckets[-2]["count"] == 2 and buckets[-2]["by_player"] == {"romain": 1, "bob": 1}
        assert buckets[-4]["start"] == local(2026, 10, 23, 12, 0) and buckets[-4]["by_player"] == {"bob": 1}
        assert buckets[0]["count"] == 1 and sum(b["count"] for b in buckets) == 5
        only = e.feed.activity("hour", player="romain", now=now)
        assert sum(b["count"] for b in only["buckets"]) == 2 and only["undated"] == 0
        assert all(set(b["by_player"]) <= {"romain"} for b in only["buckets"])
    finally:
        await e.feed.stop()


async def test_activity_day_buckets(env):
    e = env()
    e.preset_seed()
    await started(e)
    try:
        e.listener.session()
        now = local(2026, 10, 23, 15, 30)
        add(e, 1, at=local(2026, 10, 23, 0, 0))
        add(e, 1, at=local(2026, 10, 22, 23, 59))
        add(e, 3, at=local(2026, 9, 24, 0, 0))  # 29 days back: first bucket
        add(e, 3, at=local(2026, 9, 23, 23, 59))  # too old
        result = e.feed.activity("day", now=now)
        buckets = result["buckets"]
        assert len(buckets) == 30 and buckets[-1]["start"] == local(2026, 10, 23, 0, 0)
        assert buckets[0]["start"] == local(2026, 9, 24, 0, 0)
        assert buckets[-1]["count"] == 1 and buckets[-2]["count"] == 1 and buckets[0]["count"] == 1
        assert sum(b["count"] for b in buckets) == 3
        assert e.feed.activity("day")["bucket"] == "day"  # `now` defaults to the current time
    finally:
        await e.feed.stop()


# -- events and shutdown -----------------------------------------------------------------------------------------------
async def test_state_events_are_throttled_with_a_trailing_call(env):
    e = env(state_throttle=0.2)
    await started(e)
    try:
        e.listener.session()
        for i in range(5):
            e.listener.check(1, 3, 1, i + 1, 0, at=10.0 + i)
        assert len(e.events("roomfeed")) == 1  # leading call only, for now
        await until(lambda: len(e.events("roomfeed")) == 2)
        assert e.events("roomfeed")[-1]["status"]["state"] == "listening"
        await asyncio.sleep(0.4)
        assert len(e.events("roomfeed")) == 2
    finally:
        await e.feed.stop()


async def test_stop_cancels_everything_and_publishes_nothing_pending(env):
    before = set(asyncio.all_tasks())
    e = env(flush_delay=0.3)
    e.preset_seed()
    await started(e)
    e.listener.session()
    e.listener.check(1, 3, 1, 1, 0, at=1.0)
    await e.feed.stop()
    assert e.listener.stopped
    await asyncio.sleep(0.4)
    assert e.events("roomfeed_check") == []
    assert {t for t in asyncio.all_tasks() if not t.done()} <= before
    e.listener.check(1, 3, 1, 2, 0, at=2.0)  # late callbacks are ignored
    assert len(e.lines()) == 1
    await e.feed.stop()  # idempotent


async def test_overrides_file_edits_apply_on_the_next_static_poll(env, tmp_path):
    e = env()
    e.preset_seed()
    await started(e)
    try:
        e.listener.session()
        assert {p["player"] for p in e.feed.summary()["players"]} == {"romain", "bob"}
        (tmp_path / "players.yaml").write_text("bob: romain\nbobby_z: romain\n")
        e.feed._static_at = None  # static poll due
        await e.feed.poll_now()
        assert {p["player"] for p in e.feed.summary()["players"]} == {"romain"}
    finally:
        await e.feed.stop()


async def test_log_is_reloaded_from_disk(env):
    first = env()
    await started(first)
    first.listener.session()
    first.listener.check(1, 3, 1, 1, 0, at=1.0)
    await first.feed.stop()
    second = env()
    second.preset_seed()
    await started(second)
    try:
        assert second.feed.checks()["total"] == 1
        second.listener.session()
        second.listener.check(1, 3, 1, 1, 0, at=2.0)  # same key as before the restart
        assert len(second.lines()) == 1
    finally:
        await second.feed.stop()


# -- Service integration --------------------------------------------------------------------------------------------
async def test_service_starts_and_stops_the_feed_with_the_flag(tmp_path, monkeypatch):
    def no_http(*_args):
        raise RoomError("offline")

    monkeypatch.setattr("multitracker.room.fetch_room", no_http)  # neither the service nor the feed may reach the site
    from multitracker.config import RoomConfig, SlotConfig
    from multitracker.service import Service
    from multitracker.store import Store

    def config(**kw):
        return RoomConfig(server="127.0.0.1:1", password="pw", slots=[SlotConfig("romain_a", "GameA"),
                                                                       SlotConfig("romain_b", "GameB")], **kw)

    service = Service(config(), Store(tmp_path / "db.sqlite3"), reconnect_delays=(0.3, 1.0))
    await service.start()
    try:
        assert service.roomfeed is None  # off by default: nothing listens, nothing is written
        await service.reload(config(room_dashboard=True))
        feed = service.roomfeed
        assert isinstance(feed, RoomFeed) and feed.slot_name == "romain_a" and feed.tracked == {"romain_a", "romain_b"}
        assert feed.status()["enabled"] is True and feed.status()["catchup_available"] is False
        assert feed._listener is not None and feed._listener._task is not None
        await service.reload(config(room_dashboard=True, room_url=ROOM_URL))
        assert service.roomfeed is not feed and feed._stopped and service.roomfeed.status()["catchup_available"]
        await service.reload(config())
        assert service.roomfeed is None
        await service.reload(config(room_dashboard=True))
    finally:
        await service.stop()
    assert service.roomfeed is None


async def test_service_reload_reconnects_only_what_changed(tmp_path, monkeypatch):
    from multitracker.config import PLAYERS_DIR, RoomConfig, SlotConfig
    from multitracker.service import Service
    from multitracker.store import Store

    def config(*slots, password="pw", **kw):
        return RoomConfig(server="127.0.0.1:1", password=password, slots=list(slots), **kw)

    a, b, c = SlotConfig("a", "GameA"), SlotConfig("b", "GameB"), SlotConfig("c", "GameC")
    service = Service(config(a, b), Store(tmp_path / "db.sqlite3"), reconnect_delays=(0.3, 1.0))
    await service.start()
    try:
        before = dict(service.trackers)
        await service.reload(config(SlotConfig("a", "GameA"), SlotConfig("b", "GameB")))  # saved again unchanged
        assert service.trackers == before and all(service.trackers[n] is t for n, t in before.items())
        await service.reload(config(a, b, wake_room=True))  # an option the trackers do not use
        assert all(service.trackers[n] is t for n, t in before.items())
        # owner and yaml: same connection
        await service.reload(config(SlotConfig("a", "GameA", owner="Zed", yaml=PLAYERS_DIR / "x.yaml"), b))
        assert service.trackers["a"] is before["a"] and service.slot_configs["a"].owner == "Zed"
        # c added first, b removed: only those two change, in the configured order
        await service.reload(config(c, a))
        assert list(service.trackers) == ["c", "a"] and service.trackers["a"] is before["a"]
        assert before["b"]._task is None or before["b"]._task.done()
        assert "b" not in service.logic and service.logic["c"].state == "pending"
        # another game for a slot: that one reconnects
        kept_c = service.trackers["c"]
        await service.reload(config(c, SlotConfig("a", "GameZ")))
        assert service.trackers["a"] is not before["a"] and service.trackers["c"] is kept_c
        # another password: everything reconnects
        await service.reload(config(c, SlotConfig("a", "GameZ"), password="other"))
        assert service.trackers["c"] is not kept_c
    finally:
        await service.stop()


async def test_service_bk_of(tmp_path):
    from multitracker.config import RoomConfig, SlotConfig
    from multitracker.logic import LogicResult
    from multitracker.service import Service
    from multitracker.store import Store

    service = Service(RoomConfig(server="127.0.0.1:1", slots=[SlotConfig("a", "GameA"), SlotConfig("b", "GameA")]),
                      Store(tmp_path / "db.sqlite3"), reconnect_delays=(0.3, 1.0))
    await service.start()
    try:
        state = service.trackers["a"].state
        state.missing = {1, 2}
        service.logic["a"] = LogicResult("ok", in_logic=[])
        assert service._bk_of("a") is True and service._bk_of("elsewhere") is None
        service.logic["a"] = LogicResult("ok", in_logic=[1])
        assert service._bk_of("a") is False
        service.logic["a"] = LogicResult("pending")
        assert service._bk_of("a") is False
        service.logic["a"] = LogicResult("ok", in_logic=[])
        state.missing = set()
        assert service._bk_of("a") is False
        state.missing, state.client_status = {1}, 30
        assert service._bk_of("a") is False
    finally:
        await service.stop()


GROUP_PLAYERS = {**PLAYERS, 5: {"name": "Links", "game": "GameA", "type": 2}}


async def test_item_link_groups_are_not_players(env):
    e = env()
    await started(e)
    try:
        e.listener.session(players=GROUP_PLAYERS)
        e.tracker_data = payload(done={1: 1, 5: 7}, status={5: 30})
        summary = e.feed.summary()
        assert summary["room"]["slots"] == 4 and summary["room"]["done"] == 0
        assert {s["name"] for p in summary["players"] for s in p["slots"]} == {"romain_a", "romain_b", "bob", "bobby_z"}
        assert "Links" not in {p["player"] for p in summary["players"]}
        # a group's name still resolves in the checks (it can receive items)
        e.listener.check(1, 5, 7, 70, 0, at=10.0)
        item = e.feed.checks()["items"][0]
        assert item["receiver"] == "Links" and item["receiver_game"] == "GameA" and item["item"] == "GameA/item7"
        assert e.feed.summary()["room"]["slots"] == 4
    finally:
        await e.feed.stop()


async def test_a_new_seed_resets_presence_and_live_times(env):
    e = env()
    await started(e)
    try:
        e.listener.session()
        e.listener.check(3, 1, 1, 1, 0)
        assert e.feed.presence.last_check(3) is not None
        e.listener.session(seed="SEED2")
        assert e.feed.presence.last_check(3) is None and e.feed._live_check_at == {}
        assert e.feed.checks()["total"] == 0 and e.feed.log.seed == "SEED2"
    finally:
        await e.feed.stop()


async def test_live_check_without_a_seed_is_dropped_with_one_warning(env, monkeypatch):
    from multitracker.roomfeed import feed as feed_module
    warnings = []
    monkeypatch.setattr(feed_module.log, "warning", lambda msg, *args: warnings.append(msg % args))
    e = env()
    await started(e)
    try:
        e.listener.check(1, 3, 1, 1, 0, at=1.0)
        e.listener.check(1, 3, 1, 2, 0, at=2.0)
        assert warnings == ["roomfeed: live check heard while no seed is open: not recorded"]
        assert e.feed.checks()["total"] == 0
    finally:
        await e.feed.stop()


# -- final review fixes -----------------------------------------------------------------------------------------------
async def test_a_large_release_is_published_in_chunks_of_at_most_200(env):
    e = env()
    await started(e)
    try:
        e.listener.session()
        for location in range(1, 451):
            e.listener.check(1, 3, 5, location, 0, at=1000.0 + location)
        await until(lambda: sum(len(b["checks"]) for b in e.events("roomfeed_check")) >= 450)
        await asyncio.sleep(0.1)
        sizes = [len(b["checks"]) for b in e.events("roomfeed_check")]
        assert sizes == [200, 200, 50]
        keys = [c["key"] for b in e.events("roomfeed_check") for c in b["checks"]]
        assert len(set(keys)) == 450 and keys[0] == "1:450"  # newest first across the chunks
    finally:
        await e.feed.stop()


async def test_presence_is_rebuilt_when_the_listener_drops(env):
    e = env()
    await started(e)
    try:
        e.listener.session()
        summary = lambda: {s["name"]: s["presence"] for p in e.feed.summary()["players"] for s in p["slots"]}  # noqa: E731
        e.listener.send_status(2, 5)
        e.listener.send_status(3, 20)
        e.listener.kw["on_join"](4, ["AP"])
        e.listener.check(2, 3, 1, 1, 0)  # a live check just now
        assert summary() == {"romain_a": "unknown", "romain_b": "playing", "bob": "playing", "bobby_z": "playing"}
        e.listener.drop()  # the room went to sleep without a Part
        assert summary() == {"romain_a": "unknown", "romain_b": "playing", "bob": "unknown", "bobby_z": "unknown"}
        e.listener.session()  # the next session's statuses seed it again
        e.listener.send_status(3, 20)
        assert summary()["bob"] == "playing"
    finally:
        await e.feed.stop()


def write_rows(e: Env, *rows):
    log = RoomLog(e.root)
    log.open_seed("SEED1")
    for entry, names in rows:
        log.add(entry, names)


async def test_stored_names_are_used_when_the_slot_table_is_unknown(env):
    e = env(fetch_room=lambda url: (_ for _ in ()).throw(RoomError("endormie")),
            fetch=lambda url: (_ for _ in ()).throw(RoomError("endormie")))
    e.preset_seed()
    names = {"sender_name": "bob", "sender_game": "GameA", "receiver_name": "romain_b", "receiver_game": "GameB",
             "item_name": "Stored item", "location_name": "Stored loc"}
    write_rows(e, (CheckEntry(recorded_at=1000.0, at=1000.0, after=None, before=None, src="live", sender=3,
                              receiver=2, item=9, location=8, flags=0), names))
    await started(e)
    try:
        (item,) = e.feed.checks()["items"]
        assert (item["sender"], item["sender_game"], item["receiver"], item["receiver_game"]) == \
            ("bob", "GameA", "romain_b", "GameB")
        assert item["sender_player"] == "bob" and item["receiver_player"] == "romain"
        assert item["item"] == "GameB/item9" and item["location"] == "GameA/loc8"  # datapackage via the stored games
        assert e.feed.checks(player="bob")["total"] == 1 and e.feed.checks(game="GameB")["total"] == 0
        # the live slot table wins as soon as it is known
        e.listener.session(players={3: {"name": "bob_live", "game": "GameA"}})
        assert e.feed.checks()["items"][0]["sender"] == "bob_live"
    finally:
        await e.feed.stop()


async def test_catchup_merge_writes_one_batch_per_day_file(env):
    e = env()
    e.preset_seed()
    await started(e)
    try:
        e.tracker_data = payload(received={3: [(i, 100 + i, 1, 0) for i in range(30)]})
        await e.feed.poll_now()
        assert len(e.lines()) == 30
        assert len(e.feed.log.entries) == 30 and len(e.feed.log.keys) == 30
    finally:
        await e.feed.stop()


async def test_summary_active_at_is_the_last_live_check_only(env):
    e = env()
    e.preset_seed()
    await started(e)
    try:
        e.listener.session()
        e.listener.check(3, 1, 5, 6, 0, at=1000.0)
        e.listener.check(3, 1, 5, 7, 0, at=1500.0)
        e.tracker_data = payload(received={3: [(1, 1, 1, 0)]})  # a caught-up check of slot 1: not live activity
        await e.feed.poll_now()
        slots = {s["name"]: s for p in e.feed.summary()["players"] for s in p["slots"]}
        assert slots["bob"]["active_at"] == 1500.0
        assert slots["romain_a"]["active_at"] is None and slots["romain_a"]["last_check_at"] is not None
    finally:
        await e.feed.stop()
