"""M12: item history (when each item arrived) and slot activity (last check)."""
from __future__ import annotations

import pytest

from test_backend_level1 import SLOTS, connected_service, eventually, seed_zip, server  # noqa: F401  (fixtures)




def test_history_rules(tmp_path):
    from multitracker.history import History
    from multitracker.store import Store
    store = Store(tmp_path / "db.sqlite3")
    h = History(store)
    h.on_checks("S", "A", now=5)  # not synced yet: ignored
    assert h.last_check("S", "A") is None
    h.on_items("S", "A", 3, now=10)  # first sync: 3 items from before
    assert [h.item_time("S", "A", i) for i in range(3)] == [None, None, None]
    h.on_items("S", "A", 3, now=11)
    h.on_items("S", "A", 5, now=12)
    h.on_checks("S", "A", now=13)
    assert [h.item_time("S", "A", i) for i in range(5)] == [None, None, None, 12, 12]
    # persisted, and an empty first sync then items: those are new
    h2 = History(store)
    assert h2.item_time("S", "A", 4) == 12 and h2.last_check("S", "A") == 13
    h2.on_items("S", "B", 0, now=20)
    h2.on_items("S", "B", 2, now=21)
    assert [h2.item_time("S", "B", i) for i in range(2)] == [21, 21]
    assert h2.item_time("other-seed", "A", 0) is None


@pytest.mark.asyncio
async def test_live_history_and_activity(server, tmp_path):
    from bot import GameBot
    service = await connected_service(tmp_path)
    try:
        await eventually(lambda: all(t.state.synced for t in service.trackers.values()), what="synced")
        before = {n: service.summary(n)["items"]["received"] for n in SLOTS}
        assert all(service.summary(n)["last_check_at"] is None for n in SLOTS)
        async with GameBot(server, "Celeste", SLOTS["Celeste"]) as bot:
            await bot.check(sorted(bot.missing)[:15])
        await eventually(lambda: service.summary("Celeste")["last_check_at"] is not None, what="activity")
        # the checked locations held items for someone: those got a reception time
        def timed():
            return [(n, i["index"]) for n in SLOTS for i in service.detail(n)["items_list"] if i["received_at"]]
        await eventually(lambda: bool(timed()), what="timed items")
        for name, index in timed():
            assert index >= before[name]  # items present at the first sync stay "before tracking"
        for name in SLOTS:
            assert all(i["received_at"] is None for i in service.detail(name)["items_list"][:before[name]])
    finally:
        await service.stop()
