"""Logic engine used by the app: Universal Tracker in a separate worker process.

Archipelago generation code is CPU-heavy, uses global state and is not thread-safe, so it
runs in its own process. Requests are serialized; a crashed or stuck worker is restarted.
Which games get logic is decided by `logic: true` in config/apworlds.yaml (games validated
by the reference tests) — the others show "Logique indisponible".
"""
from __future__ import annotations

import asyncio
import time
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


def game_catalog(path: Path = APWORLDS_CONFIG) -> dict[str, dict[str, bool]]:
    """game name -> {"logic": enabled, "needs_yaml": the logic needs the player's yaml, "user": apworld imported by
    each user (D27)}, from config/apworlds.yaml."""
    try:
        config = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except OSError:
        return {}
    return {entry["game"]: {"logic": bool(entry.get("logic", False)), "needs_yaml": bool(entry.get("needs_yaml", False)),
                            "user": entry.get("source") == "user"}
            for entry in (config.get("apworlds") or {}).values() if entry.get("game")}


_go_mode_cache: tuple[float, set[str]] | None = None


def go_mode_disabled(path: Path = APWORLDS_CONFIG) -> set[str]:
    """Games with `go_mode: false` in config/apworlds.yaml (victory condition not reliable, D34). Cached by mtime."""
    global _go_mode_cache
    try:
        mtime = path.stat().st_mtime
    except OSError:
        return set()
    if _go_mode_cache is None or _go_mode_cache[0] != mtime:
        try:
            config = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        except (OSError, yaml.YAMLError):
            return set()
        _go_mode_cache = (mtime, {entry["game"] for entry in (config.get("apworlds") or {}).values()
                                  if entry.get("game") and entry.get("go_mode") is False})
    return _go_mode_cache[1]


# Shown after « Logique indisponible : » (docs/COMPAT.md has the details, for us).
NO_LOGIC_REASONS = {
    "Ocarina of Time": "impossible pour Ocarina of Time : les récompenses de donjon (pierres, médaillons) ne sont "
                       "connues que du spoiler",
}
STILL_TRACKED = "ses checks et ses items restent suivis"


def no_logic_reason(game: str, known: bool) -> str:
    """Why a game has no logic: impossible, not reliable enough yet, or not supported by the app."""
    if game in NO_LOGIC_REASONS:
        return f"{NO_LOGIC_REASONS[game]} ; {STILL_TRACKED}"
    if known:
        return f"la logique de ce jeu n'est pas encore assez fiable pour être affichée ; {STILL_TRACKED}"
    return f"le multitracker ne sait pas encore calculer la logique de ce jeu ; {STILL_TRACKED}"


