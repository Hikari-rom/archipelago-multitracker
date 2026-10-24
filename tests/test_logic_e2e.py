"""M5 end to end: the bot only checks what the API says is in logic, for every slot, until every goal.

If the bot gets stuck before the seed is finished, the logic under-estimates. (TEST CODE: the
full generation multiworld is used only to decide when a slot has reached its goal.)
"""
from __future__ import annotations

import asyncio
import json
import socket
from pathlib import Path

import httpx
import pytest
import uvicorn
import yaml

from testenv_helpers import FIXTURES, ROOT, generated_seed, start_server, stop_server

PORT = 38287
pytestmark = pytest.mark.asyncio


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def full_state(multiworld, player: int, items: list[dict]):
    from BaseClasses import CollectionState
    state = CollectionState(multiworld)
    # by address: a world may name a location differently from its datapackage (Cookie Clicker "Victory location")
    by_address = {(l.player, l.address): l for l in multiworld.get_locations() if l.address is not None}
    for net in items:
        if net["location"] < 0 or net["player"] == 0:
            continue
        loc = by_address[(net["player"], net["location"])]
        state.collect(loc.item, True, loc)
    state.sweep_for_advancements(locations=[l for l in multiworld.get_locations(player) if l.address is None])
    return state


def goal_reached(multiworld, player: int, items: list[dict]) -> bool:
    return multiworld.has_beaten_game(full_state(multiworld, player, items), player)


def reference_todo(multiworld, player: int, items: list[dict], missing: set[int]) -> list[str]:
    state = full_state(multiworld, player, items)
    return sorted(l.name for l in multiworld.get_reachable_locations(state, player)
                  if l.address is not None and l.address in missing)


async def play_until_done(fixture: str, seed: int, tmp_path: Path, max_rounds: int = 300, spoiler: int = 3,
                          no_yaml: frozenset[str] = frozenset()) -> dict:
    """no_yaml: games whose slots get no yaml (logic from slot_data only, like another player's slot)."""
    import logic_reference as lr
    from bot import GameBot
    from multitracker import config
    from multitracker.api import create_app
    from multitracker.logic.engine import UTLogicEngine
    from multitracker.service import Service
    from multitracker.store import Store

    zip_path = generated_seed(fixture, seed, spoiler=spoiler)
    multiworld = lr.regenerate(fixture, seed)
    lr.check_same_fill(multiworld, lr.load_multidata(zip_path))
    players = {}
    for path in (FIXTURES / fixture).glob("*.yaml"):
        doc = yaml.safe_load(path.read_text())
        players[doc["name"]] = (doc["game"], path)
    room = tmp_path / "room.yaml"
    room.write_text(json.dumps({"server": f"ws://127.0.0.1:{PORT}", "password": "test",
                                "slots": [{"name": n, "game": g, "yaml": None if g in no_yaml else str(p)}
                                          for n, (g, p) in players.items()]}))
    engine = UTLogicEngine({g: True for g, _ in players.values()})
    service_box = {}

    def factory():
        service_box["s"] = Service(config.load(room), Store(tmp_path / "db.sqlite3"), engine,
                                   logic_debounce=0.2, publish_debounce=0.05, reconnect_delays=(0.3, 1.0))
        return service_box["s"]

    start_server(zip_path, PORT)
    app = create_app(factory, frontend_dist=None)
    port = free_port()
    uv = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning"))
    task = asyncio.create_task(uv.serve())
    bots: dict[str, GameBot] = {}
    history = []
    retries = 0  # rounds without progress replayed after a pause (a late server message must not fail the test)
    retried = False
    try:
        while not uv.started:
            await asyncio.sleep(0.05)
        service = service_box["s"]
        for name, (game, _) in players.items():
            bots[name] = await GameBot(f"ws://127.0.0.1:{PORT}", name, game).connect()
        pid = {multiworld.player_name[p]: p for p in multiworld.player_ids}
        async with httpx.AsyncClient(base_url=f"http://127.0.0.1:{port}", timeout=30) as client:
            for round_ in range(max_rounds):
                # wait for every slot's logic to be up to date
                for _ in range(1200):
                    data = (await client.get("/api/slots")).json()["slots"]
                    if all(s["status"] == "connected" and s["logic"]["state"] in ("ok", "error", "unavailable")
                           for s in data) and all(service.logic_settled(s["name"]) for s in data):
                        break
                    await asyncio.sleep(0.1)
                errors = {s["name"]: s["logic"] for s in data if s["logic"]["state"] != "ok"}
                assert not errors, f"logic not available: {errors}"
                progress = False
                for s in data:
                    name = s["name"]
                    bot = bots[name]
                    # A finished slot keeps checking: its world still holds items for the others.
                    if not s["goal"] and goal_reached(multiworld, pid[name], bot.items):
                        await bot.goal()
                        progress = True
                        continue
                    detail = (await client.get(f"/api/slots/{name}")).json()
                    todo = [loc["id"] for loc in detail["in_logic_locations"]]
                    if todo:
                        await bot.check(todo)
                        progress = True
                history.append({s["name"]: (s["checks"]["done"], s["logic"]["count"], s["goal"]) for s in data})
                if all(s["goal"] for s in data):
                    return {"rounds": round_, "retries": retries, "history": history}
                if not progress and not retried:
                    # Look again after a pause: an under-estimate stays stuck, a late message does not.
                    retried, retries = True, retries + 1
                    await asyncio.sleep(2)
                    continue
                retried = False
                if not progress:
                    stuck = {s["name"]: {"missing": s["checks"]["remaining"], "items": s["items"]["received"],
                                         "reference_todo": reference_todo(multiworld, pid[s["name"]],
                                                                          bots[s["name"]].items,
                                                                          bots[s["name"]].missing)[:5],
                                         "bot_items": len(bots[s["name"]].items)}
                             for s in data if not s["goal"]}
                    dump = {name: {"items": b.items, "missing": sorted(b.missing), "slot": b.slot,
                                   "slot_data": b.slot_data} for name, b in bots.items()}
                    (ROOT / "test-output" / f"e2e_stuck_{fixture}.json").write_text(json.dumps(dump))
                    raise AssertionError(f"stuck after {round_} rounds, logic under-estimates? {stuck}")
                # let the server and the trackers catch up with the checks/goals just sent
                await asyncio.sleep(0.5)
            raise AssertionError("too many rounds")
    finally:
        for bot in bots.values():
            await bot.close()
        uv.should_exit = True
        await asyncio.wait_for(task, 30)
        stop_server(PORT)


