"""Goals of the games ("Objectifs" page): every describer, on a real generated multiworld (all22)."""
from __future__ import annotations

from collections import Counter

import pytest
import yaml

from testenv_helpers import FIXTURES, generated_seed


@pytest.fixture(scope="module")
def all22_world():
    import logic_reference as lr
    md = lr.load_multidata(generated_seed("all22", 7, spoiler=1))
    yamls = {d["name"]: (p, d["game"]) for p in (FIXTURES / "all22").glob("*.yaml")
             for d in [yaml.safe_load(p.read_text())]}
    return md, yamls


def contexts(md, yamls, full: bool):
    """A GoalContext per slot: nothing received and nothing checked, or everything (`full`)."""
    from multitracker.goals import GoalContext, yaml_options
    for slot, info in md["slot_info"].items():
        game = info.game
        dp = md["datapackage"][game]
        item_names = {v: k for k, v in dp["item_name_to_id"].items()}
        loc_names = {v: k for k, v in dp["location_name_to_id"].items()}
        own = md["locations"][slot]
        received = Counter()
        if full:
            for player_locs in md["locations"].values():
                for item, player, _flags in player_locs.values():
                    if player == slot:
                        received[item_names[item]] += 1
            for item in md["precollected_items"][slot]:
                received[item_names[item]] += 1
        names = {loc_names[loc] for loc in own}
        path, _ = yamls[info.name]
        yield info.name, GoalContext(game=game, slot_data=md["slot_data"][slot] or {}, yaml=yaml_options(path, game),
                                     received=received, checked=names if full else set(), locations=names,
                                     goal=False, checked_ids=set(own) if full else set())


def test_every_game_of_romain_has_a_goal_and_counters_start_at_zero(all22_world):
    from multitracker.goals import describe
    md, yamls = all22_world
    seen = 0
    for name, ctx in contexts(md, yamls, full=False):
        goal = describe(ctx)
        assert goal and goal["summary"] and "?" not in goal["summary"], name
        assert goal["steps"] or goal["counters"], name
        for c in goal["counters"]:
            assert 0 <= c["current"] < c["target"], (name, c)
        assert all(s["done"] is not True for s in goal["steps"]), (name, goal["steps"])
        seen += 1
    assert seen == 22


def test_with_everything_received_and_checked_the_counters_are_full(all22_world):
    """Item and location names used by the describers exist: with the whole pool every counter is reached."""
    from multitracker.goals import describe
    md, yamls = all22_world
    for name, ctx in contexts(md, yamls, full=True):
        goal = describe(ctx)
        for c in goal["counters"]:
            assert c["current"] >= c["target"], (name, c)
        for s in goal["steps"][:-1]:  # the last step is the goal itself (from the server, or its location)
            assert s["done"] in (True, None), (name, s)


def test_goal_reached_marks_every_step_done():
    from multitracker.goals import GoalContext, describe
    ctx = GoalContext(game="Kingdom Hearts 2", slot_data={"Goal": 1, "FinalXemnas": 1, "LuckyEmblemsRequired": 40},
                      yaml={}, received=Counter({"Lucky Emblem": 23}), checked=set(), locations=set(), goal=False)
    goal = describe(ctx)
    assert goal["summary"] == "40 Lucky Emblems, puis Final Xemnas"
    assert goal["counters"] == [{"label": "Lucky Emblems", "current": 23, "target": 40}]
    assert goal["steps"] == [{"label": "Vaincre Final Xemnas", "done": False}]
    assert goal["source"] == "slot_data"
    ctx.goal = True
    assert describe(ctx)["steps"][0]["done"] is True
    ctx.game = "Some Other Game"
    assert describe(ctx) is None


def test_yaml_options_skip_random_values(tmp_path):
    from multitracker.goals import yaml_options
    p = tmp_path / "p.yaml"
    p.write_text("name: P\ngame: Balatro\nBalatro:\n  goal: {beat_decks: 50, beat_ante: 0}\n"
                 "  decks_win_goal: {3: 50, 5: 50}\n  ante_win_goal: random-range-8-12\n"
                 "  required_stake_for_goal: ['White Stake']\n  jokers_unlock_goal: 75\n")
    assert yaml_options(p, "Balatro") == {"goal": "beat_decks", "required_stake_for_goal": ["White Stake"],
                                          "jokers_unlock_goal": 75}
    assert yaml_options(None, "Balatro") == {} and yaml_options(tmp_path / "missing.yaml", "Balatro") == {}


def _ctx(game, slot_data, locations, checked):
    from multitracker.goals import GoalContext
    return GoalContext(game=game, slot_data=slot_data, yaml={}, received=Counter(), checked=set(checked),
                       locations=set(locations), goal=False)


ORI_BF_MAPS = ["GladesMap", "BlackrootMap", "HollowGroveMap", "GumoHideoutMap", "SwampMap", "HoruMap", "ValleyMap",
               "ForlornMap", "SorrowMap"]


