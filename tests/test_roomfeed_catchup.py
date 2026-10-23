"""Tracker API parsing and catch-up merge (no network: _open is monkeypatched)."""
from __future__ import annotations

import json
import urllib.error

import pytest

from multitracker import room
from multitracker.roomfeed import catchup
from multitracker.roomfeed.catchup import StaticInfo, TrackerSnapshot

TRACKER = {
    "aliases": [],
    "player_items_received": [
        {"team": 0, "player": 1, "items": [[100, 11, 2, 1], {"item": 101, "location": 12, "player": 3, "flags": 0},
                                           [102, 13, 1, 0], [1, 2, 3], "junk"]},
        {"team": 0, "player": 2, "items": [[200, 21, 0, 0], [201, 0, 3, 0], [202, -1, 3, 0], [203, 22, 3, 2]]},
        {"team": 1, "player": 1, "items": [[900, 91, 2, 0]]},
        {"team": 0, "items": [[300, 31, 2, 0]]},
        {"team": 0, "player": 3, "items": None},
    ],
    "player_checks_done": [
        {"team": 0, "player": 1, "locations": [11, 12, 13]},
        {"team": 0, "player": 2, "locations": [21]},
        {"team": 1, "player": 1, "locations": [91, 92]},
        {"team": 0},
    ],
    "total_checks_done": [{"team": 0, "checks_done": 4}, {"team": 1, "checks_done": 2}],
    "activity_timers": [
        {"team": 0, "player": 1, "time": "Sat, 11 Oct 2026 00:12:00 GMT"},
        {"team": 0, "player": 2, "time": None},
        {"team": 1, "player": 1, "time": "Sat, 11 Oct 2026 00:12:00 GMT"},
        {"team": 0},
    ],
    "player_status": [
        {"team": 0, "player": 1, "status": 30},
        {"team": 0, "player": 2, "status": 0},
        {"team": 1, "player": 1, "status": 20},
        {"team": 0, "player": 3},
    ],
    "hints": [],
}
STATIC = {
    "player_locations_total": [
        {"team": 0, "player": 1, "total_locations": 50},
        {"team": 0, "player": 2, "total_locations": 70},
        {"team": 1, "player": 1, "total_locations": 5},
        {"team": 0, "player": 3},
    ],
    "player_game": [
        {"team": 0, "player": 1, "game": "Pokemon Emerald"},
        {"team": 0, "player": 2, "game": "Hades"},
        {"team": 1, "player": 1, "game": "Other"},
        {"team": 0, "game": "Nope"},
    ],
}

def test_parse_tracker_received_in_both_forms():
    snap = catchup.parse_tracker(TRACKER)
    assert snap.received[1] == [(100, 11, 2, 1), (101, 12, 3, 0), (102, 13, 1, 0)]
    assert snap.received[2] == [(200, 21, 0, 0), (201, 0, 3, 0), (202, -1, 3, 0), (203, 22, 3, 2)]
    assert 3 not in snap.received or snap.received[3] == []

def test_parse_tracker_counters_and_status():
    snap = catchup.parse_tracker(TRACKER)
    assert snap.checks_done == {1: 3, 2: 1}
    assert snap.activity == {1: 1791677520.0, 2: None}
    assert snap.status == {1: 30, 2: 0}
    assert snap.total_done == 4

def test_parse_tracker_other_team_and_empty():
    snap = catchup.parse_tracker(TRACKER, team=1)
    assert snap.received == {1: [(900, 91, 2, 0)]}
    assert snap.checks_done == {1: 2}
    assert snap.total_done == 2
    empty = catchup.parse_tracker({})
    assert empty == TrackerSnapshot(received={}, checks_done={}, activity={}, status={}, total_done=0)

def test_parse_static():
    assert catchup.parse_static(STATIC) == StaticInfo(totals={1: 50, 2: 70}, games={1: "Pokemon Emerald", 2: "Hades"})
    assert catchup.parse_static({}) == StaticInfo(totals={}, games={})

def _snapshot(received):
    return TrackerSnapshot(received=received, checks_done={}, activity={}, status={}, total_done=0)

def test_missing_entries_filters_and_orders():
    snap = catchup.parse_tracker(TRACKER)
    out = catchup.missing_entries(snap, {(2, 11)}, polled_at=2000.0, after=1500.0)
    assert [(e.receiver, e.sender, e.location, e.item) for e in out] == [(1, 3, 12, 101), (1, 1, 13, 102),
                                                                          (2, 3, 22, 203)]
    entry = out[0]
    assert (entry.src, entry.recorded_at, entry.at, entry.after, entry.before, entry.flags) == \
        ("catchup", 2000.0, None, 1500.0, 2000.0, 0)
    assert out[2].flags == 2

def test_missing_entries_no_duplicate_key_in_payload():
    snap = _snapshot({1: [(100, 11, 2, 0), (100, 11, 2, 0)], 3: [(101, 11, 2, 0)]})
    out = catchup.missing_entries(snap, set(), polled_at=10.0, after=None)
    assert len(out) == 1 and out[0].receiver == 1 and out[0].after is None

