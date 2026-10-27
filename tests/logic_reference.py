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
        # by address: a world may name a location differently from its datapackage (Cookie Clicker's victory)
        by_address = {loc.address: loc for loc in multiworld.get_locations(player) if loc.address is not None}
        for address, (item_code, item_player, _flags) in locations.items():
            loc = by_address.get(address)
            assert loc is not None, f"regenerated multiworld has no location {address} of player {player}"
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
    # The server sends the start inventory with location -2, player 0 and flags 0 (MultiServer.get_start_inventory)
    precollected = [{"item": it.code, "location": -2, "player": 0, "flags": 0}
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


class ToolProcess:
    """The app's logic worker, in its own spawned process (exactly like the app runs it), so that the
    tool and the reference can never share in-process state (class attributes, patched methods...)."""

    def __init__(self) -> None:
        import multiprocessing as mp
        from multitracker.logic.ut_worker import worker_main
        ctx = mp.get_context("spawn")
        self.conn, child = ctx.Pipe()
        self.proc = ctx.Process(target=worker_main, args=(child,), daemon=True)
        self.proc.start()
        child.close()

    def request(self, req: dict[str, Any]) -> dict[str, Any]:
        self.conn.send(req)
        if not self.conn.poll(600):
            raise TimeoutError("logic worker did not answer")
        return self.conn.recv()

    def close(self) -> None:
        try:
            self.conn.send(None)
        except OSError:
            pass
        self.proc.join(10)
        if self.proc.is_alive():
            self.proc.kill()

    def __enter__(self) -> "ToolProcess":
        return self

    def __exit__(self, *exc) -> None:
        self.close()


def as_sent_by_server(value: Any) -> Any:
    """What a client receives: the server encodes with NetUtils.encode, then JSON travels the websocket."""
    from NetUtils import encode
    return json.loads(encode(value))


def compare_slot(multiworld, multidata: dict[str, Any], player: int, yaml_path: Path | None,
                 max_snapshots: int | None = None, tool: ToolProcess | None = None) -> dict[str, Any]:
    own_tool = tool is None
    tool = tool or ToolProcess()
    try:
        name = multiworld.player_name[player]
        game = multiworld.game[player]
        snaps = snapshots(multiworld, player)
        if max_snapshots and len(snaps) > max_snapshots:
            step = (len(snaps) - 1) / (max_snapshots - 1)
            snaps = [snaps[round(i * step)] for i in range(max_snapshots)]
        all_locations = {loc.address for loc in multiworld.get_locations(player) if loc.address is not None}
        slot_data = as_sent_by_server(multidata["slot_data"][player])
        loc_name = multiworld.worlds[player].location_id_to_name
        report = {"slot": name, "game": game, "mode": None, "snapshots": []}
        for snap in snaps:
            ref = reference_in_logic(multiworld, player, snap)
            res = tool.request(as_sent_by_server({
                "op": "update", "slot_name": name, "game": game, "team": 0, "slot": player,
                "slot_data": slot_data, "yaml": str(yaml_path) if yaml_path else None,
                "seed_name": multiworld.seed_name, "items": snap.items, "missing": sorted(snap.missing),
                "checked": sorted(all_locations - snap.missing)}))
            if res.get("state") != "ok":
                report["error"] = res.get("message")
                report["ok"] = False
                return report
            report["mode"] = res.get("mode")
            report["note"] = res.get("note")  # logic knowingly late for this slot (adapters.LOGIC_NOTES)
            foreign = [e for e in res.get("errors") or [] if "manquent au monde recalculé" in e]
            if foreign:  # the regenerated world lacks locations of the slot: not the same options
                report["error"] = foreign[0]
                report["ok"] = False
                return report
            got = set(res["in_logic"])
            report["snapshots"].append({
                "sphere": snap.sphere, "items": len(snap.items), "reference": len(ref), "tool": len(got),
                "under": sorted(loc_name[a] for a in ref - got),  # in logic but the tool misses it
                "over": sorted(loc_name[a] for a in got - ref),   # the tool says in logic but it is not
            })
        report["ok"] = all(not s["under"] and not s["over"] for s in report["snapshots"])
        return report
    finally:
        if own_tool:
            tool.close()


def write_report(fixture: str, reports: list[dict[str, Any]]) -> Path:
    out = ROOT / "test-output" / "logic_reference" / f"{fixture}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(reports, indent=2, ensure_ascii=False), encoding="utf-8")
    return out
