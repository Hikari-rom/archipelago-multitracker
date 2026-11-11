"""Goals of the room's other games (goals_room.py): every describer runs, and a few rules checked by hand."""
from __future__ import annotations

import re
from collections import Counter
from pathlib import Path

import pytest

from multitracker.goals import DESCRIBERS, GoalContext, describe, yaml_options
from multitracker.goals_room import ROOM_DESCRIBERS

ROOT = Path(__file__).resolve().parent.parent
VALIDATION = ROOT / "test-output" / "logic_validation"


def ctx(game: str, slot_data=None, yaml=None, received=(), checked=(), locations=()) -> GoalContext:
    locs = set(locations) | set(checked)
    return GoalContext(game=game, slot_data=slot_data or {}, yaml=yaml or {}, received=Counter(received),
                       checked=set(checked), locations=locs, goal=False)


def test_room_describers_are_registered():
    for game, fn in ROOM_DESCRIBERS.items():
        assert DESCRIBERS[game] is fn


@pytest.mark.parametrize("game", sorted(ROOM_DESCRIBERS))
def test_room_describer_without_any_data(game):
    """A slot of another player with no slot_data and no yaml yet: a goal is still described, nothing done."""
    out = describe(ctx(game))
    assert out["summary"] and "non décrit" not in out["summary"]
    assert out["counters"] or out["steps"]
    for counter in out["counters"]:
        assert counter["current"] == 0
    assert not any(step["done"] for step in out["steps"])


def slug(game: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", game.lower()).strip("_")


def seed_contexts(game: str):
    """Empty and full GoalContext of the game's slots in the last generated validation seed (if any)."""
    import logic_reference as lr
    zips = sorted((VALIDATION / slug(game)).glob("run*/out/*.zip"), key=lambda p: p.stat().st_mtime)
    if not zips:
        return
    md = lr.load_multidata(zips[-1])
    for slot, info in md["slot_info"].items():
        if info.game != game:
            continue
        dp = md["datapackage"][game]
        items = {v: k for k, v in dp["item_name_to_id"].items()}
        locs = {v: k for k, v in dp["location_name_to_id"].items()}
        pre = Counter(items.get(i, i) for i in md["precollected_items"][slot])
        full = Counter(pre)
        for player_locs in md["locations"].values():
            for item, player, _flags in player_locs.values():
                if player == slot:
                    full[items.get(item, item)] += 1
        names = {locs.get(loc, str(loc)) for loc in md["locations"][slot]}
        yp = next((p for p in zips[-1].parent.parent.glob("players/*.yaml")
                   if re.search(rf"^game:\s*['\"]?{re.escape(game)}", p.read_text(errors="ignore"), re.M)), None)
        y = yaml_options(yp, game)
        sd = md["slot_data"][slot] or {}
        yield (GoalContext(game=game, slot_data=sd, yaml=y, received=pre, checked=set(), locations=names, goal=False),
               GoalContext(game=game, slot_data=sd, yaml=y, received=full, checked=set(names), locations=names,
                           goal=False))


@pytest.mark.parametrize("game", sorted(ROOM_DESCRIBERS))
def test_room_describer_on_a_generated_seed(game):
    """With everything received and checked, every counter is full (the goal itself stays with the server)."""
    found = False
    for empty, full in seed_contexts(game) or ():
        found = True
        e, f = describe(empty), describe(full)
        assert e["summary"] == f["summary"]
        for counter in f["counters"]:
            assert counter["target"] is None or counter["current"] <= counter["target"], counter
        assert [c["label"] for c in e["counters"]] == [c["label"] for c in f["counters"]]
    if not found:
        pytest.skip("no validation seed generated for this game")


def test_trombone_champ_counts_beaten_tracks_and_rank_reductions():
    sd = {"goal": 3, "goal_track": "none", "rating": 2, "rating_start": 5}
    out = describe(ctx("Trombone Champ", sd, received={"Rank Reduction": 1},
                       checked={"Beat: A", "Beat: B", "Play: C"}, locations={"Beat: C"}))
    assert out["summary"] == "Battre 3 morceaux"
    assert [(c["label"], c["current"], c["target"]) for c in out["counters"]] == [
        ("Morceaux battus", 2, 3), ("Rank Reductions", 1, 3)]


def test_trombone_champ_goal_track_needs_hot_dogs():
    out = describe(ctx("Trombone Champ", {"goal": 0, "goal_track": "Warm-up", "hot_dogs": 4},
                       received={"Hot Dog": 6}))
    assert out["summary"] == "Battre le morceau du but (Warm-up)"
    assert out["counters"] == [{"label": "Hot Dogs", "current": 4, "target": 4}]


def test_zuma_deluxe_goal_level_unlock_and_sun_idols():
    sd = {"adventure_goal": "Space - Stage 13", "sun_idols_required_amount": 5}
    out = describe(ctx("Zuma Deluxe", sd, received={"Sun Idol": 2, "Stage Unlock: Stage 13": 1}))
    assert out["summary"] == "Battre Space - Stage 13"
    assert out["counters"] == [{"label": "Sun Idols", "current": 2, "target": 5}]
    assert out["steps"][0] == {"label": "Niveau du but débloqué", "done": True}


def test_shapez_vanilla_counts_levels_before_26():
    checked = {f"Level {i}" for i in range(1, 11)} | {"Level 1 Additional", "Belt Upgrade Tier II"}
    out = describe(ctx("shapez", {"goal": "vanilla"}, checked=checked,
                       locations={f"Level {i}" for i in range(1, 26)}))
    assert out["summary"] == "Terminer le niveau 26"
    assert out["counters"] == [{"label": "Niveaux terminés", "current": 10, "target": 25}]


def test_witness_mountain_lasers_from_items_when_shuffled():
    sd = {"victory_condition": 0, "mountain_lasers": 7, "shuffle_lasers": 1}
    out = describe(ctx("The Witness", sd, received={"Symmetry Laser": 1, "Desert Laser": 1, "Speed Boost": 3}))
    assert out["counters"] == [{"label": "Lasers reçus", "current": 2, "target": 7}]
    sd["shuffle_lasers"] = 0
    assert describe(ctx("The Witness", sd))["steps"][0]["done"] is None


def test_vvvvvv_needs_the_trinkets_of_the_four_areas():
    out = describe(ctx("VVVVVV", {"DoorCost": 2}, received={"Trinket 01": 1, "Trinket 08": 1, "Trinket 09": 1}))
    assert out["counters"] == [{"label": "Trinkets des zones", "current": 2, "target": 8}]
