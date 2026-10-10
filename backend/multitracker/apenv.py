"""Make the vendored Archipelago importable (headless, no requirement auto-update)."""
from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
AP_DIR = ROOT / "vendor" / "Archipelago"
STUBS_DIR = ROOT / "backend" / "ap_stubs"


# Modules stubbed in STUBS_DIR, used only when the real package is not installed.
STUBBED_MODULES = ("dolphin_memory_engine",)


def _needs_stubs() -> bool:
    return any(importlib.util.find_spec(name) is None for name in STUBBED_MODULES
               if str(STUBS_DIR) not in sys.path)


def setup() -> Path:
    """Put Archipelago (and, if needed, our stubs) on sys.path. Idempotent. Returns the AP directory."""
    if not AP_DIR.is_dir():
        raise RuntimeError(f"Archipelago not found in {AP_DIR}: run scripts/bootstrap.sh")
    os.environ.setdefault("SKIP_REQUIREMENTS_UPDATE", "1")
    # Universal Tracker's settings point at <AP>/Players; if it is missing, AP's settings code
    # opens a (tkinter) folder picker. Never needed headless: make sure the folder exists.
    (AP_DIR / "Players").mkdir(exist_ok=True)
    if _needs_stubs():
        sys.path.append(str(STUBS_DIR))  # after site-packages: never shadows a real install
    if str(AP_DIR) not in sys.path:
        sys.path.insert(0, str(AP_DIR))
    return AP_DIR


def subprocess_env() -> dict[str, str]:
    """Environment for a child Python process that runs Archipelago code."""
    env = dict(os.environ)
    env["SKIP_REQUIREMENTS_UPDATE"] = "1"
    paths = [str(AP_DIR)]
    if _needs_stubs():
        paths.append(str(STUBS_DIR))
    env["PYTHONPATH"] = os.pathsep.join(filter(None, paths + [env.get("PYTHONPATH")]))
    return env
