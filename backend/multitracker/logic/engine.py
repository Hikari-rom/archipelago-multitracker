"""Factory for the logic engine used by the app."""
from __future__ import annotations

from . import LogicEngine, NullLogicEngine


def default_engine() -> LogicEngine:
    return NullLogicEngine()
