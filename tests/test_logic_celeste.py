"""Celeste (Open World): the logic follows the room's slot_data even with the yaml of another room."""
from __future__ import annotations

import pytest

from testenv_helpers import FIXTURES, generated_seed

# Romain's yaml of his first room: no roomsanity, The Summit A goal, 50 strawberries.
STALE_YAML = """name: Celeste
game: Celeste (Open World)
Celeste (Open World):
  goal_area: the_summit_a
  include_core: false
  roomsanity: false
  total_strawberries: 50
  strawberries_required_percentage: 80
"""


@pytest.fixture(scope="module")
def slot():
    import logic_reference as lr
    md = lr.load_multidata(generated_seed("celeste_rooms", 3, spoiler=1))
    player = next(iter(md["slot_info"]))
    return {"slot_data": lr.as_sent_by_server(md["slot_data"][player]), "locations": sorted(md["locations"][player]),
            "seed_name": md["seed_name"]}


def update(slot, yaml_path, slot_data):
    from multitracker.logic.ut_worker import Worker
    return Worker().handle({"op": "update", "slot_name": "Celeste", "game": "Celeste (Open World)", "team": 0,
                            "slot": 1, "slot_data": slot_data, "yaml": str(yaml_path), "seed_name": slot["seed_name"],
                            "items": [], "missing": slot["locations"], "checked": []})


def test_stale_yaml_gives_the_same_logic_as_the_room_yaml(slot, tmp_path):
    stale = tmp_path / "celeste.yaml"
    stale.write_text(STALE_YAML)
    own = update(slot, FIXTURES / "celeste_rooms" / "celeste.yaml", slot["slot_data"])
    got = update(slot, stale, slot["slot_data"])
    assert own["state"] == got["state"] == "ok"
    assert len(own["in_logic"]) > 20
    assert got["in_logic"] == own["in_logic"]
    assert not got.get("errors")


def test_world_without_the_slot_locations_is_reported(slot, tmp_path):
    """Without the options in slot_data (adapter skipped) the stale yaml builds a world without the room
    locations: the result says so instead of silently under-estimating."""
    stale = tmp_path / "celeste.yaml"
    stale.write_text(STALE_YAML)
    res = update(slot, stale, {k: v for k, v in slot["slot_data"].items() if k != "roomsanity"})
    assert res["state"] == "ok"
    assert any("manquent au monde recalculé" in e for e in res["errors"]), res.get("errors")
