"""Player yaml preparation for the regeneration (no server needed)."""
from pathlib import Path

import yaml

from multitracker.logic.ut_worker import _is_random, prepare_player_yaml


def test_is_random():
    assert _is_random("random")
    assert _is_random("random-high")
    assert _is_random({"on": 50, "off": 50})
    assert not _is_random({"on": 0, "off": 50})
    assert not _is_random("easy")
    assert not _is_random({"Strawberry": 3})  # a plain dict option (e.g. start inventory) isn't weights
    assert not _is_random(12)


def test_prepare_player_yaml_resolves_random_options_from_slot_data(tmp_path: Path):
    src = tmp_path / "in.yaml"
    src.write_text(yaml.safe_dump_all([
        {"name": "Other{number}", "game": "Super Mario 64", "Super Mario 64": {}},
        {"name": "Me{number}", "game": "Celeste (Open World)",
         "Celeste (Open World)": {"goal_area": "random", "lock_goal_area": {"true": 1, "false": 1},
                                  "some_unknown": "random", "progression_balancing": "random"}},
    ]))
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    out, still_random = prepare_player_yaml(src, "Romain_Celeste", "Celeste (Open World)", out_dir,
                                            slot_data={"goal_area": 3}, option_names={"goal_area", "lock_goal_area"})
    doc = yaml.safe_load(out.read_text())
    assert doc["name"] == "Romain_Celeste" and doc["game"] == "Celeste (Open World)"
    assert doc["Celeste (Open World)"]["goal_area"] == 3
    assert sorted(still_random) == ["lock_goal_area", "some_unknown"]
