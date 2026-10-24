"""Player yamls in config/players/ (listing with the slot names/games they describe, upload from the web UI)."""
from __future__ import annotations

import os
import re
import uuid
from pathlib import Path
from typing import Any

import yaml

from .apenv import ROOT
from . import config
from .config import ConfigError

MAX_YAML_BYTES = 512 * 1024
MAX_YAML_FILES = 500
_SAFE_NAME = re.compile(r"[^A-Za-z0-9_.-]+")


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()  # "/" on Windows too: the web UI matches these
    except ValueError:
        return str(path)


def describe(text: str) -> list[dict[str, str]]:
    """The (name, game) of every player document of a yaml. Raises ConfigError if it is not a player yaml."""
    try:
        docs = [d for d in yaml.safe_load_all(text) if d is not None]
    except yaml.YAMLError as exc:
        raise ConfigError(f"yaml illisible : {str(exc).splitlines()[0][:200]}") from exc
    players = []
    for doc in docs:
        if not isinstance(doc, dict):
            continue
        name, game = doc.get("name"), doc.get("game")
        if isinstance(name, str) and isinstance(game, str):
            players.append({"name": name, "game": game})
        elif isinstance(name, str) and isinstance(game, dict):  # weighted games: {"A": 50, "B": 50}
            players.append({"name": name, "game": " | ".join(str(g) for g, w in game.items() if w)})
    if not players:
        raise ConfigError("ce fichier n'a pas de document joueur (clés `name` et `game`)")
    return players


def list_yamls(base: Path | None = None) -> list[dict[str, Any]]:
    """Every .yaml/.yml under config/players/ (subfolders included), with the players it describes."""
    base = base or config.PLAYERS_DIR
    out: list[dict[str, Any]] = []
    if not base.is_dir():
        return out
    files = sorted(p for p in base.rglob("*") if p.suffix.lower() in (".yaml", ".yml") and p.is_file())
    for path in files[:MAX_YAML_FILES]:
        entry: dict[str, Any] = {"path": rel(path), "players": [], "error": None}
        try:
            if path.stat().st_size > MAX_YAML_BYTES:
                raise ConfigError("fichier trop gros")
            entry["players"] = describe(path.read_text(encoding="utf-8-sig"))
        except (ConfigError, OSError, UnicodeDecodeError) as exc:
            entry["error"] = str(exc)
        out.append(entry)
    return out


def safe_filename(name: str) -> str:
    base = Path(name.replace("\\", "/")).name  # never a directory from the browser
    stem, dot, ext = base.rpartition(".")
    if not dot or ext.lower() not in ("yaml", "yml"):
        raise ConfigError("seuls les fichiers .yaml ou .yml sont acceptés")
    stem = _SAFE_NAME.sub("_", stem.replace("&", "and")).strip("._")[:80]
    if not stem:
        raise ConfigError("nom de fichier invalide")
    return f"{stem}.{ext.lower()}"


def save_upload(filename: str, content: str, overwrite: bool = False, base: Path | None = None) -> dict[str, Any]:
    """Store one uploaded player yaml in config/players/. Refuses non-player yamls, huge files and silent
    overwrites (same content = no-op)."""
    base = base or config.PLAYERS_DIR
    data = content.encode("utf-8")
    if len(data) > MAX_YAML_BYTES:
        raise ConfigError(f"fichier trop gros (max {MAX_YAML_BYTES // 1024} Ko)")
    players = describe(content)
    path = base / safe_filename(filename)
    base.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() == data:
            return {"path": rel(path), "players": players, "status": "unchanged"}
        if not overwrite:
            raise FileExistsError(rel(path))
        _atomic_write(path, data)
        return {"path": rel(path), "players": players, "status": "replaced"}
    if sum(1 for p in base.rglob("*") if p.suffix.lower() in (".yaml", ".yml")) >= MAX_YAML_FILES:
        raise ConfigError(f"trop de yamls dans config/players/ (max {MAX_YAML_FILES})")
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)  # never replace a file created meanwhile
    except FileExistsError:
        raise FileExistsError(rel(path)) from None
    try:
        os.write(fd, data)
        os.fsync(fd)
    finally:
        os.close(fd)
    return {"path": rel(path), "players": players, "status": "created"}


def _atomic_write(path: Path, data: bytes) -> None:
    tmp = path.with_name(f".{path.name}.{os.getpid()}.{uuid.uuid4().hex[:8]}.tmp")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        os.write(fd, data)
        os.fsync(fd)
    finally:
        os.close(fd)
    tmp.replace(path)