class UTLogicEngine(LogicEngine):
    def __init__(self, games: dict[str, bool] | None = None, timeout: float = 300.0) -> None:
        self.games = enabled_games() if games is None else games
        self.timeout = timeout
        self._ctx = mp.get_context("spawn")
        self._proc = None
        self._conn = None
        self._lock = asyncio.Lock()
        # slot -> timeouts in a row: a slot that never finishes in time kills the worker, which drops every other
        # slot's regenerated world (20-30 s of imports, then all recomputed); after MAX_TIMEOUTS it is not sent again
        self._timeouts: dict[str, int] = {}

    MAX_TIMEOUTS = 2

    async def start(self) -> None:
        async with self._lock:
            await asyncio.to_thread(self._spawn)
        self._prewarm = asyncio.create_task(self._ping())  # import AP's worlds before the first request

    async def _ping(self) -> None:
        async with self._lock:
            try:
                await asyncio.to_thread(self._roundtrip, {"op": "ping"})
            except Exception as exc:
                log.warning("logic worker prewarm failed: %s", exc)

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
        if getattr(self, "_prewarm", None) is not None:
            self._prewarm.cancel()
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

    async def forget(self, slot_name: str) -> None:
        async with self._lock:
            if self._proc is None or not self._proc.is_alive():
                return  # a new worker keeps nothing
            try:
                await asyncio.to_thread(self._roundtrip, {"op": "forget", "slot_name": slot_name})
            except (TimeoutError, EOFError, OSError, BrokenPipeError) as exc:
                log.warning("logic worker failed (%s), restarting it", exc)
                await asyncio.to_thread(self._kill)

    async def checksums(self, games: list[str]) -> dict[str, str | None] | None:
        async with self._lock:
            if self._proc is None or not self._proc.is_alive():
                await asyncio.to_thread(self._spawn)
            try:
                res = await asyncio.to_thread(self._roundtrip, {"op": "checksums", "games": list(games)})
            except (TimeoutError, EOFError, OSError, BrokenPipeError) as exc:
                log.warning("logic worker failed (%s), restarting it", exc)
                await asyncio.to_thread(self._kill)
                return None
        return res.get("checksums") if res.get("state") == "ok" else None

    async def goal_options(self, games: list[str]) -> dict[str, list[dict[str, Any]]] | None:
        async with self._lock:
            if self._proc is None or not self._proc.is_alive():
                await asyncio.to_thread(self._spawn)
            try:
                res = await asyncio.to_thread(self._roundtrip, {"op": "goal_options", "games": list(games)})
            except (TimeoutError, EOFError, OSError, BrokenPipeError) as exc:
                log.warning("logic worker failed (%s), restarting it", exc)
                await asyncio.to_thread(self._kill)
                return None
        return res.get("options") if res.get("state") == "ok" else None

    async def compute(self, request: LogicRequest) -> LogicResult:
        if not self.games.get(request.game, False):
            return LogicResult("unavailable", message=no_logic_reason(request.game, request.game in self.games))
        req = {"op": "update", "slot_name": request.slot_name, "game": request.game, "team": request.team,
               "slot": request.slot, "slot_data": request.slot_data,
               "yaml": str(request.yaml) if request.yaml else None,
               "items": request.items, "missing": sorted(request.missing),
               "checked": sorted(request.checked), "seed_name": request.seed_name,
               "checksum": request.checksum, "explain": sorted(request.explain),
               "goal": dict(request.goal)}
        if self._timeouts.get(request.slot_name, 0) >= self.MAX_TIMEOUTS:
            return LogicResult("error", message=f"Le calcul de logique dépasse {self.timeout / 60:.0f} min pour ce "
                                                "slot : abandonné jusqu'au prochain redémarrage de l'app")
        async with self._lock:
            if self._proc is None or not self._proc.is_alive():
                await asyncio.to_thread(self._spawn)
            try:
                started = time.monotonic()
                res = await asyncio.to_thread(self._roundtrip, req)
            except (TimeoutError, EOFError, OSError, BrokenPipeError) as exc:
                log.warning("logic worker failed on %s (%s) (%s), restarting it", request.slot_name, request.game, exc)
                if isinstance(exc, TimeoutError):
                    self._timeouts[request.slot_name] = self._timeouts.get(request.slot_name, 0) + 1
                await asyncio.to_thread(self._kill)
                return LogicResult("error", message=f"Le calcul de logique a échoué ({type(exc).__name__})")
        self._timeouts.pop(request.slot_name, None)
        took = time.monotonic() - started
        if took > 60:
            log.info("logic of %s (%s) took %.0f s", request.slot_name, request.game, took)
        state = res.get("state", "error")
        if state != "ok":
            return LogicResult(state, message=res.get("message"))
        return LogicResult("ok", in_logic=list(res.get("in_logic", [])),
                           regions={int(k): v for k, v in (res.get("regions") or {}).items()},
                           blockers={int(k): v for k, v in (res.get("blockers") or {}).items()},
                           message=("; ".join(res["errors"]) if res.get("errors") else None),
                           note=res.get("note"), goal_in_logic=res.get("goal_in_logic"))


def default_engine() -> LogicEngine:
    games = enabled_games()
    if not any(games.values()):
        return NullLogicEngine()
    return UTLogicEngine(games)
