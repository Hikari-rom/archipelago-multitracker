"""HTTP API (REST + Server-Sent Events) and, in production, the built frontend."""
from __future__ import annotations

import asyncio
import json
import os
import time
from urllib.parse import urlparse
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, AsyncIterator, Callable

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .apenv import ROOT
from . import players as player_yamls
from . import user_apworlds
from .config import ConfigError, RoomConfig, SlotConfig, backup_path, restore_backup, safe_yaml_path
from .config import save as save_config
from .logtail import Follower, last_lines, mask
from .service import Service
from .updater import Updater, UpdateError

log = logging.getLogger(__name__)
FRONTEND_DIST = ROOT / "frontend" / "dist"
LOG_FILE = ROOT / "data" / "logs" / "app.log"  # written by scripts/app.sh
SSE_KEEPALIVE = 20.0
LOG_POLL = 0.5
LOG_STREAM_MAX = 1800.0  # a log stream ends after 30 min (EventSource reconnects): no stream outlives a stop


class SeenBody(BaseModel):
    count: int | None = None  # mark items [0, count) as seen; default: everything received so far


class DiscoverBody(BaseModel):
    url: str
    wake: bool = False  # load the room page first (starts a sleeping room)


class ProbeBody(BaseModel):
    room_url: str | None = None
    server: str | None = None
    password: str | None = None  # None = the saved password
    slot: str


class YamlUploadBody(BaseModel):
    filename: str
    content: str
    overwrite: bool = False


class SlotBody(BaseModel):
    name: str
    game: str | None = None
    yaml: str | None = None
    owner: str | None = None


class ApworldsImportBody(BaseModel):
    path: str


class ConfigBody(BaseModel):
    room_url: str | None = None
    server: str | None = None
    password: str | None = None  # None = keep the current password
    wake_room: bool | None = None  # None = keep the current setting
    scout_checked: bool | None = None  # None = keep the current setting
    room_dashboard: bool | None = None  # None = keep the current setting
    hints_foreign_logic: bool | None = None  # None = keep the current setting
    slots: list[SlotBody]


def _rel(path: Path | None) -> str | None:
    if path is None:
        return None
    try:
        return Path(path).resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return Path(path).name  # never expose the filesystem layout


