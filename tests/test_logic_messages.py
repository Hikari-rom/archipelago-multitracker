"""Why a game has no logic, said to the player (no reference to the repo's files)."""
from __future__ import annotations

import asyncio


def test_no_logic_reasons():
    from multitracker.logic import LogicRequest
    from multitracker.logic.engine import UTLogicEngine, no_logic_reason
    assert no_logic_reason("Ocarina of Time", False).startswith("impossible pour Ocarina of Time")
    assert "pas encore assez fiable" in no_logic_reason("Ocarina of Time 2", True)
    assert "ne sait pas encore" in no_logic_reason("Musipelago", False)
    engine = UTLogicEngine({"Game A": False})  # never started: unavailable games do not reach the worker
    for game, part in (("Game A", "pas encore assez fiable"), ("Unknown", "ne sait pas encore")):
        res = asyncio.run(engine.compute(LogicRequest(slot_name="s", game=game, team=0, slot=1, slot_data={}, yaml=None,
                                                      items=[], missing=set(), checked=set())))
        assert res.state == "unavailable" and part in res.message
        assert "docs/" not in res.message and "restent suivis" in res.message


def test_yaml_messages_point_to_the_configuration_page():
    from multitracker.logic.ut_worker import YAML_NEEDED, yaml_missing
    assert "page Configuration" in YAML_NEEDED and "config/" not in YAML_NEEDED
    assert yaml_missing("/x/config/players/room/kuro.yaml").startswith("le yaml de ce slot est introuvable (kuro.yaml)")
