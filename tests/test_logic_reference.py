"""M5 reference comparison on the multi5 test seed: the app's logic equals the full-multiworld logic
at every sphere of the playthrough, for every slot. (TEST CODE: uses multidata + regeneration.)
Randomized-option campaigns: scripts/testenv/validate_logic.py / campaign.sh (results in docs/COMPAT.md)."""
import pytest
import yaml

from testenv_helpers import FIXTURES, generated_seed


@pytest.fixture(scope="module")
def seed():
    import logic_reference as lr
    zip_path = generated_seed("multi5", 42)
    multidata = lr.load_multidata(zip_path)
    multiworld = lr.regenerate("multi5", 42)
    lr.check_same_fill(multiworld, multidata)
    return multiworld, multidata


@pytest.fixture(scope="module")
def tool():
    import logic_reference as lr
    with lr.ToolProcess() as proc:
        yield proc


@pytest.mark.parametrize("slot", ["Celeste", "KH2", "Jak", "TWWHD", "SM64"])
def test_logic_matches_reference_at_every_sphere(seed, tool, slot):
    import logic_reference as lr
    multiworld, multidata = seed
    yamls = {yaml.safe_load(p.read_text())["name"]: p for p in (FIXTURES / "multi5").glob("*.yaml")}
    player = next(p for p in multiworld.player_ids if multiworld.player_name[p] == slot)
    report = lr.compare_slot(multiworld, multidata, player, yamls[slot], tool=tool)
    assert not report.get("error"), report.get("error")
    bad = [s for s in report["snapshots"] if s["under"] or s["over"]]
    assert not bad, bad[:3]
    assert len(report["snapshots"]) > 5


def test_start_inventory_keeps_world_classification():
    from BaseClasses import ItemClassification as IC
    from multitracker.logic.ut_worker import exact_classification
    # demoted by the generator: the server's flags win
    assert exact_classification(IC.progression, 0, IC) == IC.filler
    # promoted / exact
    assert exact_classification(IC.filler, 1, IC) == IC.progression
    # extra bits only kept for progression items
    assert exact_classification(IC.progression_skip_balancing, 1, IC) == IC.progression_skip_balancing
    assert exact_classification(IC.progression_skip_balancing, 2, IC) == IC.useful
