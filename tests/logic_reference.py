"""Reference logic for validation (TEST CODE ONLY: uses the full generation multiworld and multidata).

For a generated test seed, replays the playthrough sphere by sphere and, for each slot, compares
- the locations the app's logic engine (Universal Tracker, regenerated from yaml/slot_data only)
  says are in logic, with
- the locations reachable in the *full generation multiworld* for the same received items.
"""
from __future__ import annotations

import json
import os
import zipfile
import zlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from testenv_helpers import FIXTURES, ROOT

from multitracker import apenv


def load_multidata(zip_path: Path) -> dict[str, Any]:
    apenv.setup()
    from Utils import restricted_loads
    with zipfile.ZipFile(zip_path) as zf:
        name = next(n for n in zf.namelist() if n.endswith(".archipelago"))
        data = zf.read(name)
    return restricted_loads(zlib.decompress(data[1:]))


def regenerate(fixture: str, seed: int):
    """Re-run the generation of tests/fixtures/<fixture> in-process (same seed => same fill)."""
    apenv.setup()
    os.chdir(apenv.AP_DIR)
    import Generate
    import Main
    players = FIXTURES / fixture
    argv = ["--player_files_path", str(players), "--outputpath", str(ROOT / "test-output" / "regen"),
            "--multi", str(len(list(players.glob("*.yaml")))), "--seed", str(seed), "--skip_output",
            "--spoiler", "0"]
    erargs, seed = Generate.main(Generate.mystery_argparse(argv))
    return Main.main(erargs, seed)


def check_same_fill(multiworld, multidata: dict[str, Any]) -> None:
    for player, locations in multidata["locations"].items():
        for address, (item_code, item_player, _flags) in locations.items():
            loc = multiworld.get_location(multiworld.worlds[player].location_id_to_name[address], player)
            assert loc.item.code == item_code and loc.item.player == item_player, \
                f"regenerated multiworld differs from the hosted seed at {loc}"


@dataclass
class Snapshot:
    sphere: int
    received: list  # Location objects whose item was received
    items: list[dict[str, Any]] = field(default_factory=list)  # as the server would send them
    checked: set[int] = field(default_factory=set)
    missing: set[int] = field(default_factory=set)


def snapshots(multiworld, player: int) -> list[Snapshot]:
    """State of `player` at the start of each sphere of the playthrough."""
    all_addresses = {loc.address for loc in multiworld.get_locations(player) if loc.address is not None}
    precollected = [{"item": it.code, "location": -2, "player": 0, "flags": int(it.classification)}
                    for it in multiworld.precollected_items[player] if it.code is not None]
    spheres = [list(s) for s in multiworld.get_spheres()]
    result: list[Snapshot] = []
    received, checked = [], set()
    for index in range(len(spheres) + 1):
        items = precollected + [{"item": loc.item.code, "location": loc.address, "player": loc.player,
                                 "flags": int(loc.item.classification)} for loc in received]
        result.append(Snapshot(index, list(received), items, set(checked), all_addresses - checked))
        if index == len(spheres):
            break
        for loc in spheres[index]:
            if loc.address is None:
                continue
            if loc.player == player:
                checked.add(loc.address)
            if loc.item is not None and loc.item.player == player and loc.item.code is not None:
                received.append(loc)
    return result


def reference_in_logic(multiworld, player: int, snap: Snapshot) -> set[int]:
    from BaseClasses import CollectionState
    state = CollectionState(multiworld)
    for loc in snap.received:
        state.collect(loc.item, True, loc)
    state.sweep_for_advancements(locations=[loc for loc in multiworld.get_locations(player) if loc.address is None])
    return {loc.address for loc in multiworld.get_reachable_locations(state, player)
            if loc.address is not None and loc.address in snap.missing}


def compare_slot(multiworld, multidata: dict[str, Any], player: int, yaml_path: Path | None,
                 max_snapshots: int | None = None) -> dict[str, Any]:
    from multitracker.logic.ut_worker import SlotLogic
    name = multiworld.player_name[player]
    game = multiworld.game[player]
    logic = SlotLogic(name, game, 0, player, multidata["slot_data"][player], yaml_path)
    snaps = snapshots(multiworld, player)
    if max_snapshots and len(snaps) > max_snapshots:
        step = (len(snaps) - 1) / (max_snapshots - 1)
        snaps = [snaps[round(i * step)] for i in range(max_snapshots)]
    loc_name = multiworld.worlds[player].location_id_to_name
    report = {"slot": name, "game": game, "mode": logic.mode, "snapshots": []}
    for snap in snaps:
        ref = reference_in_logic(multiworld, player, snap)
        got = set(logic.in_logic(snap.items, snap.missing)["in_logic"])
        report["snapshots"].append({
            "sphere": snap.sphere, "items": len(snap.items), "reference": len(ref), "tool": len(got),
            "under": sorted(loc_name[a] for a in ref - got),  # in logic but the tool misses it
            "over": sorted(loc_name[a] for a in got - ref),   # the tool says in logic but it is not
        })
    report["ok"] = all(not s["under"] and not s["over"] for s in report["snapshots"])
    return report


def write_report(fixture: str, reports: list[dict[str, Any]]) -> Path:
    out = ROOT / "test-output" / "logic_reference" / f"{fixture}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(reports, indent=2, ensure_ascii=False), encoding="utf-8")
    return out
