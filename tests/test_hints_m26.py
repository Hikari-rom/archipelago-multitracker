"""M26: Indices page (hints of every tracked slot, accessibility for the finder, what blocks it)."""
from __future__ import annotations

import json
import sys

import pytest

from testenv_helpers import FIXTURES


def make_service(tmp_path, foreign: bool = True):
    from multitracker import config
    from multitracker.service import Service
    from multitracker.store import Store
    path = tmp_path / "room.yaml"
    path.write_text(json.dumps({"server": "127.0.0.1:38291", "password": "", "hints_foreign_logic": foreign,
                                "slots": [{"name": "Me_A"}, {"name": "Me_B"}]}))
    return Service(config.load(path), Store(tmp_path / "db.sqlite3"))


PLAYERS = {1: {"name": "Me_A", "alias": "Me_A", "game": "Game A"}, 2: {"name": "Me_B", "alias": "Me_B", "game": "Game B"},
           3: {"name": "Friend", "alias": "Friend", "game": "Game C"}, 4: {"name": "Other", "alias": "Other", "game": "Game D"}}


def hint(finder, receiver, location, item=77, found=False, status=0, flags=1):
    return {"finding_player": finder, "receiving_player": receiver, "location": location, "item": item,
            "found": found, "entrance": "", "item_flags": flags, "status": status}


def fake_tracker(name, slot, hints, missing=(), checked=()):
    from multitracker.ap.tracker import SlotTracker
    t = SlotTracker("127.0.0.1:38291", "", name, PLAYERS[slot]["game"], None)
    st = t.state
    st.status, st.team, st.slot, st.players = "connected", 0, slot, PLAYERS
    st.hints, st.missing, st.checked, st.synced = hints, set(missing), set(checked), True
    return t


def test_table_merges_hints_and_says_who_can_do_what(tmp_path):
    from multitracker.logic import LogicResult
    s = make_service(tmp_path)
    shared = hint(1, 2, 100)  # in Me_A's world, for Me_B: both tracked slots see it
    s.trackers = {
        "Me_A": fake_tracker("Me_A", 1, [shared, hint(1, 4, 101), hint(3, 1, 500), hint(1, 1, 102, found=True)],
                             missing={100, 101}, checked={102}),
        "Me_B": fake_tracker("Me_B", 2, [dict(shared), hint(4, 2, 600, status=30)]),
    }
    s.logic = {"Me_A": LogicResult("ok", in_logic=[101],
                                   blockers={100: {"kind": "single", "items": ["Hookshot"]}}),
               "Me_B": LogicResult("pending")}
    rows = {(r["finder_slot"], r["location_id"]): r for r in s.hints.table()["hints"]}
    assert len(rows) == 5  # the shared hint once
    assert sorted(rows[("Me_A", 100)]["slots"]) == ["Me_A", "Me_B"]
    assert rows[("Me_A", 100)]["access"] == {"state": "blocked", "blockers": {"kind": "single", "items": ["Hookshot"]}}
    assert rows[("Me_A", 101)]["access"] == {"state": "ok"} and not rows[("Me_A", 101)]["receiver_tracked"]
    assert rows[("Me_A", 102)]["access"] == {"state": "found"}
    # untracked finders: not followed yet (the board starts them on the next reconcile)
    assert rows[("Friend", 500)]["access"]["state"] == "unknown" and not rows[("Friend", 500)]["finder_tracked"]
    assert rows[("Other", 600)]["status"] == "priority" and rows[("Other", 600)]["slots"] == ["Me_B"]


def test_foreign_slots_wanted_and_capped(tmp_path, monkeypatch):
    from multitracker import hints as hints_mod
    s = make_service(tmp_path)
    s.trackers = {
        "Me_A": fake_tracker("Me_A", 1, [hint(3, 1, 500), hint(3, 1, 501), hint(4, 1, 600), hint(3, 1, 502, found=True),
                                         hint(1, 3, 100)]),  # an item of Friend in my world: nothing to follow
    }
    assert s.hints.wanted() == {"Friend": ("Game C", 2), "Other": ("Game D", 1)}
    monkeypatch.setattr(hints_mod, "FOREIGN_MAX", 1)
    started = []
    monkeypatch.setattr(s.hints, "_start", lambda name, game: started.append(name) or s.hints.trackers.update(
        {name: fake_tracker(name, 3, [])}))
    monkeypatch.setattr(hints_mod, "PUBLISH_DEBOUNCE", 0)
    import asyncio
    asyncio.run(s.hints._reconcile())
    assert started == ["Friend"] and s.hints.capped == {"Other"}  # the slot with the most hints first
    row = next(r for r in s.hints.table()["hints"] if r["finder_slot"] == "Other")
    assert "au plus 1" in row["access"]["reason"]


def test_foreign_logic_disabled(tmp_path):
    s = make_service(tmp_path, foreign=False)
    s.trackers = {"Me_A": fake_tracker("Me_A", 1, [hint(3, 1, 500)])}
    import asyncio
    from multitracker import hints as hints_mod
    hints_mod.PUBLISH_DEBOUNCE, before = 0, hints_mod.PUBLISH_DEBOUNCE
    try:
        asyncio.run(s.hints._reconcile())
    finally:
        hints_mod.PUBLISH_DEBOUNCE = before
    assert not s.hints.trackers
    row = s.hints.table()["hints"][0]
    assert "désactivé" in row["access"]["reason"]


def test_blockers_super_mario_64():
    """What a location lacks, from the world's rules and item pool: one item, several copies, or a set."""
    from multitracker.logic.ut_worker import Worker, setup_ap
    setup_ap()
    from worlds.AutoWorld import AutoWorldRegister
    names = AutoWorldRegister.world_types["Super Mario 64"].location_name_to_id
    ids = sorted(names.values())
    req = {"op": "update", "slot_name": "SM64", "game": "Super Mario 64", "team": 0, "slot": 1, "slot_data": {},
           "yaml": str(FIXTURES / "multi5" / "sm64.yaml"), "items": [], "missing": ids, "checked": [],
           "explain": [names["BoB: Shoot to the Island in the Sky"], names["CCM: Big Penguin Race"],
                       names["SL: Snowman's Big Head"], names["BoB: Big Bob-Omb on the Summit"]]}
    res = Worker().handle(req)
    assert res["state"] == "ok", res
    blockers = {int(k): v for k, v in res["blockers"].items()}
    assert names["BoB: Big Bob-Omb on the Summit"] not in blockers  # in logic: nothing to explain
    assert blockers[names["BoB: Shoot to the Island in the Sky"]] == {"kind": "single", "items": ["Cannon Unlock BoB"]}
    assert blockers[names["CCM: Big Penguin Race"]] == {"kind": "set", "items": [["Power Star", 3]]}
    assert blockers[names["SL: Snowman's Big Head"]] == {"kind": "set", "items": [["Progressive Key", 2]]}
