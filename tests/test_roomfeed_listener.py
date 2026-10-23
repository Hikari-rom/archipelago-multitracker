import asyncio

import pytest

from multitracker.ap import net
from multitracker.ap.tracker import ForbiddenCommand
from multitracker.roomfeed.listener import LISTENER_COMMANDS, RoomListener

ROOM_INFO = {"cmd": "RoomInfo", "seed_name": "SEED1", "datapackage_checksums": {"A": "x", "B": "y"}}
CONNECTED = {"cmd": "Connected", "team": 0, "slot": 1,
             "players": [{"team": 0, "slot": 1, "alias": "al", "name": "Alice"},
                         {"team": 0, "slot": 2, "alias": "bo", "name": "Bob"}],
             "slot_info": {"1": {"name": "Alice", "game": "A", "type": 1},
                           "2": {"name": "Bob", "game": "B", "type": 1},
                           "3": {"name": "Links", "game": "A", "type": 2}}}


class FakeSocket:
    """Plays prepared frames, then stays open (like a quiet server) until closed."""

    def __init__(self, frames):
        self.frames = [net.encode(f if isinstance(f, list) else [f]) for f in frames]
        self.sent: list[dict] = []
        self.closed = asyncio.Event()

    async def send(self, data):
        self.sent.extend(net.decode(data))

    async def close(self):
        self.closed.set()

    def __aiter__(self):
        return self._iterate()

    async def _iterate(self):
        for frame in self.frames:
            yield frame
        await self.closed.wait()


class Cache:
    def __init__(self, missing=()):
        self._missing, self.added = list(missing), []

    def missing(self, checksums):
        return list(self._missing)

    def add(self, games):
        self.added.append(games)


async def until(predicate, timeout=3.0):
    deadline = asyncio.get_running_loop().time() + timeout
    while asyncio.get_running_loop().time() < deadline:
        if predicate():
            return
        await asyncio.sleep(0.01)
    raise AssertionError("timed out")


class Recorder:
    def __init__(self):
        self.checks, self.joins, self.parts, self.statuses, self.sessions, self.states = [], [], [], [], [], []

    def kwargs(self):
        return dict(on_session=self.sessions.append,
                    on_check=lambda *a: self.checks.append(a),
                    on_join=lambda slot, tags: self.joins.append((slot, tags)),
                    on_part=self.parts.append,
                    on_status=lambda slot, value: self.statuses.append((slot, value)),
                    on_state=lambda lst: self.states.append(lst.status))


@pytest.fixture
def play(monkeypatch):
    """Start a listener on a fake socket playing `frames`; returns (listener, socket, recorder)."""
    async def go(frames, cache=None, password="pw", **extra):
        sock = FakeSocket(frames)
        opened = []

        async def open_socket(address):
            opened.append(address)
            return sock, "ws://" + address

        monkeypatch.setattr(net, "open_socket", open_socket)
        rec = Recorder()
        lst = RoomListener(lambda: "host:1", password, "Spy", cache or Cache(), min_delay=0.01, max_delay=0.05,
                           **{**rec.kwargs(), **extra})
        lst.start()
        return lst, sock, rec, opened

    yield go


def test_whitelist_constant():
    assert LISTENER_COMMANDS == frozenset({"GetDataPackage", "Connect", "Get", "SetNotify"})


async def test_roominfo_then_connect_and_datapackage(play):
    cache = Cache(missing=["A"])
    lst, sock, rec, opened = await play([ROOM_INFO, {"cmd": "DataPackage", "data": {"games": {"A": {"checksum": "x"}}}}],
                                        cache=cache)
    try:
        await until(lambda: len(sock.sent) == 2 and cache.added)
        assert opened == ["host:1"]
        assert sock.sent[0] == {"cmd": "GetDataPackage", "games": ["A"]}
        connect = sock.sent[1]
        assert connect["cmd"] == "Connect" and connect["tags"] == ["Tracker"] and connect["items_handling"] == 0
        assert connect["game"] == "" and connect["name"] == "Spy" and connect["password"] == "pw"
        assert connect["slot_data"] is False and connect["version"] == net.AP_VERSION
        assert len(connect["uuid"]) == 32
        assert lst.seed_name == "SEED1" and lst.status == "connecting"
        assert cache.added == [{"A": {"checksum": "x"}}]
    finally:
        await lst.stop()


async def test_empty_password_is_none_and_no_datapackage_when_nothing_missing(play):
    lst, sock, rec, _ = await play([ROOM_INFO], password="")
    try:
        await until(lambda: sock.sent)
        assert [m["cmd"] for m in sock.sent] == ["Connect"] and sock.sent[0]["password"] is None
    finally:
        await lst.stop()


