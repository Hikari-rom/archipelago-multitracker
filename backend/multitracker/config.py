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
                      path=path, room_url=raw.get("room_url") or None)


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
    data["slots"] = []
    for slot in cfg.slots:
        entry: dict = {"name": slot.name}
        if slot.game:
            entry["game"] = slot.game
        if slot.yaml:
            try:
                entry["yaml"] = str(Path(slot.yaml).resolve().relative_to(ROOT))
            except ValueError:
                entry["yaml"] = str(slot.yaml)
        if slot.owner:
            entry["owner"] = slot.owner
        data["slots"].append(entry)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text("# Écrit par l'app (page Configuration). Modifiable à la main.\n"
                   + yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")
    os.chmod(tmp, 0o600)
    tmp.replace(path)
    cfg.path = path
    return path
