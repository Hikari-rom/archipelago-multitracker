from pathlib import Path

from multitracker.roomfeed.players import group_players, load_overrides

NAMES = ["romain_bw", "romain_kh2", "balatrom", "MaxFez", "MaxTD6", "MaxTruck", "MaxAccurate", "dashxcel",
         "dashxori_blind", "dashxportal", "experts@miami", "kuro_33", "kuro_TUNIC", "mathcroft_mc", "mariemme_dome",
         "menthe_isaac", "big_walkies", "Discapelago", "ash_tunic", "ash_paint"]


def test_auto_groups():
    g = group_players(NAMES)
    assert g["romain_bw"] == g["romain_kh2"] == "romain"
    assert g["MaxFez"] == g["MaxTD6"] == g["MaxTruck"] == g["MaxAccurate"] == "Max"
    assert g["dashxcel"] == g["dashxori_blind"] == g["dashxportal"] == "dashx"
    assert g["kuro_33"] == g["kuro_TUNIC"] == "kuro"
    assert g["ash_tunic"] == g["ash_paint"] == "ash"
    # different people sharing only one or two letters stay apart
    assert len({g["mathcroft_mc"], g["mariemme_dome"], g["menthe_isaac"], g["MaxFez"]}) == 4
    assert g["experts@miami"] == "experts@miami"
    assert g["balatrom"] == "balatrom"
    assert g["big_walkies"] == "big"
    assert g["Discapelago"] == "Discapelago"


def test_overrides_win():
    g = group_players(NAMES, {"balatrom": "romain", "unknown_slot": "x"})
    assert g["balatrom"] == "romain"
    assert "unknown_slot" not in g


def test_load_overrides(tmp_path: Path):
    p = tmp_path / "room_players.yaml"
    assert load_overrides(p) == {}
    p.write_text("# slot: joueur\nbalatrom: romain\nbad: [1, 2]\n", encoding="utf-8")
    assert load_overrides(p) == {"balatrom": "romain"}
    p.write_text(":::not yaml", encoding="utf-8")
    assert load_overrides(p) == {}


def test_load_overrides_tolerates_bad_encoding_and_odd_values(tmp_path):
    bad = tmp_path / "latin1.yaml"
    bad.write_bytes("Jérôme_x: jérôme\n".encode("latin-1"))
    assert load_overrides(bad) == {}
    odd = tmp_path / "odd.yaml"
    odd.write_text("a: true\nb: ' bob '\nc: 7\n", encoding="utf-8")
    assert load_overrides(odd) == {"b": "bob", "c": "7"}


def test_label_casing_comes_from_the_cluster_itself():
    assert group_players(["AB", "abc", "ab_x"])["abc"] == "abc"
