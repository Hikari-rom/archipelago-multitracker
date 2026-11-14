"""D41: what a slot lacks for its victory (items still to come), shown under the goal while it is not in go mode."""
from __future__ import annotations

import asyncio
import time
from collections import Counter

from testenv_helpers import FIXTURES


def isaac_like(have: Counter) -> bool:
    """3 bosses of 5 (The Lamb, Beast, Mega Satan...): the rule shape of Isaac's goal, with an "or"."""
    lamb = have["The Negative"] >= 1
    beast = have["Strange Door"] >= 1 and (have["The Polaroid"] >= 1 or have["The Negative"] >= 1)
    chest = have["The Polaroid"] >= 1 and have["Cathedral"] >= 1
    mega = have["Key Pieces"] >= 1 and (lamb or chest)
    return sum((lamb, beast, mega, chest)) >= 3


def test_goal_set_keeps_the_cheapest_pass_and_gives_the_alternatives():
    from multitracker.logic.ut_worker import SlotLogic
    to_come = Counter({"Cathedral": 1, "Key Pieces": 1, "The Negative": 1, "The Polaroid": 1, "Mines": 1,
                       "Knife Pieces": 2, "Boss Rush": 1})
    have = Counter({"Strange Door": 1})
    out = SlotLogic._goal_set(lambda extra: isaac_like(have + extra), to_come, time.perf_counter() + 30)
    assert out["kind"] == "set" and out["complete"]
    assert [(i["name"], i["count"]) for i in out["items"]] == [("Key Pieces", 1), ("The Negative", 1)]
    # the other pass took The Polaroid + Cathedral: neither alone replaces The Negative
    assert all(i["or"] == [] for i in out["items"])


def test_goal_set_counts_and_lone_item_alternatives():
    from multitracker.logic.ut_worker import SlotLogic
    to_come = Counter({"Power Star": 70, "Progressive Key": 2, "Wing Cap": 1})
    out = SlotLogic._goal_set(lambda e: e["Power Star"] >= 50 and e["Progressive Key"] >= 2, to_come,
                              time.perf_counter() + 30)
    assert [(i["name"], i["count"]) for i in out["items"]] == [("Power Star", 50), ("Progressive Key", 2)]
    # one item left, several would do: all of them listed
    to_come = Counter({"Hookshot": 1, "Longshot": 1, "Boots": 1})
    out = SlotLogic._goal_set(lambda e: e["Hookshot"] >= 1 or e["Longshot"] >= 1, to_come, time.perf_counter() + 30)
    (item,) = out["items"]
    assert item["count"] == 1 and {item["name"], *(a["name"] for a in item["or"])} == {"Hookshot", "Longshot"}


def test_goal_set_out_of_budget():
    from multitracker.logic.ut_worker import SlotLogic
    out = SlotLogic._goal_set(lambda e: True, Counter({"A": 1}), time.perf_counter() - 1)
    assert out == {"kind": "many"}


def test_goal_needs_super_mario_64():
    """The real world: the stars and keys Bowser in the Sky needs, nothing more; nothing once they are received."""
    from multitracker.logic.ut_worker import Worker, setup_ap
    yaml = str(FIXTURES / "multi5" / "sm64.yaml")
    setup_ap()
    from worlds.AutoWorld import AutoWorldRegister
    world = AutoWorldRegister.world_types["Super Mario 64"]
    ids = sorted(world.location_name_to_id.values())
    worker = Worker()
    req = {"op": "update", "slot_name": "SM64", "game": "Super Mario 64", "team": 0, "slot": 1, "slot_data": {},
           "yaml": yaml, "items": [], "missing": ids, "checked": []}
    res = worker.handle(req)
    assert res["state"] == "ok" and res["goal_in_logic"] is False, res
    needs = worker.handle({"op": "goal_needs", "slot_name": "SM64"})["needs"]
    assert needs["kind"] == "set" and needs["complete"], needs
    got = {i["name"]: i["count"] for i in needs["items"]}
    assert set(got) == {"Power Star", "Progressive Key"} and got["Progressive Key"] == 2, got
    items = [{"item": world.item_name_to_id[name], "location": -1, "player": 0, "flags": 1}
             for name, count in got.items() for _ in range(count)]
    res = worker.handle(dict(req, items=items))
    assert res["goal_in_logic"] is True
    assert worker.handle({"op": "goal_needs", "slot_name": "SM64"})["needs"] is None
    assert worker.handle({"op": "goal_needs", "slot_name": "nobody"})["needs"] is None
    # copies the generator demoted to filler (server flags 0, like Celeste's excess Strawberries) do not count, and
    # are not taken off the copies still to come either
    star = world.item_name_to_id["Power Star"]
    res = worker.handle(dict(req, items=[{"item": star, "location": 1, "player": 2, "flags": 0}] * 100))
    assert res["goal_in_logic"] is False
    needs = worker.handle({"op": "goal_needs", "slot_name": "SM64"})["needs"]
    assert needs["kind"] == "set" and {i["name"]: i["count"] for i in needs["items"]} == got, needs


def make_service(tmp_path, engine):
    import json
    from multitracker import config
    from multitracker.service import Service
    from multitracker.store import Store
    path = tmp_path / "room.yaml"
    path.write_text(json.dumps({"server": "127.0.0.1:38291", "password": "", "slots": [{"name": "Me"}]}))
    return Service(config.load(path), Store(tmp_path / "db.sqlite3"), engine, logic_debounce=0, publish_debounce=0)


