"""Make the vendored Archipelago importable (headless, no requirement auto-update)."""
from __future__ import annotations

import importlib.abc
import importlib.util
import logging
import os
import sys
import warnings
import zipimport
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
AP_DIR = ROOT / "vendor" / "Archipelago"
STUBS_DIR = ROOT / "backend" / "ap_stubs"
CATALOG = ROOT / "config" / "apworlds.yaml"


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
    _install_core_overrides()
    _sort_resource_listdir()
    return AP_DIR


class _CoreOverrideFinder(importlib.abc.MetaPathFinder):
    """Imports `worlds.<module>` from an apworld instead of the core world folder of the same name."""

    def __init__(self) -> None:
        self.apworlds: dict[str, Path] = {}

    def find_spec(self, fullname, path, target=None):
        apworld = self.apworlds.get(fullname)
        if apworld is None or not apworld.is_file():
            return None
        return zipimport.zipimporter(str(apworld)).find_spec(fullname)


_core_overrides = _CoreOverrideFinder()


def core_overrides(catalog: Path = CATALOG) -> dict[str, Path]:
    """`worlds.<module>` -> apworld, for the catalog entries with `replaces_core: true` (D28).

    AP 0.6.7 loads its core world folders first and skips an apworld whose game is already loaded: a room generated
    with a newer version of a core world (TUNIC) would keep the old logic.
    """
    try:
        import yaml
        entries = (yaml.safe_load(catalog.read_text(encoding="utf-8")) or {}).get("apworlds") or {}
    except (OSError, ValueError, ImportError):
        return {}
    out = {}
    for entry in entries.values():
        filename = str(entry.get("filename") or "")
        if entry.get("replaces_core") and filename.endswith(".apworld"):
            out[f"worlds.{filename[:-len('.apworld')]}"] = AP_DIR / "custom_worlds" / filename
    return out


def _install_core_overrides() -> None:
    _core_overrides.apworlds = core_overrides()
    if _core_overrides not in sys.meta_path:
        sys.meta_path.insert(0, _core_overrides)


def _sort_resource_listdir() -> None:
    """List a world's data folders in name order, as Windows (NTFS) does, not in ext4's hash order.

    Pokemon Emerald builds its regions in `pkg_resources.resource_listdir` order: the datapackage holds the same
    names either way, but its checksum (D12) follows that order and the rooms are generated on Windows.
    """
    if getattr(_sort_resource_listdir, "done", False):
        return
    _sort_resource_listdir.done = True
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            import pkg_resources
    except ImportError:
        return
    listdir = pkg_resources.resource_listdir

    def resource_listdir(package_or_requirement, resource_name):
        names = listdir(package_or_requirement, resource_name)
        if isinstance(pkg_resources.get_provider(package_or_requirement), pkg_resources.ZipProvider):
            return names  # an apworld: same order as on Windows already
        return sorted(names)

    pkg_resources.resource_listdir = resource_listdir


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