async def test_connected_sends_get_and_setnotify_per_status_key(play):
    lst, sock, rec, _ = await play([ROOM_INFO, CONNECTED])
    try:
        await until(lambda: lst.status == "listening" and len(sock.sent) == 3 and rec.sessions)
        keys = ["_read_client_status_0_1", "_read_client_status_0_2", "_read_client_status_0_3"]
        assert sock.sent[1] == {"cmd": "Get", "keys": keys}
        assert sock.sent[2] == {"cmd": "SetNotify", "keys": keys}
        assert (lst.team, lst.slot) == (0, 1)
        assert lst.players == {1: {"name": "Alice", "game": "A"}, 2: {"name": "Bob", "game": "B"},
                               3: {"name": "Links", "game": "A"}}
        assert lst.listening_since is not None and lst.error is None
        assert rec.sessions == [lst] and rec.states.count("listening") == 1
    finally:
        await lst.stop()


async def test_item_send_dict_and_list_forms(play):
    item_dict = {"cmd": "PrintJSON", "type": "ItemSend", "receiving": 2, "data": [],
                 "item": {"item": 10, "location": 20, "player": 1, "flags": 1}}
    item_list = {"cmd": "PrintJSON", "type": "ItemSend", "receiving": 1, "item": [11, 21, 2, 4]}
    bad = [{"cmd": "PrintJSON", "type": "ItemSend", "receiving": 1},
           {"cmd": "PrintJSON", "type": "ItemSend", "receiving": "x", "item": {"item": 1, "location": 2, "player": 3}},
           {"cmd": "PrintJSON", "type": "ItemSend", "receiving": 1, "item": [1, 2]},
           {"cmd": "PrintJSON", "type": "Chat", "message": "hi"}]
    lst, sock, rec, _ = await play([ROOM_INFO, CONNECTED, item_dict, [*bad], item_list])
    try:
        await until(lambda: len(rec.checks) == 2)
        (s1, r1, i1, l1, f1, at1), (s2, r2, i2, l2, f2, at2) = rec.checks
        assert (s1, r1, i1, l1, f1) == (1, 2, 10, 20, 1)
        assert (s2, r2, i2, l2, f2) == (2, 1, 11, 21, 4)
        assert isinstance(at1, float) and at1 <= at2
        assert len(rec.checks) == 2
    finally:
        await lst.stop()


async def test_join_part_filtered_by_team(play):
    frames = [ROOM_INFO, CONNECTED,
              {"cmd": "PrintJSON", "type": "Join", "team": 0, "slot": 2, "tags": ["AP", "Tracker"]},
              {"cmd": "PrintJSON", "type": "Join", "team": 1, "slot": 2, "tags": ["AP"]},
              {"cmd": "PrintJSON", "type": "Join", "team": 0, "slot": 1},
              {"cmd": "PrintJSON", "type": "Part", "team": 1, "slot": 2},
              {"cmd": "PrintJSON", "type": "Part", "team": 0, "slot": 2}]
    lst, sock, rec, _ = await play(frames)
    try:
        await until(lambda: rec.parts)
        assert rec.joins == [(2, ["AP", "Tracker"]), (1, [])]
        assert rec.parts == [2]
    finally:
        await lst.stop()


async def test_retrieved_and_setreply_statuses(play):
    frames = [ROOM_INFO, CONNECTED,
              {"cmd": "Retrieved", "keys": {"_read_client_status_0_1": 20, "_read_client_status_0_2": None,
                                            "other": 5}},
              {"cmd": "SetReply", "key": "_read_client_status_0_2", "value": 30},
              {"cmd": "SetReply", "key": "unrelated", "value": 99}]
    lst, sock, rec, _ = await play(frames)
    try:
        await until(lambda: (2, 30) in rec.statuses)
        assert rec.statuses == [(1, 20), (2, 0), (2, 30)]
        assert lst.statuses == {1: 20, 2: 30}
    finally:
        await lst.stop()


async def test_connection_refused(play):
    lst, sock, rec, _ = await play([ROOM_INFO, {"cmd": "ConnectionRefused", "errors": ["InvalidSlot"]}])
    try:
        await until(lambda: lst.status == "error")
        assert lst.error == "connexion refusée : InvalidSlot"
    finally:
        await lst.stop()


async def test_callback_exception_does_not_break_session(play):
    item = {"cmd": "PrintJSON", "type": "ItemSend", "receiving": 2, "item": {"item": 1, "location": 2, "player": 1}}

    seen = []

    def boom(*a):
        seen.append(a)
        raise RuntimeError("boom")

    def boom_session(lst):
        raise RuntimeError("boom")
    lst, sock, rec, _ = await play([ROOM_INFO, CONNECTED, item, item], on_check=boom, on_session=boom_session)
    try:
        await until(lambda: len(seen) == 2)
        assert lst.status == "listening"
    finally:
        await lst.stop()