async def test_bot_finishes_multi5_using_only_in_logic_locations(tmp_path):
    result = await play_until_done("multi5", 42, tmp_path)
    out = ROOT / "test-output" / "e2e_multi5.json"
    out.write_text(json.dumps(result, indent=1))
    assert result["rounds"] > 1


async def test_bot_finishes_m7_batch_using_only_in_logic_locations(tmp_path):
    """Ori BF, KH BBS, Jak 3, Pokemon BW/Platinum, R&C 2/3, AEMinecraft, Isaac, Slay the Spire."""
    result = await play_until_done("m7a", 11, tmp_path, spoiler=1)
    (ROOT / "test-output" / "e2e_m7a.json").write_text(json.dumps(result, indent=1))
    assert result["rounds"] > 1


async def test_bot_finishes_m7b_batch_using_only_in_logic_locations(tmp_path):
    """Super Mario Odyssey (Spicy Meatball Overdrive), Mario Kart Wii, Super Mario 64."""
    result = await play_until_done("m7b", 13, tmp_path, spoiler=1)
    (ROOT / "test-output" / "e2e_m7b.json").write_text(json.dumps(result, indent=1))
    assert result["rounds"] > 1


async def test_bot_finishes_m7c_batch_using_only_in_logic_locations(tmp_path):
    """Balatro, The Legend of Zelda - Phantom Hourglass."""
    result = await play_until_done("m7c", 17, tmp_path, spoiler=1)
    (ROOT / "test-output" / "e2e_m7c.json").write_text(json.dumps(result, indent=1))
    assert result["rounds"] > 1


async def test_bot_finishes_m13_batch_using_only_in_logic_locations(tmp_path):
    """PokePark."""
    result = await play_until_done("m13", 17, tmp_path, spoiler=1)
    (ROOT / "test-output" / "e2e_m13.json").write_text(json.dumps(result, indent=1))
    assert result["rounds"] > 1


async def test_bot_finishes_m13w_batch_using_only_in_logic_locations(tmp_path):
    """Ori and the Will of the Wisps with the options of Romain's yaml (random options: 3/4, see COMPAT)."""
    result = await play_until_done("m13w", 17, tmp_path, spoiler=1)
    (ROOT / "test-output" / "e2e_m13w.json").write_text(json.dumps(result, indent=1))
    assert result["rounds"] > 1


async def test_bot_finishes_m14_batch_using_only_in_logic_locations(tmp_path):
    """Core games of the room played by others: The Witness, Risk of Rain 2, Terraria, Undertale, A Short Hike,
    Inscryption, shapez, Raft, Civilization VI, Paint (default options)."""
    result = await play_until_done("m14", 17, tmp_path, spoiler=1)
    (ROOT / "test-output" / "e2e_m14.json").write_text(json.dumps(result, indent=1))
    assert result["rounds"] > 1


M14B_NO_YAML = frozenset({"Mario Kart Double Dash", "Archipeladoku", "Lego Star Wars: The Complete Saga",
                          "Outer Wilds", "Portal 2"})


async def test_bot_finishes_m14b_batch_using_only_in_logic_locations(tmp_path):
    """Other apworlds of the room, at the room's version; the ones Universal Tracker can rebuild from slot_data
    alone get no yaml (the case of another player's slot). Subnautica and VVVVVV (areas shuffled) need their
    adapters, Overcooked! 2 too (kitchens shuffled) and Hollow Knight (random costs), Stardew Valley its
    received-items hook (progression items counted by pre-fill classification), Lethal Company its adapter
    (starting moon from the start inventory, scrap map), Satisfactory its yaml and adapter (Hub tiers as
    generated); Haste needs its yaml."""
    result = await play_until_done("m14b", 17, tmp_path, spoiler=1, no_yaml=M14B_NO_YAML)
    (ROOT / "test-output" / "e2e_m14b.json").write_text(json.dumps(result, indent=1))
    assert result["rounds"] > 1


