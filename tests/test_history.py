"""M12: item history (when each item arrived) and slot activity (last check)."""
from __future__ import annotations

import pytest

from test_backend_level1 import SLOTS, connected_service, eventually, seed_zip, server  # noqa: F401  (fixtures)


def test_history_rules(tmp_path):
    from multitracker.history import History
    from multitracker.store import Store
    store = Store(tmp_path / "db.sqlite3")
    h = History(store)
    times = lambda hist, slot="A": hist.times("S", slot)  # noqa: E731
    h.on_checks("S", "A", now=5)  # not synced yet: ignored
    assert h.last_check("S", "A") is None
    h.on_items("S", "A", 3, fresh=True, now=10)  # first sync: 3 items from before
    assert times(h) == [(None, None)] * 3
    h.on_items("S", "A", 3, now=11)
    h.on_items("S", "A", 5, now=12)
    h.on_checks("S", "A", now=13)
    h.on_checks("S", "A", new_checks=40, now=14)  # release/collect: not activity
    assert h.last_check("S", "A") == 13
    assert times(h)[3:] == [(12, None), (12, None)]
    # disconnected at 20; two items arrive meanwhile and show up at the next sync, an hour later: a range
    h.lost("S", "A", now=20)
    h.on_items("S", "A", 7, fresh=True, now=3620)
    assert times(h)[5:] == [(3620, 20), (3620, 20)]
    # quick reconnection: exact enough
    h.lost("S", "A", now=3700)
    h.on_items("S", "A", 8, fresh=True, now=3730)
    assert times(h)[7] == (3730, None)
    h.flush(now=3800)  # trackers stopping
    # persisted (new process), seen at 3800: items found at the next sync come with that lower bound
    h2 = History(store)
    assert times(h2)[3] == (12, None) and h2.last_check("S", "A") == 13
    h2.on_items("S", "A", 9, fresh=True, now=9000)
    assert times(h2)[8] == (9000, 3800)
    # an empty first sync, then items: those are new; another seed is another history
    h2.on_items("S", "B", 0, fresh=True, now=20)
    h2.on_items("S", "B", 2, now=21)
    assert times(h2, "B") == [(21, None), (21, None)]
    assert h2.times("other-seed", "A") == [] and h2.last_check("other-seed", "A") is None


def test_history_writes_are_throttled_and_migrated(tmp_path):
    import sqlite3
    from multitracker.history import WRITE_INTERVAL, History
    from multitracker.store import Store
    db = tmp_path / "db.sqlite3"
    old = sqlite3.connect(db)  # tables as created by the first M12 release
    old.executescript("CREATE TABLE tracking (seed_name TEXT NOT NULL, slot_name TEXT NOT NULL, started_at REAL "
                      "NOT NULL, last_check_at REAL, PRIMARY KEY (seed_name, slot_name));"
                      "CREATE TABLE item_times (seed_name TEXT NOT NULL, slot_name TEXT NOT NULL, idx INTEGER "
                      "NOT NULL, received_at REAL, PRIMARY KEY (seed_name, slot_name, idx));"
                      "INSERT INTO tracking VALUES ('S', 'A', 100, 150);"
                      "INSERT INTO item_times VALUES ('S', 'A', 0, NULL), ('S', 'A', 1, 120);")
    old.commit()
    old.close()
    store = Store(db)
    h = History(store)
    assert h.times("S", "A") == [(None, None), (120, None)] and h.last_check("S", "A") == 150
    h.on_items("S", "A", 3, fresh=True, now=1000)  # last seen unknown: the last check is the lower bound
    assert h.times("S", "A")[2] == (1000, 150)
    h.on_checks("S", "A", now=1001)  # written at the sync (1000): this one waits
    assert store.tracking("S", "A")["last_check_at"] == 150 and h.last_check("S", "A") == 1001
    h.on_checks("S", "A", now=1000 + WRITE_INTERVAL)
    assert store.tracking("S", "A")["last_check_at"] == 1000 + WRITE_INTERVAL
    h.on_checks("S", "A", now=1002 + WRITE_INTERVAL)
    h.lost("S", "A", now=1003 + WRITE_INTERVAL)  # written right away
    assert store.tracking("S", "A") == {"started_at": 100, "last_check_at": 1002 + WRITE_INTERVAL,
                                        "last_seen_at": 1003 + WRITE_INTERVAL}


@pytest.mark.asyncio
async def test_live_history_and_activity(server, tmp_path):
    from bot import GameBot
    service = await connected_service(tmp_path)
    try:
        await eventually(lambda: all(t.state.synced for t in service.trackers.values()), what="synced")
        before = {n: service.summary(n)["items"]["received"] for n in SLOTS}
        assert all(service.summary(n)["last_check_at"] is None for n in SLOTS)
        async with GameBot(server, "Celeste", SLOTS["Celeste"]) as bot:
            todo = sorted(bot.missing)[:15]
            for start in range(0, 15, 5):  # small batches: a burst would look like a release
                await bot.check(todo[start:start + 5])
        await eventually(lambda: service.summary("Celeste")["last_check_at"] is not None, what="activity")
        # the checked locations held items for someone: those got a reception time
        def timed():
            return [(n, i["index"]) for n in SLOTS for i in service.detail(n)["items_list"] if i["received_at"]]
        await eventually(lambda: bool(timed()), what="timed items")
        for name, index in timed():
            assert index >= before[name]  # items present at the first sync stay "before tracking"
        for name in SLOTS:
            assert all(i["received_at"] is None for i in service.detail(name)["items_list"][:before[name]])
        # dashboard feed: the timed items sent by someone else, newest first, with their slot
        recent = service.recent_items()
        sent = {(n, i["index"]) for n in SLOTS for i in service.detail(n)["items_list"]
                if i["received_at"] and i["origin"] not in ("own", "start")}
        assert {(i["slot"], i["index"]) for i in recent} == sent
        assert [i["received_at"] for i in recent] == sorted((i["received_at"] for i in recent), reverse=True)
        assert all(i["game"] == service.summary(i["slot"])["game"] for i in recent)
        assert len(service.recent_items(per_slot=1)) <= len(SLOTS)
    finally:
        await service.stop()
