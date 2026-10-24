"""Apworlds imported from the user's own Archipelago install (D27).

The app ships the apworlds of config/apworlds.yaml (lock, sha256). The games it does not ship come from the user's
Archipelago `custom_worlds` folder: "Importer" copies them to data/apworlds/ (kept across updates), and every
process that loads Archipelago copies them into its custom_worlds first (`sync`). Only the `source: user` games of
the catalog are imported: an apworld of a game the app ships would replace the validated one, any other brings no
logic. Whether an imported apworld is the room's version is
checked at run time like any other (D12: logic refused when the datapackage checksum differs).

Only reads the archives (manifest, `game = "..."` line); importing never runs their code.
"""
from __future__ import annotations

import filecmp
import json
import logging
import os
import re
import shutil
import sys
import zipfile
from pathlib import Path

import yaml

from .apenv import AP_DIR, ROOT

log = logging.getLogger(__name__)

USER_DIR = ROOT / "data" / "apworlds"
CUSTOM_DIR = AP_DIR / "custom_worlds"
CATALOG = ROOT / "config" / "apworlds.yaml"
RECORD = ".user_apworlds.json"  # in custom_worlds: the files sync() put there
GAME_LINE = re.compile(r"""^\s+game(?:\s*:\s*[\w\[\]]+)?\s*=\s*(["'])(.+?)\1\s*(?:#.*)?$""", re.M)


def apworld_game(path: Path) -> str | None:
    """The game an .apworld registers: its manifest, else the `game = "..."` of its top-level __init__.py."""
    try:
        with zipfile.ZipFile(path) as zf:
            names = zf.namelist()
            for name in names:
                if name == "archipelago.json" or (name.count("/") == 1 and name.endswith("/archipelago.json")):
                    game = json.loads(zf.read(name)).get("game")
                    if isinstance(game, str) and game:
                        return game
            for name in names:
                if name.count("/") == 1 and name.endswith("/__init__.py"):
                    m = GAME_LINE.search(zf.read(name).decode("utf-8", errors="ignore"))
                    if m:
                        return m.group(2)
    except (OSError, zipfile.BadZipFile, ValueError, KeyError):
        return None
    return None


def _catalog_games(catalog: Path | None, user: bool) -> set[str]:
    try:
        config = yaml.safe_load((catalog or CATALOG).read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError):
        return set()
    return {e["game"] for e in (config.get("apworlds") or {}).values()
            if isinstance(e, dict) and e.get("game") and (e.get("source") == "user") == user}


def shipped_games(catalog: Path | None = None) -> set[str]:
    """Games the app itself provides (config/apworlds.yaml entries not marked `source: user`)."""
    return _catalog_games(catalog, user=False)


def user_games(catalog: Path | None = None) -> set[str]:
    """Games whose apworld each user imports (`source: user`): the only ones worth importing."""
    return _catalog_games(catalog, user=True)


def _record(custom: Path) -> list[str]:
    try:
        names = json.loads((custom / RECORD).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    return [n for n in names if isinstance(n, str) and "/" not in n and "\\" not in n] if isinstance(names, list) else []


def shipped_files(custom: Path | None = None) -> set[str]:
    """Apworld files in custom_worlds that sync() did not put there (the lock's, or added by hand)."""
    custom = custom or CUSTOM_DIR
    mine = set(_record(custom))
    return {p.name for p in custom.glob("*.apworld")} - mine if custom.is_dir() else set()


def default_source() -> Path | None:
    """The custom_worlds folder of a usual Archipelago install, if one exists."""
    candidates: list[Path] = []
    if sys.platform == "win32":
        for var in ("ProgramData", "LOCALAPPDATA", "APPDATA"):
            if os.environ.get(var):
                candidates.append(Path(os.environ[var]) / "Archipelago" / "custom_worlds")
        candidates.append(Path("C:/ProgramData/Archipelago/custom_worlds"))
    else:
        home = Path.home()
        candidates += [home / "Archipelago" / "custom_worlds", home / ".local/share/Archipelago/custom_worlds",
                       home / "Applications/Archipelago/custom_worlds"]
    return next((c for c in candidates if c.is_dir()), None)


def _copy(src: Path, dest: Path) -> None:
    tmp = dest.with_name(f"{dest.name}.{os.getpid()}.tmp")
    shutil.copyfile(src, tmp)
    os.replace(tmp, dest)


def import_dir(source: Path, dest: Path | None = None, custom: Path | None = None,
               catalog: Path | None = None) -> list[dict]:
    """Replace data/apworlds/ with the apworlds of `source` for the `source: user` games of the catalog (any other
    one would bring no logic, and tools like a Discord presence have no business running here). One row per
    .apworld of `source`: {file, game, status}, status in imported | shipped | not_needed | unreadable | duplicate."""
    dest = dest or USER_DIR
    if not source.is_dir():
        raise FileNotFoundError(f"dossier introuvable : {source}")
    games, wanted, files = shipped_games(catalog), user_games(catalog), shipped_files(custom)
    rows, chosen, seen = [], {}, set()
    for path in sorted(source.glob("*.apworld"), key=lambda p: p.name.lower()):
        game = None if path.name in files else apworld_game(path)
        if path.name in files or game in games:
            status = "shipped"
        elif game is None:
            status = "unreadable"
        elif game not in wanted:
            status = "not_needed"
        elif game in seen:
            status = "duplicate"
        else:
            status = "imported"
            seen.add(game)
            chosen[path.name] = path
        rows.append({"file": path.name, "game": game, "status": status})
    dest.mkdir(parents=True, exist_ok=True)
    for old in dest.glob("*.apworld"):
        if old.name not in chosen:
            old.unlink()
    for name, path in chosen.items():
        _copy(path, dest / name)
    return rows


def imported(dest: Path | None = None) -> list[dict]:
    """The apworlds of data/apworlds/: {file, game}."""
    dest = dest or USER_DIR
    if not dest.is_dir():
        return []
    return [{"file": p.name, "game": apworld_game(p)} for p in sorted(dest.glob("*.apworld"), key=lambda p: p.name.lower())]


def sync(custom: Path | None = None, user: Path | None = None, catalog: Path | None = None) -> list[str]:
    """Make custom_worlds hold exactly the imported apworlds of `source: user` games (plus the app's own files).
    Leaves an up-to-date copy in place, so concurrent processes never see it missing. Returns the names there."""
    custom, user = custom or CUSTOM_DIR, user or USER_DIR
    if not custom.is_dir():
        return []
    previous = _record(custom)
    games, files = user_games(catalog), shipped_files(custom)
    wanted: dict[str, Path] = {}
    for path in sorted(user.glob("*.apworld")) if user.is_dir() else []:
        if path.name not in files and apworld_game(path) in games:  # else the app's own apworld wins
            wanted[path.name] = path
    for name in previous:
        if name not in wanted:
            (custom / name).unlink(missing_ok=True)
    for name, path in wanted.items():
        dest = custom / name
        if not (dest.is_file() and filecmp.cmp(path, dest, shallow=False)):
            _copy(path, dest)
    record = custom / RECORD
    if wanted:
        tmp = record.with_name(f"{RECORD}.{os.getpid()}.tmp")
        tmp.write_text(json.dumps(sorted(wanted)), encoding="utf-8")
        os.replace(tmp, record)
    else:
        record.unlink(missing_ok=True)
    return sorted(wanted)
