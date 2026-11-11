"""Victory chosen by hand in the Configuration (D34): config, options of each game, goals and logic."""
from __future__ import annotations

from collections import Counter

import httpx
import pytest

from testenv_helpers import FIXTURES

KH2_OPTIONS = [{"option": "Goal", "display": "Goal", "choices": ["three_proofs", "lucky_emblem_hunt", "hitlist"]}]


class FakeGoalEngine:
    """Logic engine that only knows the victory conditions (no worker)."""

    async def start(self):
        pass

    async def stop(self):
        pass

    async def compute(self, request):
        from multitracker.logic import LogicResult
        return LogicResult("unavailable", message="test")

    async def forget(self, slot_name):
        pass

    async def checksums(self, games):
        return None

    async def goal_options(self, games):
        return {g: (KH2_OPTIONS if g == "Kingdom Hearts 2" else []) for g in games}


def test_goal_override_is_off_by_default_and_round_trips(tmp_path):
    from multitracker import config as config_mod
    from multitracker.config import RoomConfig, SlotConfig
    path = tmp_path / "room.yaml"
    path.write_text("server: 127.0.0.1:1\nslots: [{name: A}]\n")
    cfg = config_mod.load(path)
    assert cfg.goal_override is False and cfg.slots[0].goal is None
    config_mod.save(RoomConfig(server="127.0.0.1:1", path=path, goal_override=True,
                               slots=[SlotConfig("A", "Kingdom Hearts 2", goal={"Goal": "hitlist"})]))
    cfg = config_mod.load(path)
    assert cfg.goal_override is True and cfg.slots[0].goal == {"Goal": "hitlist"}


def test_goal_options_of_the_worlds():
    from multitracker import apenv
    from multitracker.logic.ut_worker import goal_options_of
    apenv.setup()
    from worlds.AutoWorld import AutoWorldRegister
    kh2 = goal_options_of(AutoWorldRegister.world_types["Kingdom Hearts 2"])
    assert [o["option"] for o in kh2] == ["Goal"] and "three_proofs" in kh2[0]["choices"]
    assert goal_options_of(AutoWorldRegister.world_types["Fall Guys"]) == []  # tickets: a Range, nothing to choose
    lego = goal_options_of(AutoWorldRegister.world_types["Lego Star Wars: The Complete Saga"])
    assert "minikit_goal_completion_method" not in {o["option"] for o in lego}


def test_every_describer_takes_every_victory_it_offers():
    """A goal chosen by hand reaches the describer through GoalContext.opt and never breaks it."""
    from multitracker import apenv
    from multitracker.goals import DESCRIBERS, GoalContext, describe
    from multitracker.logic.ut_worker import goal_options_of
    apenv.setup()
    from worlds.AutoWorld import AutoWorldRegister
    tried = 0
    for game in DESCRIBERS:
        world = AutoWorldRegister.world_types.get(game)
        if world is None:
            continue
        for option in goal_options_of(world):
            for value in option["choices"]:
                ctx = GoalContext(game=game, slot_data={}, yaml={}, received=Counter(), checked=set(),
                                  locations=set(), goal=False, overrides={option["option"]: value})
                goal = describe(ctx)
                assert goal and goal["summary"], (game, option["option"], value)
                tried += 1
    assert tried > 30


def test_chosen_goal_wins_over_slot_data_and_generic_goal():
    from multitracker.goals import GoalContext, describe
    ctx = GoalContext(game="Kingdom Hearts 2", slot_data={"Goal": 0, "FinalXemnas": 0}, yaml={},
                      received=Counter(), checked=set(), locations=set(), goal=False,
                      overrides={"Goal": "lucky_emblem_hunt"})
    goal = describe(ctx)
    assert goal["summary"].startswith("0 Lucky Emblems") or "Lucky Emblems" in goal["summary"]
    assert "manuel" in goal["source"]
    ctx = GoalContext(game="Some Game", slot_data={}, yaml={}, received=Counter(), checked=set(), locations=set(),
                      goal=False, overrides={"goal": "dark_world"}, override_names={"goal": "Goal"})
    goal = describe(ctx)
    assert goal["summary"] == "Goal : dark_world" and goal["source"] == "manuel"
    assert goal["steps"] == [{"label": "Objectif atteint", "done": False}]
    ctx.overrides = {}
    assert describe(ctx) is None


def test_chosen_goal_goes_into_the_prepared_yaml_and_the_world_key(tmp_path):
    import yaml
    from multitracker import apenv
    from multitracker.logic.ut_worker import prepare_player_yaml, request_key
    apenv.setup()
    from worlds.AutoWorld import AutoWorldRegister
    options = dict(AutoWorldRegister.world_types["Kingdom Hearts 2"].options_dataclass.type_hints)
    out, _ = prepare_player_yaml(FIXTURES / "multi5" / "kh2.yaml", "KH2", "Kingdom Hearts 2", tmp_path, {}, options,
                                 {"Goal": "hitlist", "Nope": "x"})
    section = yaml.safe_load(out.read_text())["Kingdom Hearts 2"]
    assert section["Goal"] == "hitlist" and "Nope" not in section
    req = {"slot_name": "KH2", "game": "Kingdom Hearts 2", "team": 0, "slot": 1, "slot_data": {}, "yaml": None}
    assert request_key(req) != request_key({**req, "goal": {"Goal": "hitlist"}})
    assert request_key(req) == request_key({**req, "goal": {}})


