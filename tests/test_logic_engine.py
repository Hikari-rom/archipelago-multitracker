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
        assert res.state == "unavailable" and "pas encore assez fiable" in res.message
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
    req["checksum"] = ""  # the room did not say: refused too
    assert "n'indique pas" in Worker().handle(req)["message"]
    import worlds
    req["checksum"] = worlds.network_data_package["games"]["Kingdom Hearts 2"]["checksum"]
    assert "yaml" in Worker().handle(req)["message"]  # same version: goes on (and needs the yaml)


def test_user_apworld_refusal_says_what_to_do():
    """D27: Blue Prince's apworld comes from the player's own Archipelago. Missing (CI) or of another version than the
    room's, the reason tells how to fix it."""
    from multitracker.logic.ut_worker import Worker
    res = Worker().handle({"op": "update", "slot_name": "ash_blue", "game": "Blue Prince", "team": 0, "slot": 1,
                           "slot_data": {}, "yaml": None, "items": [], "missing": [1], "checked": [],
                           "checksum": "0" * 40})
    assert res["state"] == "unavailable" and "importe" in res["message"], res


_ = pytest


def test_region_names_sent_to_the_app_are_plain_strings():
    """AEMinecraft names its regions with a str Enum: pickled as is, the app process cannot load them."""
    import pickle
    from enum import Enum
    from multitracker.logic.ut_worker import plain_name

    class Region(str, Enum):
        OVERWORLD = "Overworld"

    name = plain_name(Region.OVERWORLD)
    assert name == "Overworld" and type(name) is str
    assert type(pickle.loads(pickle.dumps(name))) is str
    assert plain_name("Nether") == "Nether"


def test_world_loading_noise_is_summarized():
    """Tracebacks of core worlds that cannot load here and manifest warnings become one summary line."""
    import logging
    from multitracker.logic.ut_worker import world_loading_summary
    root = logging.getLogger()
    messages: list[str] = []

    class Keep(logging.Handler):
        def emit(self, record):
            messages.append(record.getMessage())

    keep, level = Keep(), root.level
    root.addHandler(keep)
    root.setLevel(logging.INFO)
    try:
        with world_loading_summary():
            try:
                raise ModuleNotFoundError("No module named 'zilliandomizer'")
            except ModuleNotFoundError:
                root.exception("Could not load world WorldSource(zillion, is_zip=False, relative=True):")
            root.error("Invalid or missing manifest file for /x/custom_worlds/balatro.apworld. This apworld will "
                       "stop working with Archipelago 0.7.0.")
            root.error("compatible_version - This might be the incorrect world version for this file")
            root.warning("something unexpected")
    finally:
        root.removeHandler(keep)
        root.setLevel(level)
    assert "something unexpected" in messages
    summary = [m for m in messages if m.startswith("Archipelago worlds:")]
    assert len(summary) == 1 and "zillion" in summary[0] and "balatro" in summary[0]
    assert not any("Could not load world" in m or "compatible_version" in m for m in messages)


async def test_local_checksums_survive_a_restart():
    from multitracker.logic.engine import UTLogicEngine
    engine = UTLogicEngine({"Super Mario 64": True}, timeout=120)
    await engine.start()
    try:
        first = await engine.checksums(["Super Mario 64", "Nope"])
        assert isinstance(first["Super Mario 64"], str) and first["Nope"] is None
        await engine.stop()  # what an apworld import does (Service.restart_logic)
        await engine.start()
        assert await engine.checksums(["Super Mario 64"]) == {"Super Mario 64": first["Super Mario 64"]}
    finally:
        await engine.stop()