def test_missing_entries_receiver_order():
    snap = _snapshot({3: [(1, 31, 1, 0)], 1: [(2, 12, 2, 0), (3, 13, 2, 0)]})
    out = catchup.missing_entries(snap, set(), polled_at=10.0, after=None)
    assert [(e.receiver, e.location) for e in out] == [(1, 12), (1, 13), (3, 31)]

def test_api_urls():
    assert catchup.api_urls("https://archipelago.gg/room/wVAe_qVET2qit1wc2Kzj6A", "yQdtVUWGRFaaMCu14kdq8A") == (
        "https://archipelago.gg/api/tracker/yQdtVUWGRFaaMCu14kdq8A",
        "https://archipelago.gg/api/static_tracker/yQdtVUWGRFaaMCu14kdq8A")

@pytest.mark.parametrize("tracker_id", ["../x", "short", "a" * 41, "abc def ghi", ""])
def test_api_urls_bad_tracker_id(tracker_id):
    with pytest.raises(room.RoomError):
        catchup.api_urls("https://archipelago.gg/room/wVAe_qVET2qit1wc2Kzj6A", tracker_id)

def test_api_urls_bad_room_url():
    with pytest.raises(room.RoomError):
        catchup.api_urls("https://archipelago.gg/other", "yQdtVUWGRFaaMCu14kdq8A")

@pytest.fixture
def allowed(monkeypatch):
    monkeypatch.setenv("MT_ROOM_HOSTS", "127.0.0.1")

def test_fetch_json_ok(monkeypatch, allowed):
    seen = []
    def fake_open(url, timeout, max_bytes):
        seen.append((url, timeout, max_bytes))
        return json.dumps({"a": 1}).encode()
    monkeypatch.setattr(catchup, "_open", fake_open)
    assert catchup.fetch_json("http://127.0.0.1:1/api/tracker/x", timeout=5.0) == {"a": 1}
    assert seen == [("http://127.0.0.1:1/api/tracker/x", 5.0, 64 * 1024 * 1024)]

@pytest.mark.parametrize("body", [b"not json", b"[1, 2]", b"\xff\xfe"])
def test_fetch_json_unreadable(monkeypatch, allowed, body):
    monkeypatch.setattr(catchup, "_open", lambda *a: body)
    with pytest.raises(room.RoomError, match="réponse illisible du site"):
        catchup.fetch_json("http://127.0.0.1:1/x")

def test_fetch_json_too_large(monkeypatch, allowed):
    def fake_open(url, timeout, max_bytes):
        raise room.RoomError("réponse trop grande")
    monkeypatch.setattr(catchup, "_open", fake_open)
    with pytest.raises(room.RoomError, match="trop grande"):
        catchup.fetch_json("http://127.0.0.1:1/x", max_bytes=10)

def test_fetch_json_network_error(monkeypatch, allowed):
    def fake_open(*args):
        raise urllib.error.URLError("boom")
    monkeypatch.setattr(catchup, "_open", fake_open)
    with pytest.raises(room.RoomError, match="impossible de joindre 127.0.0.1 : .*boom"):
        catchup.fetch_json("http://127.0.0.1:1/x")

def test_fetch_json_http_error(monkeypatch, allowed):
    def fake_open(url, timeout, max_bytes):
        raise urllib.error.HTTPError(url, 503, "down", None, None)
    monkeypatch.setattr(catchup, "_open", fake_open)
    with pytest.raises(room.RoomError, match="le site a répondu 503"):
        catchup.fetch_json("http://127.0.0.1:1/x")

def test_fetch_json_refuses_unlisted_host(monkeypatch):
    monkeypatch.delenv("MT_ROOM_HOSTS", raising=False)
    monkeypatch.setattr(catchup, "_open", lambda *a: pytest.fail("must not open"))
    with pytest.raises(room.RoomError, match="site non autorisé"):
        catchup.fetch_json("http://127.0.0.1/api/tracker/x")

def test_open_size_limit_and_no_redirect():
    import http.server
    import threading

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path == "/redir":
                self.send_response(302)
                self.send_header("Location", "/big")
                self.end_headers()
                return
            body = b"x" * 100 if self.path == "/big" else b"{}"
            self.send_response(200)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):
            pass

    srv = http.server.HTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        base = f"http://127.0.0.1:{srv.server_address[1]}"
        assert catchup._open(f"{base}/ok", 5.0, 100) == b"{}"
        assert len(catchup._open(f"{base}/big", 5.0, 100)) == 100
        with pytest.raises(room.RoomError, match="trop grande"):
            catchup._open(f"{base}/big", 5.0, 99)
        with pytest.raises(urllib.error.HTTPError):
            catchup._open(f"{base}/redir", 5.0, 100)
    finally:
        srv.shutdown()
        srv.server_close()
