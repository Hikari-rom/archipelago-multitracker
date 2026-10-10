"""Make the vendored Archipelago importable (headless, no requirement auto-update)."""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
AP_DIR = ROOT / "vendor" / "Archipelago"
STUBS_DIR = ROOT / "backend" / "ap_stubs"


def setup() -> Path:
    """Put Archipelago and our stubs on sys.path. Idempotent. Returns the AP directory."""
    if not AP_DIR.is_dir():
        raise RuntimeError(f"Archipelago not found in {AP_DIR}: run scripts/bootstrap.sh")
    os.environ.setdefault("SKIP_REQUIREMENTS_UPDATE", "1")
    for path in (str(STUBS_DIR), str(AP_DIR)):
        if path not in sys.path:
            sys.path.insert(0, path)
    return AP_DIR


def subprocess_env() -> dict[str, str]:
    """Environment for a child Python process that runs Archipelago code."""
    env = dict(os.environ)
    env["SKIP_REQUIREMENTS_UPDATE"] = "1"
    env["PYTHONPATH"] = os.pathsep.join(filter(None, [str(STUBS_DIR), str(AP_DIR), env.get("PYTHONPATH")]))
    return env
