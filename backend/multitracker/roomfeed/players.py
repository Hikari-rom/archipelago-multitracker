"""Group the room's slots into players: automatic rule from the slot names, then manual corrections
(config/room_players.yaml, `slot: player`)."""
from __future__ import annotations

import logging
from pathlib import Path

import yaml

from ..apenv import ROOT

log = logging.getLogger(__name__)

OVERRIDES_PATH = ROOT / "config" / "room_players.yaml"
MIN_PREFIX = 3  # bases sharing this many first letters belong to the same player


def _base(name: str) -> str:
    return name.split("_", 1)[0] or name


def _common_prefix(words: list[str]) -> str:
    first, last = min(words), max(words)
    i = 0
    while i < min(len(first), len(last)) and first[i] == last[i]:
        i += 1
    return first[:i]


def group_players(names: list[str], overrides: dict[str, str] | None = None) -> dict[str, str]:
    """Slot name -> player. Base = text before the first "_"; bases sharing their first MIN_PREFIX letters
    (case-insensitive) form one player, named after their longest common prefix (casing of the first name)."""
    bases = {n: _base(n) for n in names}
    clusters: dict[str, list[str]] = {}
    for base in dict.fromkeys(b.lower() for b in bases.values()):
        clusters.setdefault(base[:MIN_PREFIX], []).append(base)
    label: dict[str, str] = {}  # lowered base -> player
    for members in clusters.values():
        prefix = _common_prefix(members)
        original = next(b for b in bases.values() if b.lower() in members)
        for m in members:
            label[m] = original[:len(prefix)]
    result = {n: label[b.lower()] for n, b in bases.items()}
    for slot, player in (overrides or {}).items():
        if slot in result:
            result[slot] = player
    return result


def load_overrides(path: Path = OVERRIDES_PATH) -> dict[str, str]:
    """`slot: player` pairs; a missing or unreadable file means no correction."""
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    except (OSError, UnicodeDecodeError, yaml.YAMLError) as exc:
        log.warning("room players file %s ignored: %s", path, exc)
        return {}
    if not isinstance(raw, dict):
        return {}
    return {str(k): str(v).strip() for k, v in raw.items()
            if isinstance(v, (str, int)) and not isinstance(v, bool) and str(v).strip()}
