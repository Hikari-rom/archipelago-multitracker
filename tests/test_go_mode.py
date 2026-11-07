"""Go mode: the victory is reachable with the items received (worker `goal_in_logic`, D34).
(TEST CODE: compares with the full multiworld, like test_logic_reference.py.)"""
import pytest
import yaml

from testenv_helpers import FIXTURES, generated_seed


@pytest.fixture(scope="module")
def tool():
    import logic_reference as lr
    with lr.ToolProcess() as proc:
        yield proc


def test_default_completion_condition_is_not_a_victory():
    from multitracker import apenv
    from multitracker.logic.ut_worker import has_real_completion
    apenv.setup()
    from BaseClasses import MultiWorld
    mw = MultiWorld(1)
    assert not has_real_completion(mw.completion_condition[1])
    assert has_real_completion(lambda state: state.has("Victory", 1))


def test_fall_guys_go_mode_with_the_tickets_of_natazox(tool):
    """Natazox's yaml (30 tickets out of 50, qualifysanity 1000): go mode exactly when the final is in logic."""
    import logic_reference as lr
    zip_path = generated_seed("m34_fallguys", 3, spoiler=1)
    multidata = lr.load_multidata(zip_path)
    multiworld = lr.regenerate("m34_fallguys", 3)
    lr.check_same_fill(multiworld, multidata)
    path = FIXTURES / "m34_fallguys" / "natazox_fall.yaml"
    report = lr.compare_slot(multiworld, multidata, 1, path, max_snapshots=40, tool=tool)
    assert not report.get("error"), report.get("error")
    snaps = report["snapshots"]
    assert not [s for s in snaps if s["under"] or s["over"]], snaps[:2]
    assert not [s for s in snaps if s["goal_over"] or s["goal_under"]], [
        (s["sphere"], s["goal_tool"], s["goal_reference"]) for s in snaps]
    assert snaps[0]["goal_tool"] is False and snaps[-1]["goal_tool"] is True


@pytest.mark.parametrize("slot", ["Celeste", "KH2", "Jak", "TWWHD", "SM64"])
def test_go_mode_matches_the_reference(tool, slot):
    import logic_reference as lr
    zip_path = generated_seed("multi5", 42)
    multidata = lr.load_multidata(zip_path)
    multiworld = lr.regenerate("multi5", 42)
    yamls = {yaml.safe_load(p.read_text())["name"]: p for p in (FIXTURES / "multi5").glob("*.yaml")}
    player = next(p for p in multiworld.player_ids if multiworld.player_name[p] == slot)
    report = lr.compare_slot(multiworld, multidata, player, yamls[slot], tool=tool)
    snaps = report["snapshots"]
    assert not [s for s in snaps if s["goal_over"] or s["goal_under"]], [
        (s["sphere"], s["goal_tool"], s["goal_reference"]) for s in snaps]
    assert snaps[0]["goal_tool"] is False and snaps[-1]["goal_tool"] is True


async def test_service_go_mode(tmp_path, monkeypatch):
    from multitracker.config import RoomConfig, SlotConfig
    from multitracker.logic import LogicResult
    from multitracker import service as service_mod
    from multitracker.service import Service
    from multitracker.store import Store

    monkeypatch.setattr(service_mod, "go_mode_disabled", lambda: {"GameB"})
    service = Service(RoomConfig(server="127.0.0.1:1", slots=[SlotConfig("a", "GameA"), SlotConfig("b", "GameB")]),
                      Store(tmp_path / "db.sqlite3"), reconnect_delays=(0.3, 1.0))
    await service.start()
    try:
        state = service.trackers["a"].state
        state.missing = {1, 2}
        service.logic["a"] = LogicResult("ok", in_logic=[], goal_in_logic=True)
        assert service.go_mode("a") is True
        assert service._bk_of("a") is False  # nothing left in logic, but the victory is: not BK
        assert service.summary("a")["go_mode"] is True
        service.logic["a"] = LogicResult("ok", in_logic=[1], goal_in_logic=None)
        assert service.go_mode("a") is False
        service.logic["a"] = LogicResult("error", goal_in_logic=True)
        assert service.go_mode("a") is False
        service.logic["a"] = LogicResult("ok", goal_in_logic=True)
        state.client_status = 30  # goal reached: gold, not go mode
        assert service.go_mode("a") is False
        service.trackers["b"].state.missing = {1}
        service.logic["b"] = LogicResult("ok", goal_in_logic=True)
        assert service.go_mode("b") is False  # go_mode: false in config/apworlds.yaml
    finally:
        await service.stop()
