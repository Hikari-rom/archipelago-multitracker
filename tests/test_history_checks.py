"""M19: history of the checks made (when, and what they held) and the restricted LocationScouts."""
from __future__ import annotations

import json

import pytest

from test_backend_level1 import PORT, eventually, seed_zip, server  # noqa: F401  (fixtures)


def test_check_times_rules(tmp_path):
    from multitracker.history import History
    from multitracker.store import Store
    store = Store(tmp_path / "db.sqlite3")
    h = History(store)
    h.on_items("S", "A", 0, fresh=True, now=10, checked={1, 2})  # first sync: checked before the app watched
    assert h.check_times("S", "A") == {1: (None, None), 2: (None, None)}
    h.on_items("S", "A", 0, now=11, checked={1, 2, 3})
    assert h.check_times("S", "A")[3] == (11, None)
    h.lost("S", "A", now=20)
    h.on_items("S", "A", 0, fresh=True, now=3620, checked={1, 2, 3, 4})  # found at the next sync: a range
    assert h.check_times("S", "A")[4] == (3620, 20)
    h.flush(now=3700)
    h2 = History(store)  # new process: read back from the database
    assert h2.check_times("S", "A") == {3: (11, None), 4: (3620, 20)}  # only timed ones before the next sync
    h2.on_items("S", "A", 0, fresh=True, now=3710, checked={1, 2, 3, 4, 5})
    assert h2.check_times("S", "A")[5] == (3710, None) and h2.check_times("S", "A")[1] == (None, None)


def test_check_times_start_on_a_slot_tracked_before(tmp_path):
    """Databases from before M19 have item times but no check times: the checks already done have no time."""
    from multitracker.history import History
    from multitracker.store import Store
    store = Store(tmp_path / "db.sqlite3")
    store.start_tracking("S", "A", 5, 2)
    h = History(store)
    h.on_items("S", "A", 2, fresh=True, now=10, checked={7, 8})
    assert h.check_times("S", "A") == {7: (None, None), 8: (None, None)}
    h.on_items("S", "A", 2, now=11, checked={7, 8, 9})
    assert h.check_times("S", "A")[9] == (11, None)


def make_service(tmp_path, scout: bool):
    from multitracker import config
    from multitracker.service import Service
    from multitracker.store import Store
    path = tmp_path / "room.yaml"  # two of the five slots: the others are players the app does not follow
    path.write_text(json.dumps({"server": f"127.0.0.1:{PORT}", "password": "test", "scout_checked": scout,
                                "slots": [{"name": "Celeste"}, {"name": "KH2"}]}))
    return Service(config.load(path), Store(tmp_path / "db.sqlite3"), publish_debounce=0.05,
                   reconnect_delays=(0.3, 1.0))


@pytest.mark.asyncio
@pytest.mark.parametrize("scout", [True, False])
async def test_sent_checks_history(server, seed_zip, tmp_path, scout):
    import logic_reference as lr
    from bot import GameBot
    md = lr.load_multidata(seed_zip)
    slot_of = {info.name: sid for sid, info in md["slot_info"].items()}
    truth = md["locations"][slot_of["Celeste"]]  # location -> (item, receiving slot, flags)
    service = make_service(tmp_path, scout)
    sent_scouts = []
    await service.start()
    try:
        tracker = service.trackers["Celeste"]
        original = tracker._send

        async def spy(*msgs):
            sent_scouts.extend(m for m in msgs if m.get("cmd") == "LocationScouts")
            await original(*msgs)
        tracker._send = spy
        await eventually(lambda: all(t.state.synced for t in service.trackers.values()), what="synced")
        async with GameBot(server, "Celeste", "Celeste (Open World)") as bot:
            done = sorted(bot.missing)[:8]
            await bot.check(done)
        await eventually(lambda: set(done) <= tracker.state.checked, what="checks seen")
        to_tracked = {loc for loc in done if md["slot_info"][truth[loc][1]].name in ("Celeste", "KH2")}
        expected = set(done) if scout else to_tracked
        await eventually(lambda: set(service.check_contents("Celeste")) >= expected, what="contents")
        contents = service.check_contents("Celeste")
        for loc in expected:
            assert contents[loc] == tuple(truth[loc]), loc
        assert set(contents) == expected
        page = service.history_page("sent", "Celeste", 100, 0)
        assert page["total"] == len(done) and page["scout_checked"] is scout
        assert all(r["checked_at"] is not None for r in page["items"])
        rows = {r["location_id"]: r for r in page["items"]}
        for loc in done:
            receiver = md["slot_info"][truth[loc][1]].name
            assert rows[loc]["receiver"] == (receiver if loc in expected else None)
            assert rows[loc]["to_self"] == ((receiver == "Celeste") if loc in expected else None)
        summary = service.summary("Celeste")["sent"]
        assert summary["known"] == len(expected)
        assert summary["to_others"] == sum(1 for loc in expected if truth[loc][1] != slot_of["Celeste"])
        if scout:
            assert sent_scouts and all(m["create_as_hint"] == 0 and set(m["locations"]) <= set(done)
                                       for m in sent_scouts)
        else:
            assert not sent_scouts
        received = service.history_page("received", None, 1000, 0)
        assert received["total"] == sum(len(t.state.items) for t in service.trackers.values())
        assert {s["name"] for s in received["slots"]} == {"Celeste", "KH2"}
    finally:
        await service.stop()
    if scout:  # contents are kept: a new process does not ask again
        service = make_service(tmp_path, scout)
        await service.start()
        try:
            await eventually(lambda: service.trackers["Celeste"].state.synced, what="synced again")
            assert set(service.check_contents("Celeste")) == set(done)
            assert not (set(done) - service.trackers["Celeste"].state.contents.keys())
        finally:
            await service.stop()
