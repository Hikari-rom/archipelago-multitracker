"""D31: pinned checks, stored per seed for any slot of the room, unpinned once done."""
from __future__ import annotations

import asyncio

from test_hints_m26 import fake_tracker, make_service


def service_with_room(tmp_path):
    s = make_service(tmp_path)
    s.trackers = {"Me_A": fake_tracker("Me_A", 1, [], missing={100, 101}, checked={102})}
    s.trackers["Me_A"].state.seed_name = "seed1"
    s.datapackage.location_name = lambda game, loc: f"{game} #{loc}"
    return s


def test_pin_unpin_and_names(tmp_path):
    s = service_with_room(tmp_path)
    queue: asyncio.Queue = asyncio.Queue()
    s.subscribers.add(queue)
    s.set_pin("Me_A", 100, True)
    s.set_pin("Friend", 500, True)  # another player's world (Indices page)
    s.set_pin("Me_A", 100, True)  # twice: still one pin
    assert [(p["slot"], p["location"], p["name"]) for p in s.pins()] == [
        ("Me_A", 100, "Game A #100"), ("Friend", 500, "Game C #500")]
    assert queue.get_nowait() == {"type": "pins"}
    s.set_pin("Me_A", 100, False)
    assert [p["slot"] for p in s.pins()] == ["Friend"]
    try:
        s.set_pin("Nobody", 1, True)
    except KeyError:
        pass
    else:
        raise AssertionError("unknown slot accepted")


def test_done_checks_are_unpinned(tmp_path):
    s = service_with_room(tmp_path)
    s.set_pin("Me_A", 101, True)
    s.set_pin("Me_A", 100, True)
    st = s.trackers["Me_A"].state
    st.checked.add(101)
    st.missing.discard(101)
    s._unpin_done("Me_A", st)
    assert [p["location"] for p in s.pins()] == [100]
    assert s.store.pins("seed1") == [("Me_A", 100, s.store.pins("seed1")[0][2])]
    st.checked.add(100)  # done but not seen by _on_change yet: dropped when read
    assert s.pins() == [] and s.store.pins("seed1") == []


def test_pins_api(tmp_path):
    from test_user_apworlds import call
    s = service_with_room(tmp_path)
    assert call(s, "PUT", "/api/pins", json={"slot": "Me_A", "location": 100}).json()["pins"][0]["location"] == 100
    assert call(s, "GET", "/api/pins").json()["pins"][0]["name"] == "Game A #100"
    assert call(s, "PUT", "/api/pins", json={"slot": "Nobody", "location": 1}).status_code == 404
    assert call(s, "PUT", "/api/pins", json={"slot": "Me_A", "location": 100, "pinned": False}).json() == {"pins": []}
