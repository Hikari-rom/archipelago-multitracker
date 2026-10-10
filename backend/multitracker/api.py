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
from .service import Service

log = logging.getLogger(__name__)
FRONTEND_DIST = ROOT / "frontend" / "dist"
SSE_KEEPALIVE = 20.0


class SeenBody(BaseModel):
    count: int | None = None  # mark items [0, count) as seen; default: everything received so far


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
        return {"server": service.config.server, "slots": [service.summary(n) for n in service.trackers]}

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