@pytest.mark.parametrize("maps", [ORI_BF_MAPS, [f"ProgressiveMap{i}" for i in range(1, 10)]])
def test_ori_bf_maps_are_counted_from_the_map_checks(maps):
    from multitracker.goals import describe
    goal = describe(_ctx("Ori and the Blind Forest", {"goal": ["AllMaps"]}, maps + ["SorrowMapstone"],
                         maps[:3] + ["SorrowMapstone"]))
    assert {"label": "Cartes activées", "current": 3, "target": 9} in goal["counters"]
    assert [s["label"] for s in goal["steps"]] == ["Fuir le mont Horu"]


def test_ori_bf_maps_unknown_without_map_locations():
    from multitracker.goals import describe
    goal = describe(_ctx("Ori and the Blind Forest", {"goal": ["AllMaps"]}, [], []))
    assert {"label": "Toutes les cartes", "done": None} in goal["steps"]


def test_ori_wotw_wisps_are_counted_from_their_locations():
    from multitracker.goals import describe
    wisps = ["EastHollow.ForestsVoice", "LowerReach.ForestsMemory", "UpperDepths.ForestsEyes",
             "WestPools.ForestsStrength", "WindtornRuins.Seir"]
    goal = describe(_ctx("Ori and the Will of the Wisps", {"goal_wisps": True}, wisps, wisps[:2]))
    assert {"label": "Wisps", "current": 2, "target": 5} in goal["counters"]
    assert all(s["done"] is not None for s in goal["steps"]), goal["steps"]


WOTW_SHRIEK = "Capacités pour Shriek"


def _wotw(slot_data, received):
    from multitracker.goals import describe
    c = _ctx("Ori and the Will of the Wisps", slot_data, [], [])
    c.received = Counter(received)
    return {x["label"]: x for x in describe(c)["counters"]}


def test_ori_wotw_launch_comes_from_its_fragments():
    abilities = {"Sword": 1, "Double Jump": 1, "Dash": 1, "Bash": 1, "Glide": 1, "Burrow": 1}
    sd = {"goal_trees": True, "launch_frag": 5, "total_frag": 7}
    assert _wotw(sd, {**abilities, "Launch Fragment": 4})[WOTW_SHRIEK]["current"] == 6
    shriek = _wotw(sd, {**abilities, "Launch Fragment": 5})[WOTW_SHRIEK]
    assert shriek["current"] == 7 and "5 Launch Fragments" in shriek["detail"]
    # without the option, Launch is an item of its own
    assert _wotw({"goal_trees": True, "launch_frag": 0}, {**abilities, "Launch": 1})[WOTW_SHRIEK]["current"] == 7


def test_ori_wotw_relics_are_counted():
    sd = {"goal_relics": True, "relic_locs": [[0, 1], [1, 2], [2, 3]]}
    assert _wotw(sd, {"Relic": 2})["Reliques"] == {"label": "Reliques", "current": 2, "target": 3}
    assert "Reliques" not in _wotw({"goal_trees": True}, {"Relic": 2})


def test_sm64_bowser_stages_follow_their_key_checks():
    from multitracker.goals import describe
    keys = ["Bowser in the Dark World Key", "Bowser in the Fire Sea Key"]
    goal = describe(_ctx("Super Mario 64", {"StarsToFinish": 70, "CompletionType": 1}, keys, keys[:1]))
    steps = {s["label"]: s["done"] for s in goal["steps"]}
    assert steps["Bowser in the Dark World"] is True and steps["Bowser in the Fire Sea"] is False
    goal = describe(_ctx("Super Mario 64", {"StarsToFinish": 70, "CompletionType": 1}, [], []))
    assert {s["label"]: s["done"] for s in goal["steps"]}["Bowser in the Fire Sea"] is None


def test_mkdd_all_cup_tour_goal():
    from multitracker.goals import describe
    ctx = _ctx("Mario Kart Double Dash", {"trophy_requirement": 13, "all_cup_tour_min_cc": 1,
                                          "all_cup_tour_min_rank": 0},
               ["All Cup Tour Gold", "Trophy Goal Completed"], [])
    ctx.received = Counter({"Trophy": 4, "Progressive CC": 1})
    goal = describe(ctx)
    assert goal["summary"] == "13 trophées, puis l'All Cup Tour en or (100cc)"
    assert goal["counters"] == [{"label": "Trophées", "current": 4, "target": 13}]
    assert goal["steps"] == [{"label": "All Cup Tour débloqué", "done": False},
                             {"label": "100cc", "done": True},
                             {"label": "Gagner l'All Cup Tour", "done": False}]
    ctx.checked = {"All Cup Tour Gold"}
    assert describe(ctx)["steps"][-1]["done"] is True


def test_mkdd_trophies_goal_from_the_locations_and_the_yaml():
    from multitracker.goals import describe
    ctx = _ctx("Mario Kart Double Dash", {"trophy_requirement": 10, "all_cup_tour_min_cc": 2},
               ["Trophy Goal Completed"], ["Trophy Goal Completed"])
    goal = describe(ctx)
    assert goal["summary"] == "10 trophées"
    assert [s["label"] for s in goal["steps"]] == ["Objectif atteint"] and goal["steps"][0]["done"] is True
    ctx = _ctx("Mario Kart Double Dash", {}, [], [])
    ctx.yaml = {"goal": "all_cup_tour", "all_cup_tour_min_cc": "50cc"}
    goal = describe(ctx)
    assert goal["summary"] == "Trophées, puis l'All Cup Tour en or (50cc)"
    assert [s["label"] for s in goal["steps"]] == ["All Cup Tour débloqué", "Gagner l'All Cup Tour"]