def make_app(cfg, tmp_path):
    from multitracker.api import create_app
    from multitracker.service import Service
    from multitracker.store import Store

    def factory():
        return Service(cfg, Store(tmp_path / "db.sqlite3"), logic=FakeGoalEngine(), reconnect_delays=(0.3, 1.0))
    return create_app(factory, frontend_dist=None)


async def test_goal_through_the_config_api(tmp_path):
    from multitracker import config as config_mod
    from multitracker.config import RoomConfig, SlotConfig
    path = tmp_path / "room.yaml"
    cfg = RoomConfig(server="127.0.0.1:1", path=path, slots=[SlotConfig("A", "Kingdom Hearts 2")])
    config_mod.save(cfg)
    app = make_app(cfg, tmp_path)
    slot = {"name": "A", "game": "Kingdom Hearts 2"}
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as client:
            got = (await client.get("/api/goal-options", params={"game": ["Kingdom Hearts 2"]})).json()
            assert got["games"] == {"Kingdom Hearts 2": KH2_OPTIONS}
            got = (await client.get("/api/config")).json()
            assert got["goal_override"] is False and got["slots"][0]["goal"] == {}
            assert got["games"]["Kingdom Hearts 2"]["goal_options"] == KH2_OPTIONS
            assert got["goal_options_pending"] == []
            r = await client.put("/api/config", json={"server": "127.0.0.1:1", "goal_override": True,
                                                      "slots": [{**slot, "goal": {"Goal": "nope"}}]})
            assert r.status_code == 400 and "condition de victoire" in r.json()["detail"]
            r = await client.put("/api/config", json={"server": "127.0.0.1:1", "goal_override": True,
                                                      "slots": [{**slot, "goal": {"Goal": "hitlist"}}]})
            assert r.status_code == 200, r.text
            assert config_mod.load(path).slots[0].goal == {"Goal": "hitlist"}
            r = await client.put("/api/config", json={"server": "127.0.0.1:1", "slots": [slot]})  # goal omitted
            assert r.status_code == 200 and config_mod.load(path).slots[0].goal == {"Goal": "hitlist"}
            got = (await client.get("/api/config")).json()
            assert got["goal_override"] is True and got["slots"][0]["goal"] == {"Goal": "hitlist"}
            summary = (await client.get("/api/slots")).json()["slots"][0]
            assert summary["goal_choosable"] is True
            r = await client.put("/api/config", json={"server": "127.0.0.1:1", "slots": [{**slot, "goal": {}}]})
            assert r.status_code == 200 and config_mod.load(path).slots[0].goal is None


async def test_goal_choice_only_when_the_option_is_on(tmp_path):
    from multitracker.config import RoomConfig, SlotConfig
    from multitracker.service import Service
    from multitracker.store import Store
    cfg = RoomConfig(server="127.0.0.1:1", slots=[SlotConfig("A", "Kingdom Hearts 2", goal={"Goal": "hitlist"})])
    service = Service(cfg, Store(tmp_path / "db.sqlite3"), logic=FakeGoalEngine(), reconnect_delays=(0.3, 1.0))
    await service.start()
    try:
        await service.goal_options_for(["Kingdom Hearts 2"])
        assert service.goal_choice("A") == {}  # option off: kept in the file, no effect
        cfg.goal_override = True
        assert service.goal_choice("A") == {"Goal": "hitlist"}
        cfg.slots[0].goal = {"Goal": "gone_in_a_new_apworld"}
        assert service.goal_choice("A") == {}
    finally:
        await service.stop()


class SlowGoalEngine(FakeGoalEngine):
    """The logic worker busy with the slots' logic: the victory conditions come late."""

    def __init__(self):
        import asyncio
        self.release = asyncio.Event()
        self.asked = []

    async def goal_options(self, games):
        self.asked.append(list(games))
        await self.release.wait()
        return await super().goal_options(games)