M24A_NO_YAML = frozenset({"Slime Rancher"})


async def test_bot_finishes_m24a_batch_using_only_in_logic_locations(tmp_path):
    """First batch of the 2026-10 room (v0.2.1): The Wind Waker (core; dungeon and secret cave entrances, required
    bosses: its adapter), R.E.P.O, PEAK (loot sanity: its adapter), Slime Rancher (no yaml, slot_data only) and
    Clair Obscur Expedition 33."""
    result = await play_until_done("m24a", 17, tmp_path, spoiler=1, no_yaml=M24A_NO_YAML)
    (ROOT / "test-output" / "e2e_m24a.json").write_text(json.dumps(result, indent=1))
    assert result["rounds"] > 1


M24B_NO_YAML = frozenset({"Bloons TD6"})


async def test_bot_finishes_m24b_batch_using_only_in_logic_locations(tmp_path):
    """Second batch of the 2026-10 room (v0.2.2), apworlds imported by the user: ArchipelaCode (problems drawn at
    random: its adapter), Cookie Clicker, A Dance of Fire and Ice, Bloons TD6 (no yaml, slot_data only) and Blue
    Prince."""
    result = await play_until_done("m24b", 17, tmp_path, spoiler=1, no_yaml=M24B_NO_YAML)
    (ROOT / "test-output" / "e2e_m24b.json").write_text(json.dumps(result, indent=1))
    assert result["rounds"] > 1


async def test_bot_finishes_m24c_batch_using_only_in_logic_locations(tmp_path):
    """Third batch of the 2026-10 room (v0.2.3), each game with its adapter: Trackmania (map counts), Slime Rancher 2
    (shop checks and catalog waves), Deep Rock Galactic (locations removed with the global random), The Farmer Was
    Replaced (crop costs) and Don't Starve Together (goal boss, research locations, start inventory overflow)."""
    result = await play_until_done("m24c", 17, tmp_path, spoiler=1)
    (ROOT / "test-output" / "e2e_m24c.json").write_text(json.dumps(result, indent=1))
    assert result["rounds"] > 1


M24D_NO_YAML = frozenset({"Baldur's Gate 3", "Big Walk", "Burnout Paradise Remastered"})


async def test_bot_finishes_m24d_batch_using_only_in_logic_locations(tmp_path):
    """Fourth batch of the 2026-10 room (v0.2.4), no adapter needed: Burnout Paradise Remastered, Baldur's Gate 3 and
    Big Walk (no yaml, slot_data only), Geometry Dash and 2048."""
    result = await play_until_done("m24d", 17, tmp_path, spoiler=1, no_yaml=M24D_NO_YAML)
    (ROOT / "test-output" / "e2e_m24d.json").write_text(json.dumps(result, indent=1))
    assert result["rounds"] > 1


M24E_NO_YAML = frozenset({"Donut County"})


async def test_bot_finishes_m24e_batch_using_only_in_logic_locations(tmp_path):
    """Fifth batch of the 2026-10 room (v0.2.5), no adapter needed: ClusterTruck, Cyberpunk 2077, Dead Rising Deluxe
    Remaster, Dome Keeper and Donut County (no yaml, slot_data only)."""
    result = await play_until_done("m24e", 17, tmp_path, spoiler=1, no_yaml=M24E_NO_YAML)
    (ROOT / "test-output" / "e2e_m24e.json").write_text(json.dumps(result, indent=1))
    assert result["rounds"] > 1


async def test_bot_finishes_m24f_batch_using_only_in_logic_locations(tmp_path):
    """Sixth batch of the 2026-10 room (v0.2.6), no adapter needed: DREDGE, Enter The Gungeon, Fall Guys, Fez and
    Hades."""
    result = await play_until_done("m24f", 17, tmp_path, spoiler=1)
    (ROOT / "test-output" / "e2e_m24f.json").write_text(json.dumps(result, indent=1))
    assert result["rounds"] > 1


M24G_NO_YAML = frozenset({"Hades2Rogue", "Luigi's Mansion", "Nine Sols"})


async def test_bot_finishes_m24g_batch_using_only_in_logic_locations(tmp_path):
    """Seventh batch of the 2026-10 room (v0.2.7), no adapter needed: Hades2Rogue, Luigi's Mansion and Nine Sols (no
    yaml, slot_data only), Keep Talking and Nobody Explodes and Nodebuster."""
    result = await play_until_done("m24g", 17, tmp_path, spoiler=1, no_yaml=M24G_NO_YAML)
    (ROOT / "test-output" / "e2e_m24g.json").write_text(json.dumps(result, indent=1))
    assert result["rounds"] > 1
