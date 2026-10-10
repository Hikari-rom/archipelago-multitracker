"""HTTP API (REST + Server-Sent Events) and, in production, the built frontend."""
from __future__ import annotations

import asyncio
import json
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, AsyncIterator, Callable

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .apenv import ROOT
from .config import PLAYERS_DIR, ConfigError, RoomConfig, SlotConfig, safe_yaml_path
from .config import save as save_config
from .service import Service

log = logging.getLogger(__name__)
FRONTEND_DIST = ROOT / "frontend" / "dist"
SSE_KEEPALIVE = 20.0


class SeenBody(BaseModel):
    count: int | None = None  # mark items [0, count) as seen; default: everything received so far


class DiscoverBody(BaseModel):
    url: str


class SlotBody(BaseModel):
    name: str
    game: str | None = None
    yaml: str | None = None
    owner: str | None = None


class ConfigBody(BaseModel):
    room_url: str | None = None
    server: str | None = None
    password: str | None = None  # None = keep the current password
    slots: list[SlotBody]


def _rel(path: Path | None) -> str | None:
    if path is None:
        return None
    try:
        return str(Path(path).resolve().relative_to(ROOT))
    except ValueError:
        return str(path)


def create_app(service_factory: Callable[[], Service], frontend_dist: Path | None = FRONTEND_DIST) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        service = service_factory()
        app.state.service = service
        await service.start()
        try:
            yield
        finally:
            await service.stop()

    app = FastAPI(title="Archipelago Multitracker", lifespan=lifespan)

    def get_service(request: Request) -> Service:
        return request.app.state.service

    def require_slot(service: Service, name: str) -> None:
        if name not in service.trackers:
            raise HTTPException(404, f"slot inconnu : {name}")

    @app.get("/api/health")
    async def health(request: Request) -> dict[str, Any]:
        service = get_service(request)
        return {"ok": True, "slots": len(service.trackers),
                "connected": sum(t.state.status == "connected" for t in service.trackers.values())}

    @app.get("/api/slots")
    async def slots(request: Request) -> dict[str, Any]:
        service = get_service(request)
        return {"server": service.current_server, "room_url": service.config.room_url,
                "room_error": service.room_error, "slots": [service.summary(n) for n in service.trackers]}

    @app.get("/api/config")
    async def get_config(request: Request) -> dict[str, Any]:
        cfg = get_service(request).config
        return {"room_url": cfg.room_url, "server": cfg.server, "has_password": bool(cfg.password),
                "slots": [{"name": s.name, "game": s.game, "owner": s.owner,
                           "yaml": _rel(s.yaml)} for s in cfg.slots],
                "player_yamls": sorted(_rel(p) for p in PLAYERS_DIR.glob("*.y*ml"))}

    @app.post("/api/discover")
    async def discover(body: DiscoverBody) -> dict[str, Any]:
        from .room import RoomError, fetch_room
        try:
            info = await asyncio.to_thread(fetch_room, body.url, 15.0, True)
        except RoomError as exc:
            raise HTTPException(400, str(exc)) from exc
        return {"room_url": info.url, "server": info.server,
                "players": [{"name": n, "game": g} for n, g in info.players]}

    @app.put("/api/config")
    async def put_config(body: ConfigBody, request: Request) -> dict[str, Any]:
        service = get_service(request)
        current = service.config
        try:
            if not (body.room_url or body.server):
                raise ConfigError("indique l'URL de la room ou l'adresse du serveur")
            if body.room_url:
                from .room import RoomError, parse_room_url
                try:
                    parse_room_url(body.room_url)
                except RoomError as exc:
                    raise ConfigError(str(exc)) from exc
            names = [s.name.strip() for s in body.slots]
            if any(not n for n in names) or len(set(names)) != len(names):
                raise ConfigError("noms de slots vides ou en double")
            slots = [SlotConfig(name=s.name.strip(), game=s.game or None, yaml=safe_yaml_path(s.yaml),
                                owner=(s.owner or "").strip() or None) for s in body.slots]
        except ConfigError as exc:
            raise HTTPException(400, str(exc)) from exc
        new = RoomConfig(server=(body.server or "").strip(), slots=slots, path=current.path,
                         password=current.password if body.password is None else body.password,
                         room_url=(body.room_url or "").strip() or None)
        save_config(new)
        await service.reload(new)
        return {"ok": True, "slots": len(slots)}

    @app.get("/api/slots/{name:path}")
    async def slot_detail(name: str, request: Request) -> dict[str, Any]:
        service = get_service(request)
        require_slot(service, name)
        return service.detail(name)

    @app.post("/api/slots/{name:path}/seen")
    async def mark_seen(name: str, request: Request, body: SeenBody | None = None) -> dict[str, Any]:
        service = get_service(request)
        require_slot(service, name)
        try:
            count = service.mark_seen(name, body.count if body else None)
        except ValueError as exc:
            raise HTTPException(409, str(exc)) from exc
        return {"seen": count}

    @app.get("/api/events")
    async def events(request: Request) -> StreamingResponse:
        service = get_service(request)
        queue = service.subscribe()

        async def stream() -> AsyncIterator[str]:
            try:
                yield "retry: 3000\n\n"
                snapshot = {"type": "snapshot", "slots": [service.summary(n) for n in service.trackers]}
                yield f"event: snapshot\ndata: {json.dumps(snapshot)}\n\n"
                while True:
                    if await request.is_disconnected():
                        break
                    try:
                        event = await asyncio.wait_for(queue.get(), SSE_KEEPALIVE)
                    except asyncio.TimeoutError:
                        yield ": keepalive\n\n"
                        continue
                    if event["type"] == "_close":
                        break
                    yield f"event: {event['type']}\ndata: {json.dumps(event)}\n\n"
            finally:
                service.unsubscribe(queue)

        return StreamingResponse(stream(), media_type="text/event-stream",
                                 headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

    if frontend_dist is not None and (frontend_dist / "index.html").exists():
        if (frontend_dist / "assets").is_dir():
            app.mount("/assets", StaticFiles(directory=frontend_dist / "assets"), name="assets")

        @app.get("/{path:path}", include_in_schema=False)
        async def spa(path: str) -> FileResponse:
            if path.startswith("api/"):
                raise HTTPException(404)
            try:
                candidate = (frontend_dist / path).resolve()
                if path and candidate.is_file() and frontend_dist.resolve() in candidate.parents:
                    return FileResponse(candidate)
            except (ValueError, OSError):
                pass
            return FileResponse(frontend_dist / "index.html")

    return app