async def test_config_page_does_not_wait_for_the_logic_worker(tmp_path):
    """GET /api/config answers at once with the conditions it knows and names the tracked games still pending; only
    the tracked games are asked to the worker, and the answer is kept on disk for the next start."""
    import asyncio
    from multitracker.api import create_app
    from multitracker.config import RoomConfig, SlotConfig
    from multitracker.service import Service
    from multitracker.store import Store
    cache = tmp_path / "goal_options.json"
    cfg = RoomConfig(server="127.0.0.1:1", path=tmp_path / "room.yaml", slots=[SlotConfig("A", "Kingdom Hearts 2")])
    engine = SlowGoalEngine()
    app = create_app(lambda: Service(cfg, Store(tmp_path / "db.sqlite3"), logic=engine, reconnect_delays=(0.3, 1.0),
                                     goal_cache=cache), frontend_dist=None)
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as client:
            got = await asyncio.wait_for(client.get("/api/config"), 5)
            assert "goal_options" not in got.json()["games"].get("Kingdom Hearts 2", {})
            assert got.json()["goal_options_pending"] == ["Kingdom Hearts 2"]
            engine.release.set()
            got = (await client.get("/api/goal-options", params={"game": ["Kingdom Hearts 2"]})).json()
            assert got["games"] == {"Kingdom Hearts 2": KH2_OPTIONS}
    assert engine.asked == [["Kingdom Hearts 2"]]  # not the 100 games of the catalog
    assert cache.exists()

    engine = SlowGoalEngine()  # next start: known from the disk cache, the worker is not asked
    app = create_app(lambda: Service(cfg, Store(tmp_path / "db.sqlite3"), logic=engine, reconnect_delays=(0.3, 1.0),
                                     goal_cache=cache), frontend_dist=None)
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as client:
            got = (await asyncio.wait_for(client.get("/api/config"), 5)).json()
            assert got["games"]["Kingdom Hearts 2"]["goal_options"] == KH2_OPTIONS
            assert got["goal_options_pending"] == []
        await asyncio.sleep(0.05)
    assert engine.asked == []


def test_goal_cache_is_dropped_when_the_apworlds_change(tmp_path):
    from multitracker import goal_cache
    ap, user = tmp_path / "ap", tmp_path / "user"
    (ap / "custom_worlds").mkdir(parents=True)
    (ap / "Utils.py").write_text("__version__ = '0.6.7'")
    catalog = tmp_path / "apworlds.yaml"
    catalog.write_text("apworlds: {}")
    key = lambda: goal_cache.fingerprint(ap, catalog, user)  # noqa: E731
    goal_cache.save({"Kingdom Hearts 2": KH2_OPTIONS}, tmp_path / "c.json", key())
    assert goal_cache.load(tmp_path / "c.json", key()) == {"Kingdom Hearts 2": KH2_OPTIONS}
    user.mkdir()
    (user / "kh2.apworld").write_bytes(b"new")
    assert goal_cache.load(tmp_path / "c.json", key()) == {}


async def test_goal_chosen_from_the_slot(tmp_path):
    """Tab « But » / page Objectifs: the selectors appear (summary) and save (PUT /api/slots/<slot>/goal) only
    while « Choisir le but à la main » is on in the Configuration; the choice lands in config/room.yaml."""
    from multitracker import config as config_mod
    from multitracker.config import RoomConfig, SlotConfig
    path = tmp_path / "room.yaml"
    cfg = RoomConfig(server="127.0.0.1:1", path=path, slots=[SlotConfig("A", "Kingdom Hearts 2"), SlotConfig("B")])
    config_mod.save(cfg)
    app = make_app(cfg, tmp_path)
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as client:
            await client.get("/api/goal-options", params={"game": ["Kingdom Hearts 2"]})
            summary = (await client.get("/api/slots")).json()["slots"][0]
            assert "goal_options" not in summary  # option off: no selector
            r = await client.put("/api/slots/A/goal", json={"goal": {"Goal": "hitlist"}})
            assert r.status_code == 409
            r = await client.put("/api/config", json={"server": "127.0.0.1:1", "goal_override": True,
                                                      "slots": [{"name": "A", "game": "Kingdom Hearts 2"},
                                                                {"name": "B"}]})
            assert r.status_code == 200, r.text
            summary = (await client.get("/api/slots")).json()["slots"][0]
            assert summary["goal_options"] == KH2_OPTIONS and summary["goal_chosen"] == {}
            r = await client.put("/api/slots/A/goal", json={"goal": {"Goal": "nope"}})
            assert r.status_code == 400 and "condition de victoire" in r.json()["detail"]
            r = await client.put("/api/slots/A/goal", json={"goal": {"Goal": "hitlist"}})
            assert r.status_code == 200, r.text
            saved = config_mod.load(path)
            assert saved.goal_override is True and saved.slots[0].goal == {"Goal": "hitlist"}
            assert [s.name for s in saved.slots] == ["A", "B"]
            assert (await client.get("/api/slots")).json()["slots"][0]["goal_chosen"] == {"Goal": "hitlist"}
            r = await client.put("/api/slots/A/goal", json={"goal": {"Goal": ""}})  # back to automatic
            assert r.status_code == 200 and config_mod.load(path).slots[0].goal is None
            assert (await client.put("/api/slots/Z/goal", json={"goal": {}})).status_code == 404
