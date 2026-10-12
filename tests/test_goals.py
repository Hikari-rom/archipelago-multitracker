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
