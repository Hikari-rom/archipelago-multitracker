"""Room configuration (config/room.yaml)."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from .apenv import ROOT

DEFAULT_CONFIG = ROOT / "config" / "room.yaml"


class ConfigError(ValueError):
    pass


@dataclass
class SlotConfig:
    name: str
    game: str | None = None
    yaml: Path | None = None  # player yaml, used by the logic engine when the world needs it
    owner: str | None = None  # player owning the slot (multi-player support)


@dataclass
class RoomConfig:
    server: str
    password: str = ""
    slots: list[SlotConfig] = field(default_factory=list)
    path: Path | None = None
    room_url: str | None = None  # archipelago.gg room link: the port is refreshed from it
    wake_room: bool = False  # load the room page (which starts a sleeping room) when the server is unreachable
    scout_checked: bool = True  # ask the server what the checked locations held (History page; no spoiler)
    room_dashboard: bool = False  # room-wide dashboard (roomfeed): extra listener + check log
    # Indices page: follow (read-only) the untracked slots that hold hinted items of tracked slots, for their logic
    hints_foreign_logic: bool = True

    def slot(self, name: str) -> SlotConfig | None:
        return next((s for s in self.slots if s.name == name), None)


def config_path() -> Path:
    return Path(os.environ.get("MT_CONFIG", DEFAULT_CONFIG))


def load(path: Path | None = None) -> RoomConfig:
    path = Path(path or config_path())
    if not path.exists():
        raise ConfigError(f"{path} introuvable : copie config/room.example.yaml en config/room.yaml")
    with open(path, encoding="utf-8") as fh:
        raw = yaml.safe_load(fh) or {}
    if not isinstance(raw, dict) or not (raw.get("server") or raw.get("room_url")):
        raise ConfigError(f"{path} : il faut 'server' ou 'room_url'")
    slots: list[SlotConfig] = []
    seen: set[str] = set()
    for i, entry in enumerate(raw.get("slots") or []):
        if isinstance(entry, str):
            entry = {"name": entry}
        if not isinstance(entry, dict) or not entry.get("name"):
            raise ConfigError(f"{path} : slots[{i}] doit avoir un 'name'")
        name = str(entry["name"])
        if name in seen:
            raise ConfigError(f"{path} : le slot {name!r} apparaît deux fois")
        seen.add(name)
        yaml_path = entry.get("yaml")
        if yaml_path:
            yaml_path = Path(yaml_path)
            if not yaml_path.is_absolute():
                yaml_path = ROOT / yaml_path
        slots.append(SlotConfig(name=name, game=entry.get("game"), yaml=yaml_path, owner=entry.get("owner")))
    return RoomConfig(server=str(raw.get("server") or ""), password=str(raw.get("password") or ""), slots=slots,
                      path=path, room_url=raw.get("room_url") or None, wake_room=raw.get("wake_room") is True,
                      scout_checked=raw.get("scout_checked") is not False,
                      room_dashboard=raw.get("room_dashboard") is True,
                      hints_foreign_logic=raw.get("hints_foreign_logic") is not False)


PLAYERS_DIR = ROOT / "config" / "players"


def safe_yaml_path(value: str | None) -> Path | None:
    """Player yamls set from the web UI must live in config/players/ (the logic engine reads them)."""
    if not value:
        return None
    path = Path(value)
    if not path.is_absolute():
        path = ROOT / path
    path = path.resolve()
    if PLAYERS_DIR.resolve() not in path.parents or path.suffix.lower() not in (".yaml", ".yml"):
        raise ConfigError(f"le yaml doit être un fichier .yaml de config/players/ : {value}")
    return path


def save(cfg: RoomConfig, path: Path | None = None) -> Path:
    """Write the config as YAML (atomic replace). The file stays out of git (password)."""
    path = Path(path or cfg.path or config_path())
    data: dict = {}
    if cfg.room_url:
        data["room_url"] = cfg.room_url
    if cfg.server:
        data["server"] = cfg.server
    data["password"] = cfg.password
    data["wake_room"] = cfg.wake_room
    data["scout_checked"] = cfg.scout_checked
    data["room_dashboard"] = cfg.room_dashboard
    data["hints_foreign_logic"] = cfg.hints_foreign_logic
    data["slots"] = []
    for slot in cfg.slots:
        entry: dict = {"name": slot.name}
        if slot.game:
            entry["game"] = slot.game
        if slot.yaml:
            try:
                entry["yaml"] = Path(slot.yaml).resolve().relative_to(ROOT).as_posix()  # same file on Linux and Windows
            except ValueError:
                entry["yaml"] = str(slot.yaml)
        if slot.owner:
            entry["owner"] = slot.owner
        data["slots"].append(entry)
    path.parent.mkdir(parents=True, exist_ok=True)
    content = ("# Écrit par l'app (page Configuration). Modifiable à la main.\n"
               + yaml.safe_dump(data, allow_unicode=True, sort_keys=False)).encode("utf-8")
    if path.exists():
        previous = path.read_bytes()
        if previous != content:
            _write_private(backup_path(path), previous)  # one step back: "Restaurer la configuration précédente"
    _write_private(path, content)
    cfg.path = path
    return path


def backup_path(path: Path | None = None) -> Path:
    path = Path(path or config_path())
    return path.with_name(path.name + ".bak")


def restore_backup(path: Path | None = None) -> RoomConfig:
    """Swap the config file and its backup (so a restore can itself be undone); returns the restored config."""
    path = Path(path or config_path())
    bak = backup_path(path)
    if not bak.exists():
        raise ConfigError("aucune configuration précédente")
    restored = load(bak)  # refuse a broken backup before touching anything
    current = path.read_bytes() if path.exists() else None
    _write_private(path, bak.read_bytes())
    if current is not None:
        _write_private(bak, current)
    restored.path = path
    return restored


def _write_private(path: Path, content: bytes) -> None:
    """Atomic replace, mode 0600 (the file holds the room password)."""
    tmp = path.with_name(path.name + ".tmp")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        os.write(fd, content)
        os.fsync(fd)
    finally:
        os.close(fd)
    tmp.replace(path)