def test_fall_guys_counts_final_round_tickets():
    from multitracker.goals import describe
    ctx = _ctx("Fall Guys", {"final_round_tickets_required": 30, "final_round_tickets_in_pool": 50},
               ["Win a Final Round", "Qualify in Tip Toe"], [])
    ctx.received = Counter({"Final Round Ticket": 12, "Beans": 3})
    goal = describe(ctx)
    assert goal["summary"] == "30 Final Round Tickets, puis gagner une finale"
    assert goal["counters"] == [{"label": "Final Round Tickets", "current": 12, "target": 30}]
    assert goal["steps"] == [{"label": "Gagner une finale (Win a Final Round)", "done": False}]
    ctx.checked = {"Win a Final Round"}
    assert describe(ctx)["steps"][-1]["done"] is True


def test_fall_guys_ticket_count_from_the_yaml():
    from multitracker.goals import describe
    ctx = _ctx("Fall Guys", {}, ["Win a Final Round"], [])
    ctx.yaml = {"final_round_tickets_required": 12}
    assert describe(ctx)["counters"][0]["target"] == 12


# Real shape of the Balatro mod's `balatro_deck_wins<slot>_<team>` (wins keyed by the index in the mod's stake pool,
# a Lua sequence arrives as a JSON list): included stakes White, Green, Red -> index 2 is Green, 3 is Red.
BALATRO_SD = {"goal": 3, "decks_win_goal": 7, "required_stake": 3, "included_stakes": [1, 3, 2]}
BALATRO_GREEN = ["Red", "Yellow", "Green", "Black", "Checkered", "Painted", "Erratic"]
BALATRO_PROFILE = {f"b_{d.lower()}": {"count": 0, "losses": {}, "wins": [None, 1]} for d in BALATRO_GREEN[:6]}
BALATRO_PROFILE |= {"b_erratic": {"count": 0, "losses": {}, "wins": [None, None, 1]},
                    "b_blue": {"count": 0, "losses": {}, "wins": {}}}


def _balatro(storage):
    ctx = _ctx("Balatro", BALATRO_SD, [], [f"{d} Deck Ante 8 Green Stake" for d in BALATRO_GREEN]
               + ["Erratic Deck Ante 8 Red Stake"])
    ctx.storage = storage
    from multitracker.goals import describe
    return describe(ctx)


def test_balatro_counts_the_wins_of_the_mod_profile_not_the_checks():
    # the Erratic Deck win on Green Stake was checked, but the mod's profile only has its Red Stake win: no goal
    goal = _balatro({"balatro_deck_wins122_0": BALATRO_PROFILE})
    assert goal["counters"] == [{"label": "Decks gagnants", "current": 6, "target": 7}]
    assert "Erratic Deck" in goal["note"] and "profil" in goal["note"]


def test_balatro_profile_wins_as_a_mapping_and_falls_back_on_the_checks():
    profile = {k: {"wins": {str(i + 1): v for i, v in enumerate(d["wins"]) if v}} for k, d in BALATRO_PROFILE.items()}
    profile["b_erratic"]["wins"]["2"] = 1  # won again on Green Stake
    goal = _balatro({"balatro_deck_wins122_0": profile})
    assert goal["counters"][0]["current"] == 7 and not goal.get("note")
    for storage in ({}, {"balatro_deck_wins122_0": None}):  # no copy on the server yet: the checks
        assert _balatro(storage)["counters"][0]["current"] == 7


def test_tracker_reads_the_balatro_mod_wins_from_data_storage():
    import asyncio
    from multitracker.ap.tracker import SlotTracker
    sent, changes = [], []
    t = SlotTracker("127.0.0.1:38291", "", "balatrom", "Balatro", None, on_change=lambda _t, k: changes.append(k))

    async def send(*msgs):
        sent.extend(msgs)
    t._send = send

    async def run():
        await t._handle({"cmd": "Connected", "team": 0, "slot": 122, "slot_info": {"122": {"game": "Balatro"}},
                         "players": [], "slot_data": BALATRO_SD})
        await t._handle({"cmd": "Retrieved", "keys": {"balatro_deck_wins122_0": BALATRO_PROFILE}})
        await t._handle({"cmd": "SetReply", "key": "balatro_deck_wins122_0", "value": {}})
    asyncio.run(run())
    get = next(m for m in sent if m["cmd"] == "Get")
    assert "balatro_deck_wins122_0" in get["keys"]
    assert next(m for m in sent if m["cmd"] == "SetNotify")["keys"] == get["keys"]
    assert "storage" in changes[1] and t.state.storage == {"balatro_deck_wins122_0": {}}
