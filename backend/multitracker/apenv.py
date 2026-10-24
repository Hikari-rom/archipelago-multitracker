"""Make the vendored Archipelago importable (headless, no requirement auto-update)."""
from __future__ import annotations

import importlib.util
import logging
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
AP_DIR = ROOT / "vendor" / "Archipelago"
STUBS_DIR = ROOT / "backend" / "ap_stubs"


# Modules stubbed in STUBS_DIR, used only when the real package is not installed.
STUBBED_MODULES = ("dolphin_memory_engine",)
_synced = False


def _needs_stubs() -> bool:
    """Whether Archipelago code needs STUBS_DIR: already on our path (setup() ran), or a stubbed module is missing."""
    if str(STUBS_DIR) in sys.path:
        return True
    return any(importlib.util.find_spec(name) is None for name in STUBBED_MODULES)


def setup() -> Path:
    """Put Archipelago (and, if needed, our stubs) on sys.path. Idempotent. Returns the AP directory."""
    if not AP_DIR.is_dir():
        raise RuntimeError(f"Archipelago not found in {AP_DIR}: run scripts/bootstrap.sh")
    os.environ.setdefault("SKIP_REQUIREMENTS_UPDATE", "1")
    # Universal Tracker's settings point at <AP>/Players; if it is missing, AP's settings code
    # opens a (tkinter) folder picker. Never needed headless: make sure the folder exists.
    (AP_DIR / "Players").mkdir(exist_ok=True)
    if _needs_stubs() and str(STUBS_DIR) not in sys.path:
        sys.path.append(str(STUBS_DIR))  # after site-packages: never shadows a real install
    if str(AP_DIR) not in sys.path:
        sys.path.insert(0, str(AP_DIR))
    _sync_user_apworlds()
    return AP_DIR


def _sync_user_apworlds() -> None:
    """Copy the user's imported apworlds (D27) into custom_worlds, once per process, before worlds load."""
    global _synced
    if _synced:
        return
    _synced = True
    from . import user_apworlds
    try:
        user_apworlds.sync()
    except OSError as e:
        logging.getLogger(__name__).warning("imported apworlds not synced: %s", e)


def subprocess_env() -> dict[str, str]:
    """Environment for a child Python process that runs Archipelago code."""
    env = dict(os.environ)
    env["SKIP_REQUIREMENTS_UPDATE"] = "1"
    paths = [str(AP_DIR)]
    if _needs_stubs():
        paths.append(str(STUBS_DIR))
    env["PYTHONPATH"] = os.pathsep.join(filter(None, paths + [env.get("PYTHONPATH")]))
    return env
