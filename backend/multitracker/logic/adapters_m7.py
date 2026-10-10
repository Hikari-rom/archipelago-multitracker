"""More per-game regeneration adapters (same contract as adapters.py)."""
from __future__ import annotations

from typing import Any, Callable, ContextManager

ADAPTERS_M7: dict[str, Callable[[type, dict[str, Any], set[int]], ContextManager]] = {}
