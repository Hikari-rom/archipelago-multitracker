"""Logic engine process management (no AP server needed)."""
import os
import signal

import pytest

from testenv_helpers import FIXTURES


def request(slot_data=None):
    from multitracker.logic import LogicRequest
    return LogicRequest(slot_name="SM64", game="Super Mario 64", team=0, slot=1, slot_data=slot_data or {},
                        yaml=FIXTURES / "multi5" / "sm64.yaml", items=[], missing={3626000, 3626001},
                        checked=set(), seed_name="test")


async def test_worker_crash_is_recovered():
    from multitracker.logic.engine import UTLogicEngine
    engine = UTLogicEngine({"Super Mario 64": True}, timeout=120)
    await engine.start()
    try:
        first = await engine.compute(request())
        assert first.state == "ok", first.message
        os.kill(engine._proc.pid, signal.SIGKILL)  # the worker dies (OOM, crash...)
        engine._proc.join(5)
        again = await engine.compute(request())  # respawned transparently
        assert again.state == "ok", again.message
        assert again.in_logic == first.in_logic
    finally:
        await engine.stop()


async def test_disabled_and_unknown_games():
    from multitracker.logic.engine import UTLogicEngine
    engine = UTLogicEngine({"Super Mario 64": False}, timeout=120)
    await engine.start()
    try:
        res = await engine.compute(request())
        assert res.state == "unavailable" and "validée" in res.message
        engine.games["Nope"] = True
        req = request()
        req.game = "Nope"
        res = await engine.compute(req)
        assert res.state == "unavailable" and "apworld" in res.message
    finally:
        await engine.stop()


def test_missing_yaml_for_a_yaml_world():
    from multitracker.logic.ut_worker import Worker
    res = Worker().handle({"op": "update", "slot_name": "KH2", "game": "Kingdom Hearts 2", "team": 0, "slot": 1,
                           "slot_data": {}, "yaml": None, "items": [], "missing": [1], "checked": []})
    assert res["state"] == "unavailable" and "yaml" in res["message"]



def test_other_apworld_version_in_the_room():
    """D12: the room was generated with another version of the apworld (other datapackage checksum)."""
    from multitracker.logic.ut_worker import Worker
    req = {"op": "update", "slot_name": "KH2", "game": "Kingdom Hearts 2", "team": 0, "slot": 1,
           "slot_data": {}, "yaml": None, "items": [], "missing": [1], "checked": [], "checksum": "0" * 40}
    res = Worker().handle(req)
    assert res["state"] == "unavailable" and "autre version" in res["message"]
    import worlds
    req["checksum"] = worlds.network_data_package["games"]["Kingdom Hearts 2"]["checksum"]
    assert "yaml" in Worker().handle(req)["message"]  # same version: goes on (and needs the yaml)


_ = pytest
