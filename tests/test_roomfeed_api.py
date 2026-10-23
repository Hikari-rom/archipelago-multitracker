"""Room-wide dashboard HTTP endpoints and SSE events (fake service, stub feed)."""
from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace

import httpx

from multitracker.api import create_app

DISABLED = "tableau de bord de la room désactivé"


class StubFeed:
    def __init__(self):
        self.calls: list[tuple] = []

    def status(self):
        return {"enabled": True, "state": "listening"}

    def summary(self):
        return {"room": {"done": 1, "total": 2}, "players": []}

    def checks(self, limit=50, offset=0, player=None, slot=None, game=None):
        self.calls.append(("checks", limit, offset, player, slot, game))
        return {"total": 0, "offset": offset, "items": []}

    def activity(self, bucket="hour", player=None, now=None):
        self.calls.append(("activity", bucket, player))
        return {"bucket": bucket, "buckets": [], "undated": 0}


class FakeService:
    def __init__(self, roomfeed, events=()):
        self.roomfeed = roomfeed
        self.trackers = {}
        self.config = SimpleNamespace(password="")
        self.events = list(events)

    def room_event(self):
        return {"type": "room"}

    def subscribe(self):
        queue: asyncio.Queue = asyncio.Queue()
        for event in [*self.events, {"type": "_close"}]:
            queue.put_nowait(event)
        return queue

    def unsubscribe(self, queue):
        pass


class Client:
    """Sync wrapper over the ASGI app (the service is set directly: no lifespan needed)."""

    def __init__(self, roomfeed, events=()):
        self.app = create_app(lambda: None, frontend_dist=None, log_file=None)
        self.app.state.service = FakeService(roomfeed, events)

    def get(self, path, **kw):
        async def go():
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=self.app), base_url="http://t") as c:
                return await c.get(path, **kw)
        return asyncio.run(go())

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def client(roomfeed, events=()):
    return Client(roomfeed, events)


def test_disabled_status_is_200_and_other_endpoints_404():
    with client(None) as c:
        r = c.get("/api/roomfeed")
        assert r.status_code == 200 and r.json() == {"enabled": False}
        for path in ("summary", "checks", "activity"):
            r = c.get(f"/api/roomfeed/{path}")
            assert r.status_code == 404 and r.json()["detail"] == DISABLED


def test_enabled_endpoints_return_the_feed_data():
    with client(StubFeed()) as c:
        assert c.get("/api/roomfeed").json() == {"enabled": True, "state": "listening"}
        assert c.get("/api/roomfeed/summary").json()["room"] == {"done": 1, "total": 2}
        assert c.get("/api/roomfeed/checks").json() == {"total": 0, "offset": 0, "items": []}
        assert c.get("/api/roomfeed/activity").json()["bucket"] == "hour"


def test_checks_forwards_filters_and_clamps_paging():
    feed = StubFeed()
    with client(feed) as c:
        c.get("/api/roomfeed/checks")
        c.get("/api/roomfeed/checks", params={"limit": 20, "offset": 40, "player": "Romain", "slot": "R_KH2",
                                              "game": "Kingdom Hearts 2"})
        c.get("/api/roomfeed/checks", params={"limit": 100000, "offset": -5})
        c.get("/api/roomfeed/checks", params={"limit": 0, "player": "", "slot": "", "game": ""})
    assert feed.calls == [("checks", 50, 0, None, None, None),
                          ("checks", 20, 40, "Romain", "R_KH2", "Kingdom Hearts 2"),
                          ("checks", 500, 0, None, None, None),
                          ("checks", 1, 0, None, None, None)]


def test_activity_buckets_and_player():
    feed = StubFeed()
    with client(feed) as c:
        assert c.get("/api/roomfeed/activity", params={"bucket": "day", "player": "Romain"}).status_code == 200
        r = c.get("/api/roomfeed/activity", params={"bucket": "week"})
        assert r.status_code == 400
    assert feed.calls == [("activity", "day", "Romain")]


def test_roomfeed_sse_events_pass_through_unchanged():
    events = [{"type": "roomfeed_check", "checks": [{"key": "1:2", "sender": "A", "item": "Sword"}]},
              {"type": "roomfeed", "status": {"enabled": True, "state": "listening"}}]
    with client(StubFeed(), events) as c:
        body = c.get("/api/events").text
    blocks = {b.split("\n")[0]: b for b in body.split("\n\n") if b.startswith("event:")}
    for event in events:
        block = blocks[f"event: {event['type']}"]
        assert json.loads(block.split("data: ", 1)[1]) == event
