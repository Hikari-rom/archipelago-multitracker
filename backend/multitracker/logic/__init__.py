"""Logic engine interface: which missing locations are in logic with the items received so far."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class LogicRequest:
    slot_name: str
    game: str
    team: int
    slot: int
    slot_data: dict[str, Any]
    yaml: Path | None
    items: list[dict[str, Any]]  # NetworkItem dicts (item, location, player, flags)
    missing: set[int]
    checked: set[int]
    seed_name: str | None = None


@dataclass
class LogicResult:
    # ok: computed · unavailable: no logic for this game/slot · pending: not computed yet · error: failed
    state: str
    in_logic: list[int] = field(default_factory=list)
    message: str | None = None
    regions: dict[int, str] = field(default_factory=dict)  # location id -> region name (when known)
    computed_at: float = field(default_factory=time.time)
    seconds: float | None = None

    def to_json(self) -> dict[str, Any]:
        return {"state": self.state, "count": len(self.in_logic), "message": self.message,
                "computed_at": self.computed_at, "seconds": self.seconds}


class LogicEngine:
    async def start(self) -> None:
        pass

    async def stop(self) -> None:
        pass

    async def compute(self, request: LogicRequest) -> LogicResult:
        raise NotImplementedError


class NullLogicEngine(LogicEngine):
    """No logic at all: every slot is "Logique indisponible"."""

    async def compute(self, request: LogicRequest) -> LogicResult:
        return LogicResult("unavailable", message="Moteur de logique désactivé")