async def test_send_refuses_everything_but_the_whitelist(play):
    lst, sock, rec, _ = await play([ROOM_INFO, CONNECTED])
    try:
        await until(lambda: lst.status == "listening")
        before = len(sock.sent)
        for msg in ({"cmd": "LocationScouts", "locations": [1], "create_as_hint": 0}, {"cmd": "Say", "text": "x"},
                    {"cmd": "LocationChecks", "locations": [1]}, {"cmd": "Sync"}, {"cmd": "StatusUpdate", "status": 30}, {}):
            with pytest.raises(ForbiddenCommand):
                await lst._send(msg)
        with pytest.raises(ForbiddenCommand):  # one forbidden command in a batch: nothing is sent
            await lst._send({"cmd": "Get", "keys": []}, {"cmd": "Say", "text": "x"})
        assert len(sock.sent) == before
    finally:
        await lst.stop()


async def test_empty_address_means_disconnected_and_no_connection(monkeypatch):
    calls = []

    async def open_socket(address):
        calls.append(address)
        raise AssertionError("must not connect")
    monkeypatch.setattr(net, "open_socket", open_socket)
    lst = RoomListener(lambda: "", "", "Spy", Cache(), min_delay=0.01, max_delay=0.05)
    lst.start()
    try:
        await until(lambda: lst.status == "disconnected")
        assert lst.error == "adresse du serveur inconnue (room endormie ?)"
        await asyncio.sleep(0.15)
        assert calls == [] and lst.status == "disconnected"
    finally:
        await lst.stop()


async def test_reconnects_after_the_server_closes(monkeypatch):
    sockets = []

    class ShortSocket(FakeSocket):
        async def _iterate(self):
            for frame in self.frames:
                yield frame

    async def open_socket(address):
        sock = ShortSocket([ROOM_INFO, CONNECTED])
        sockets.append(sock)
        return sock, address
    monkeypatch.setattr(net, "open_socket", open_socket)
    lst = RoomListener(lambda: "host:1", "", "Spy", Cache(), min_delay=0.01, max_delay=0.05)
    lst.start()
    try:
        await until(lambda: len(sockets) >= 2)
        assert all(s.closed.is_set() or s is sockets[-1] for s in sockets)
    finally:
        await lst.stop()
    assert lst.status in ("disconnected", "listening")


@pytest.fixture
def sleeps(monkeypatch):
    """Record the listener's waits (>= 1 s: the test helpers only sleep for tenths) without really waiting."""
    real_sleep, waits = asyncio.sleep, []

    async def fake_sleep(delay, *a):
        if delay >= 1:
            waits.append(delay)
            delay = 0.001
        await real_sleep(delay, *a)
    monkeypatch.setattr(asyncio, "sleep", fake_sleep)
    return waits


def backoff_listener(**kwargs):
    return RoomListener(lambda: "host:1", "", "Spy", Cache(), min_delay=2.0, max_delay=20.0, **kwargs)


async def test_backoff_resets_after_a_session_that_ends_by_exception(monkeypatch, sleeps):
    attempts = []

    class DroppedSocket(FakeSocket):
        async def _iterate(self):
            for frame in self.frames:
                yield frame
            raise ConnectionError("abnormal close")

    async def open_socket(address):
        attempts.append(address)
        if len(attempts) == 3:
            return DroppedSocket([ROOM_INFO, CONNECTED]), address
        raise ConnectionError("down")
    monkeypatch.setattr(net, "open_socket", open_socket)
    lst = backoff_listener()
    lst.start()
    try:
        await until(lambda: len(attempts) >= 5)
    finally:
        await lst.stop()
    assert sleeps[:4] == [2.0, 4.0, 2.0, 4.0]  # grows while down, back to min_delay after the dropped session


async def test_refusals_back_off_and_a_fatal_one_waits_max_delay(monkeypatch, sleeps):
    errors = [["Whatever"], ["Whatever"], ["InvalidSlot"]]

    async def open_socket(address):
        return FakeSocket([ROOM_INFO, {"cmd": "ConnectionRefused", "errors": errors.pop(0)}]), address
    monkeypatch.setattr(net, "open_socket", open_socket)
    lst = backoff_listener()
    lst.start()
    try:
        await until(lambda: len(sleeps) >= 3)
    finally:
        await lst.stop()
    assert sleeps[:3] == [2.0, 4.0, 20.0]  # other refusals back off; a fatal one waits max_delay
