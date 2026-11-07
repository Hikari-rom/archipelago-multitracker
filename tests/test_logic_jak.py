"""Jak and Daxter: every Power Cell received counts toward the connector levels, filler copies included."""
from __future__ import annotations

import pytest

from testenv_helpers import FIXTURES, generated_seed

GAME = "Jak and Daxter: The Precursor Legacy"


@pytest.fixture(scope="module")
def slot():
    import logic_reference as lr
    md = lr.load_multidata(generated_seed("jak_cells", 5, spoiler=1))
    player = next(iter(md["slot_info"]))
    from worlds.AutoWorld import AutoWorldRegister
    world_cls = AutoWorldRegister.world_types[GAME]
    fire_canyon = {code for name, code in world_cls.location_name_to_id.items() if name.startswith("FC: ")}
    return {"slot_data": lr.as_sent_by_server(md["slot_data"][player]), "locations": sorted(md["locations"][player]),
            "seed_name": md["seed_name"], "cell": world_cls.item_name_to_id["Power Cell"], "fire_canyon": fire_canyon}


def in_logic(slot, progression: int, filler: int) -> set[int]:
    """Logic with Power Cells sent by another player, as the server flags them (1: progression, 0: filler)."""
    from multitracker.logic.ut_worker import Worker
    items = [{"item": slot["cell"], "location": 9000 + i, "player": 2, "flags": 1 if i < progression else 0}
             for i in range(progression + filler)]
    res = Worker().handle({"op": "update", "slot_name": "Jak", "game": GAME, "team": 0, "slot": 1,
                           "slot_data": slot["slot_data"], "yaml": str(FIXTURES / "jak_cells" / "jak.yaml"),
                           "seed_name": slot["seed_name"], "items": items, "missing": slot["locations"],
                           "checked": []})
    assert res["state"] == "ok", res
    return set(res["in_logic"])


def test_filler_power_cells_open_fire_canyon(slot):
    """The real room: 25 cells received, 3 of them sent as filler, Fire Canyon needs 25. The game counts all 25."""
    assert slot["slot_data"]["fire_canyon_cell_count"] == 25
    assert not in_logic(slot, 24, 0) & slot["fire_canyon"]
    all_progression = in_logic(slot, 25, 0)
    assert all_progression & slot["fire_canyon"]
    assert in_logic(slot, 22, 3) == all_progression
