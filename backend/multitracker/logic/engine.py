"""Logic engine used by the app: Universal Tracker in a separate worker process.

Archipelago generation code is CPU-heavy, uses global state and is not thread-safe, so it
runs in its own process. Requests are serialized; a crashed or stuck worker is restarted.
Which games get logic is decided by `logic: true` in config/apworlds.yaml (games validated
by the reference tests) — the others show "Logique indisponible".
"""
from __future__ import annotations

import asyncio
import logging
import multiprocessing as mp
from pathlib import Path
from typing import Any

import yaml

from ..apenv import ROOT
from . import LogicEngine, LogicRequest, LogicResult, NullLogicEngine

log = logging.getLogger(__name__)
APWORLDS_CONFIG = ROOT / "config" / "apworlds.yaml"


def enabled_games(path: Path = APWORLDS_CONFIG) -> dict[str, bool]:
    """game name -> logic enabled, from config/apworlds.yaml."""
    try:
        config = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except OSError:
        return {}
    return {entry["game"]: bool(entry.get("logic", False))
            for entry in (config.get("apworlds") or {}).values() if entry.get("game")}


class UTLogicEngine(LogicEngine):
    def __init__(self, games: dict[str, bool] | None = None, timeout: float = 300.0) -> None:
        self.games = enabled_games() if games is None else games
        self.timeout = timeout
        self._ctx = mp.get_context("spawn")
        self._proc = None
        self._conn = None
        self._lock = asyncio.Lock()

    async def start(self) -> None:
        async with self._lock:
            await asyncio.to_thread(self._spawn)

    def _spawn(self) -> None:
        from .ut_worker import worker_main
        parent, child = self._ctx.Pipe()
        proc = self._ctx.Process(target=worker_main, args=(child,), name="multitracker-logic", daemon=True)
        proc.start()
        child.close()
        self._proc, self._conn = proc, parent
        log.info("logic worker started (pid %s)", proc.pid)

    def _kill(self) -> None:
        if self._proc is not None and self._proc.is_alive():
            self._proc.kill()
            self._proc.join(5)
        self._proc = self._conn = None

    async def stop(self) -> None:
        async with self._lock:
            if self._conn is not None:
                try:
                    self._conn.send(None)
                except OSError:
                    pass
            if self._proc is not None:
                await asyncio.to_thread(self._proc.join, 5)
            self._kill()

    def _roundtrip(self, req: dict[str, Any]) -> dict[str, Any]:
        self._conn.send(req)
        if not self._conn.poll(self.timeout):
            raise TimeoutError(f"logic worker did not answer within {self.timeout:.0f}s")
        return self._conn.recv()

    async def compute(self, request: LogicRequest) -> LogicResult:
        if not self.games.get(request.game, False):
            return LogicResult("unavailable", message="Logique non validée pour ce jeu (voir docs/COMPAT.md)")
        req = {"op": "update", "slot_name": request.slot_name, "game": request.game, "team": request.team,
               "slot": request.slot, "slot_data": request.slot_data,
               "yaml": str(request.yaml) if request.yaml else None,
               "items": request.items, "missing": sorted(request.missing)}
        async with self._lock:
            if self._proc is None or not self._proc.is_alive():
                await asyncio.to_thread(self._spawn)
            try:
                res = await asyncio.to_thread(self._roundtrip, req)
            except (TimeoutError, EOFError, OSError, BrokenPipeError) as exc:
                log.warning("logic worker failed (%s), restarting it", exc)
                await asyncio.to_thread(self._kill)
                return LogicResult("error", message=f"Le calcul de logique a échoué ({type(exc).__name__})")
        state = res.get("state", "error")
        if state != "ok":
            return LogicResult(state, message=res.get("message"))
        return LogicResult("ok", in_logic=list(res.get("in_logic", [])),
                           message=("; ".join(res["errors"]) if res.get("errors") else None))


def default_engine() -> LogicEngine:
    games = enabled_games()
    if not any(games.values()):
        return NullLogicEngine()
    return UTLogicEngine(games)
