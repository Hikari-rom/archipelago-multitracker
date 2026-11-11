"""Disk cache of the victory conditions of each game (Configuration > « Choisir le but à la main », D34).

Reading them needs the logic worker, which imports every world (20-30 s on the Pi) and serves the slots' logic
first: the Configuration page must not wait for it. The cache is valid while the worlds and the code reading them
are the same (fingerprint of the apworld files, the AP version and ut_worker.py).
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
from pathlib import Path
from typing import Any

from .apenv import AP_DIR, CATALOG, ROOT

log = logging.getLogger(__name__)

CACHE_FILE = ROOT / "data" / "cache" / "goal_options.json"
VERSION = 1


def _apworlds(folder: Path) -> list[Path]:
    try:
        return sorted(p for p in folder.iterdir() if p.suffix == ".apworld")
    except OSError:
        return []


def fingerprint(ap_dir: Path = AP_DIR, catalog: Path = CATALOG, user_dir: Path = ROOT / "data" / "apworlds") -> str:
    """Same worlds, same code reading them. Not the file dates of what a release ships: the Windows update extracts
    every file again (new dates), which made the first start after each update wait for the worker."""
    h = hashlib.sha1(str(VERSION).encode())
    small = [catalog, catalog.with_name("apworlds.lock.yaml"), ap_dir / "Utils.py",
             Path(__file__).parent / "logic" / "ut_worker.py"]
    for path in small:  # read whole: a few kB
        try:
            h.update(path.name.encode() + b"\0" + path.read_bytes() + b"\n")
        except OSError:
            continue
    for path in _apworlds(ap_dir / "custom_worlds"):  # shipped with the app: their versions are in the lock file
        try:
            h.update(f"{path.name}\0{path.stat().st_size}\n".encode())
        except OSError:
            continue
    for path in _apworlds(user_dir):  # imported by the user (data/, kept by updates)
        try:
            st = path.stat()
        except OSError:
            continue
        h.update(f"{path.name}\0{st.st_size}\0{st.st_mtime_ns}\n".encode())
    return h.hexdigest()


def load(path: Path = CACHE_FILE, key: str | None = None) -> dict[str, list[dict[str, Any]]]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    if not isinstance(data, dict) or data.get("fingerprint") != (key or fingerprint()):
        return {}
    games = data.get("games")
    return games if isinstance(games, dict) else {}


def save(games: dict[str, list[dict[str, Any]]], path: Path = CACHE_FILE, key: str | None = None) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_name(path.name + ".tmp")
        tmp.write_text(json.dumps({"fingerprint": key or fingerprint(), "games": games}, ensure_ascii=False),
                       encoding="utf-8")
        os.replace(tmp, path)
    except OSError as exc:
        log.warning("goal options cache not written: %s", exc)