def create_app(service_factory: Callable[[], Service], frontend_dist: Path | None = FRONTEND_DIST,
               log_file: Path | None = LOG_FILE, updater: Updater | None = None) -> FastAPI:
    """updater: None = no update checks (tests); __main__ gives one."""
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        service = service_factory()
        app.state.service = service
        await service.start()
        checks = asyncio.create_task(updater.loop()) if updater else None
        try:
            yield
        finally:
            if checks:
                checks.cancel()
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

    def require_json(request: Request) -> None:
        # POST without a JSON body is a "simple" request another site could send from the browser (no preflight)
        if not request.headers.get("content-type", "").startswith("application/json"):
            raise HTTPException(415, "Content-Type: application/json attendu")

    def update_info() -> dict[str, Any]:
        return updater.info() if updater else {"mode": "none", "current": {"version": None}, "latest": None,
                                               "available": False, "blocked": None, "checked_at": None,
                                               "check_error": None, "running": False, "status": None}

    @app.get("/api/update")
    async def get_update() -> dict[str, Any]:
        return await asyncio.to_thread(update_info)

    @app.post("/api/update/check")
    async def check_update(request: Request) -> dict[str, Any]:
        require_json(request)
        if updater is None:
            raise HTTPException(409, "mises à jour désactivées")
        return await updater.check()

    @app.post("/api/update/apply")
    async def apply_update(request: Request) -> dict[str, Any]:
        require_json(request)
        if updater is None:
            raise HTTPException(409, "mises à jour désactivées")
        try:
            await updater.apply()
        except UpdateError as exc:
            raise HTTPException(409, str(exc)) from exc
        return await asyncio.to_thread(update_info)

    # -- apworlds imported from the user's own Archipelago install (D27) ----------------------
    def apworlds_info(service: Service) -> dict[str, Any]:
        room = service.room_checksums()
        files = user_apworlds.imported()
        for f in files:
            f["in_room"] = (f["game"] in room) if room else None
        source = user_apworlds.default_source()
        return {"dir": _rel(user_apworlds.USER_DIR), "default_source": str(source) if source else None,
                "files": files}

    @app.get("/api/apworlds")
    async def get_apworlds(request: Request) -> dict[str, Any]:
        return await asyncio.to_thread(apworlds_info, get_service(request))

    @app.post("/api/apworlds/import")
    async def import_apworlds(body: ApworldsImportBody, request: Request) -> dict[str, Any]:
        require_json(request)
        same_origin(request)  # the imported apworlds run in the logic worker: only from the app's own page
        service = get_service(request)
        source = Path(body.path.strip()).expanduser()
        if not body.path.strip() or not source.is_absolute():
            raise HTTPException(400, "indique le chemin complet du dossier custom_worlds")
        try:
            rows = await asyncio.to_thread(user_apworlds.import_dir, source)
        except FileNotFoundError as exc:
            raise HTTPException(400, str(exc)) from exc
        except OSError as exc:
            raise HTTPException(500, f"import impossible : {exc}") from exc
        await service.restart_logic()  # the worker loads the worlds once: restart it on the new set
        return {**await asyncio.to_thread(apworlds_info, service), "report": rows}

    @app.post("/api/apworlds/check")
    async def check_apworlds(request: Request) -> dict[str, Any]:
        """Version of each imported apworld against the room: room | other | not_loaded | not_in_room | unknown."""
        require_json(request)
        service = get_service(request)
        info = await asyncio.to_thread(apworlds_info, service)
        room = service.room_checksums()
        games = sorted({f["game"] for f in info["files"] if f["game"]})
        local = await service.logic_engine.checksums(games) if games else {}
        for f in info["files"]:
            if not room or local is None or not f["game"]:
                f["version"] = "unknown"
            elif f["game"] not in room:
                f["version"] = "not_in_room"
            elif not local.get(f["game"]):
                f["version"] = "not_loaded"
            else:
                f["version"] = "room" if local[f["game"]] == room[f["game"]] else "other"
        return info

    @app.get("/api/slots")
    async def slots(request: Request) -> dict[str, Any]:
        service = get_service(request)
        return {"server": service.current_server, "room_url": service.config.room_url,
                "room_error": service.room_error, "room_sleeping": service.room_sleeping,
                "wake_room": service.config.wake_room, "room_dashboard": service.config.room_dashboard,
                "now": time.time(),  # the browser corrects its clock with this (activity, item times)
                "slots": [service.summary(n) for n in service.trackers]}

    def games_info() -> dict[str, dict[str, bool]]:
        """The catalog, plus whether each game's apworld was imported by the user (D27)."""
        from .logic.engine import game_catalog
        games = game_catalog()
        imported = {f["game"] for f in user_apworlds.imported() if f["game"]}
        for game, info in games.items():
            info["imported"] = game in imported
        return games

    @app.get("/api/config")
    async def get_config(request: Request) -> dict[str, Any]:
        cfg = get_service(request).config
        yamls = await asyncio.to_thread(player_yamls.list_yamls)
        return {"room_url": cfg.room_url, "server": cfg.server, "has_password": bool(cfg.password),
                "wake_room": cfg.wake_room, "scout_checked": cfg.scout_checked,
                "room_dashboard": cfg.room_dashboard, "hints_foreign_logic": cfg.hints_foreign_logic,
                "has_backup": backup_path(cfg.path).exists(),
                "slots": [{"name": s.name, "game": s.game, "owner": s.owner,
                           "yaml": _rel(s.yaml)} for s in cfg.slots],
                "player_yamls": [y["path"] for y in yamls], "yamls": yamls, "games": await asyncio.to_thread(games_info)}

    @app.post("/api/discover")
    async def discover(body: DiscoverBody, request: Request) -> dict[str, Any]:
        same_origin(request)
        from .room import RoomError, fetch_room
        try:
            info = await asyncio.to_thread(fetch_room, body.url, 15.0, body.wake)
        except RoomError as exc:
            raise HTTPException(400, str(exc)) from exc
        return {"room_url": info.url, "server": info.server, "sleeping": info.sleeping,
                "players": [{"name": n, "game": g} for n, g in info.players]}

    @app.post("/api/room/wake")
    async def wake_room(request: Request) -> dict[str, Any]:
        same_origin(request)
        service = get_service(request)
        try:
            woke = await service.wake_room_now()
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc
        if not woke:
            return {"ok": False, "server": service.current_server,
                    "room_error": "réveil déjà demandé il y a moins de 30 s : patiente un peu"}
        return {"ok": service.room_error is None, "server": service.current_server, "room_error": service.room_error}

    @app.post("/api/config/test")
    async def test_connection(body: ProbeBody, request: Request) -> dict[str, Any]:
        """Connect once as a read-only tracker to check the address, the password and one slot name."""
        same_origin(request)
        from .ap.tracker import probe
        from .room import RoomError, fetch_room
        service = get_service(request)
        address = (body.server or "").strip()
        if body.room_url:
            try:
                info = await asyncio.to_thread(fetch_room, body.room_url, 15.0, False)
            except RoomError as exc:
                return {"ok": False, "errors": [str(exc)]}
            if info.sleeping or not info.server:
                return {"ok": False, "sleeping": True,
                        "errors": ["room endormie : réveille-la (ouvre son lien) puis réessaie"]}
            address = info.server
        if not address:
            raise HTTPException(400, "indique l'URL de la room ou l'adresse du serveur")
        if body.password is None:
            # The saved password only goes to the room/server it was saved for.
            cfg = service.config
            same_target = (bool(body.room_url) and body.room_url.rstrip("/") == (cfg.room_url or "").rstrip("/")) or \
                (not body.room_url and address in {cfg.server, service.current_server})
            if not same_target:
                return {"ok": False, "errors": ["indique le mot de passe de cette room"], "server": address}
        password = service.config.password if body.password is None else body.password
        result = await probe(address, password, body.slot)
        result["server"] = address
        return result

    @app.post("/api/yamls")
    async def upload_yaml(body: YamlUploadBody, request: Request) -> dict[str, Any]:
        same_origin(request)
        try:
            return await asyncio.to_thread(player_yamls.save_upload, body.filename, body.content, body.overwrite)
        except FileExistsError as exc:
            raise HTTPException(409, f"{exc} existe déjà avec un autre contenu") from exc
        except ConfigError as exc:
            raise HTTPException(400, str(exc)) from exc

    @app.post("/api/config/restore")
    async def restore_config(request: Request) -> dict[str, Any]:
        same_origin(request)
        service = get_service(request)
        from .config import load as load_config
        path = service.config.path
        if not backup_path(path).exists():
            raise HTTPException(400, "aucune configuration précédente")
        try:
            restored = load_config(backup_path(path))
            for slot in restored.slots:  # same rule as PUT /api/config
                slot.yaml = safe_yaml_path(str(slot.yaml)) if slot.yaml else None
        except ConfigError as exc:
            raise HTTPException(400, str(exc)) from exc
        restored.path = path
        await service.reload(restored, before_start=lambda: restore_backup(path))
        return {"ok": True, "slots": len(restored.slots)}

    def same_origin(request: Request) -> None:
        """Refuse cross-site writes (a page on another site making the browser call this API)."""
        origin = request.headers.get("origin")
        if not origin or urlparse(origin).netloc == request.headers.get("host"):
            return
        extra = {o.strip().rstrip("/") for o in os.environ.get("MT_ALLOWED_ORIGINS", "").split(",") if o.strip()}
        if origin.rstrip("/") not in extra:  # e.g. a reverse proxy / vite dev server: MT_ALLOWED_ORIGINS
            raise HTTPException(403, "origine refusée (voir MT_ALLOWED_ORIGINS)")

    @app.put("/api/config")
    async def put_config(body: ConfigBody, request: Request) -> dict[str, Any]:
        same_origin(request)
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
                         room_url=(body.room_url or "").strip() or None,
                         wake_room=current.wake_room if body.wake_room is None else body.wake_room,
                         scout_checked=current.scout_checked if body.scout_checked is None else body.scout_checked,
                         room_dashboard=current.room_dashboard if body.room_dashboard is None else body.room_dashboard,
                         hints_foreign_logic=(current.hints_foreign_logic if body.hints_foreign_logic is None
                                              else body.hints_foreign_logic))
        await service.reload(new, before_start=lambda: save_config(new))
        return {"ok": True, "slots": len(slots)}

    # async on purpose: the trackers are mutated on the event loop
    @app.get("/api/hints")
    async def hints(request: Request) -> dict[str, Any]:
        """Hints of every tracked slot, with whether the player who has to do the check can do it now."""
        return get_service(request).hints.table()

    @app.get("/api/items/recent")
    async def recent_items(request: Request) -> dict[str, Any]:
        return {"items": get_service(request).recent_items()}

    @app.get("/api/history")
    async def history(request: Request, kind: str = "sent", slot: list[str] | None = Query(None), limit: int = 200,
                      offset: int = 0) -> dict[str, Any]:
        """Checks made (kind=sent) or items received, newest first; `slot` (repeatable): only these slots."""
        service = get_service(request)
        if kind not in ("sent", "received"):
            raise HTTPException(400, "kind : sent ou received")
        for name in slot or []:
            require_slot(service, name)
        return service.history_page(kind, slot or None, max(1, min(limit, 1000)), max(0, offset))

    def require_roomfeed(request: Request) -> Any:
        feed = get_service(request).roomfeed
        if feed is None:
            raise HTTPException(404, "tableau de bord de la room désactivé")
        return feed

    # async on purpose: the feed is mutated on the event loop, never read it from a worker thread
    @app.get("/api/roomfeed")
    async def roomfeed_status(request: Request) -> dict[str, Any]:
        feed = get_service(request).roomfeed
        return {"enabled": False} if feed is None else feed.status()

    @app.get("/api/roomfeed/summary")
    async def roomfeed_summary(request: Request) -> dict[str, Any]:
        return require_roomfeed(request).summary()

    @app.get("/api/roomfeed/checks")
    async def roomfeed_checks(request: Request, limit: int = 50, offset: int = 0, player: str | None = None,
                              slot: str | None = None, game: str | None = None) -> dict[str, Any]:
        """Checks made in the whole room, newest first (`player`, `slot`, `game`: optional filters)."""
        feed = require_roomfeed(request)
        return feed.checks(max(1, min(limit, 500)), max(0, offset), player or None, slot or None, game or None)

    @app.get("/api/roomfeed/activity")
    async def roomfeed_activity(request: Request, bucket: str = "hour", player: str | None = None) -> dict[str, Any]:
        feed = require_roomfeed(request)
        if bucket not in ("hour", "day"):
            raise HTTPException(400, "bucket : hour ou day")
        return feed.activity(bucket, player or None)

    @app.get("/api/slots/{name:path}")
    async def slot_detail(name: str, request: Request) -> dict[str, Any]:
        service = get_service(request)
        require_slot(service, name)
        return service.detail(name)

    @app.post("/api/slots/{name:path}/seen")
    async def mark_seen(name: str, request: Request, body: SeenBody | None = None) -> dict[str, Any]:
        same_origin(request)
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
                yield f"event: room\ndata: {json.dumps(service.room_event())}\n\n"
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

    @app.get("/api/logs/stream")
    async def log_stream(request: Request, lines: int = 300) -> StreamingResponse:
        """The app's log like `tail -f`: event `init` (last lines), then `lines` as they are written,
        `reset` when the file was rotated. Read only; the room password is masked."""
        lines = max(0, min(lines, 2000))
        secrets = [get_service(request).config.password]

        async def stream() -> AsyncIterator[str]:
            yield "retry: 3000\n\n"
            missing = log_file is None or not log_file.is_file()  # e.g. app not started by scripts/app.sh
            first, offset, inode = ([], 0, 0) if log_file is None else \
                await asyncio.to_thread(last_lines, log_file, lines)
            yield f"event: init\ndata: {json.dumps({'lines': mask(first, secrets), 'missing': missing})}\n\n"
            follower = None if log_file is None else Follower(log_file, offset, inode)
            started = idle = time.monotonic()
            while time.monotonic() - started < LOG_STREAM_MAX:
                if await request.is_disconnected():
                    break
                await asyncio.sleep(LOG_POLL)
                if follower is None:
                    continue
                reset, new = await asyncio.to_thread(follower.poll)
                if reset:
                    yield f"event: reset\ndata: {{}}\n\n"
                if new:
                    idle = time.monotonic()
                    yield f"event: lines\ndata: {json.dumps({'lines': mask(new, secrets)})}\n\n"
                elif time.monotonic() - idle > SSE_KEEPALIVE:
                    idle = time.monotonic()
                    yield ": keepalive\n\n"

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