def test_service_shows_the_needs_with_their_hints(tmp_path, monkeypatch):
    from multitracker.ap.tracker import SlotTracker
    from multitracker.logic import LogicEngine, LogicResult

    class Engine(LogicEngine):
        def __init__(self):
            self.goal_in_logic, self.asked = False, 0

        async def compute(self, request):
            return LogicResult("ok", in_logic=[], goal_in_logic=self.goal_in_logic)

        async def goal_needs(self, slot_name):
            self.asked += 1
            return {"kind": "set", "complete": True, "items": [
                {"name": "Key Pieces", "count": 1, "or": []},
                {"name": "The Negative", "count": 1, "or": [{"name": "The Polaroid", "count": 1}]}]}

    engine = Engine()
    s = make_service(tmp_path, engine)
    players = {1: {"name": "Me", "alias": "Me", "game": "Isaac"}, 2: {"name": "Friend", "alias": "Friend", "game": "Celeste"}}
    t = SlotTracker("127.0.0.1:38291", "", "Me", "The Binding of Isaac Repentance", None)
    st = t.state
    st.status, st.team, st.slot, st.players, st.synced = "connected", 0, 1, players, True
    st.missing = {1}
    st.hints = [{"finding_player": 2, "receiving_player": 1, "location": 500, "item": 7, "found": False,
                 "entrance": "", "item_flags": 1, "status": 0},
                {"finding_player": 2, "receiving_player": 1, "location": 501, "item": 8, "found": True,
                 "entrance": "", "item_flags": 1, "status": 0}]
    s.trackers = {"Me": t}
    names = {7: "The Polaroid", 8: "Key Pieces"}
    monkeypatch.setattr(s.datapackage, "item_name", lambda game, item: names.get(item, f"Item {item}"))
    monkeypatch.setattr(s.datapackage, "location_name", lambda game, loc: f"Loc {loc}")

    async def run():
        s._schedule_logic("Me")
        await s._logic_tasks["Me"]
    asyncio.run(run())
    assert engine.asked == 1
    needs = s._goal_needs_view("Me")
    assert needs["kind"] == "set"
    key, negative = needs["items"]
    assert key["hints"] == []  # its hint is found: the item is on its way
    assert negative["hints"] == [{"item": "The Polaroid", "finder": "Friend", "finder_game": "Celeste",
                                  "location": "Loc 500", "access": "unknown"}]
    # go mode: nothing to show, and nothing asked to the worker
    engine.goal_in_logic = True
    asyncio.run(run())
    assert engine.asked == 1 and s._goal_needs_view("Me") is None and "Me" not in s.goal_needs


def test_counted_leaves_out_filler_copies_and_the_yaml_start_inventory():
    """Taken off the slot's items: the progression items received, start inventory included (the world's own start
    items, The Wind Waker HD's first sword or KH Birth by Sleep's starting worlds, are in the slot's items:
    `world_start`). Not the copies demoted to filler, nor the yaml's `start_inventory` (added on top by the generator)."""
    from types import SimpleNamespace as Item
    from multitracker.logic.ut_worker import counted
    start_sword, yaml_bomb = Item(name="Progressive Sword", advancement=True), Item(name="Bombs", advancement=True)
    received = [start_sword, yaml_bomb, Item(name="Progressive Sword", advancement=True), Item(name="Bombs", advancement=True),
                Item(name="Strawberry", advancement=True), Item(name="Strawberry", advancement=False)]
    assert counted(received, [start_sword, yaml_bomb], {"Bombs": 1}) == {"Progressive Sword": 2, "Bombs": 1,
                                                                         "Strawberry": 1}
    assert counted(received, [start_sword, yaml_bomb]) == {"Progressive Sword": 2, "Bombs": 2, "Strawberry": 1}


def test_pool_names_items_by_their_id_and_counts_the_pre_fill_items():
    """Received items are named from their id (datapackage): Cookie Clicker's "Unlock Bank" and "Progressive Bank"
    share one id. Items kept for the world's own pre-fill (Phantom Hourglass's boss metals) are neither in the pool
    nor placed in Universal Tracker's regeneration (it stops after generate_basic)."""
    from types import SimpleNamespace as NS
    from multitracker.logic.ut_worker import SlotLogic

    def item(name, code, advancement=True, player=1):
        return NS(name=name, code=code, advancement=advancement, player=player)

    placed = item("Boss Key", 3)
    world = NS(item_id_to_name={1: "Progressive Bank", 2: "Rupee", 3: "Boss Key", 4: "Azurine"},
               get_pre_fill_items=lambda: [item("Azurine", 4), item("Azurine", 4), placed])  # placed: counted once
    mw = NS(itempool=[item("Unlock Bank", 1), item("Rupee", 2, advancement=False), item("Other", 9, player=2)],
            worlds={1: world},
            get_locations=lambda player: [NS(item=placed, address=10), NS(item=item("Event", None), address=None)])
    logic = NS(core=NS(multiworld=mw, player_id=1), slot_name="X", _pool_cache=None,
               world_start=[item("Unlock Bank", 1)])  # a start item the world took out of its pool
    assert SlotLogic._pool(logic) == {"Progressive Bank": 2, "Boss Key": 1, "Azurine": 2}
