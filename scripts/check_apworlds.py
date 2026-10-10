#!/usr/bin/env python3
"""Check that every apworld from config/apworlds.yaml loads on the vendored Archipelago.

Each game is checked in a fresh subprocess (an apworld that breaks at import time
cannot affect the others). Prints a table and writes the raw results as JSON
to test-output/apworld_check.json.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
AP = ROOT / "vendor" / "Archipelago"
OUT = ROOT / "test-output" / "apworld_check.json"
STUBS = ROOT / "backend" / "ap_stubs"

PROBE = r"""
import io, json, sys, traceback, contextlib
game = sys.argv[1]
buf = io.StringIO()
result = {"game": game}
try:
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        import worlds
        from worlds.AutoWorld import AutoWorldRegister
    result["loaded"] = game in AutoWorldRegister.world_types
    if result["loaded"]:
        w = AutoWorldRegister.world_types[game]
        result["module"] = w.__module__
        result["locations"] = len(w.location_name_to_id)
        result["items"] = len(w.item_name_to_id)
        result["ut_can_gen_without_yaml"] = bool(getattr(w, "ut_can_gen_without_yaml", False))
        result["interpret_slot_data"] = hasattr(w, "interpret_slot_data")
    result["failed_world_loads"] = list(worlds.failed_world_loads)
except BaseException as exc:
    result["loaded"] = False
    result["error"] = "".join(traceback.format_exception_only(type(exc), exc)).strip()
result["log_tail"] = buf.getvalue()[-3000:]
print("@@RESULT@@" + json.dumps(result))
"""


def check(game: str) -> dict:
    env = {**os.environ, "SKIP_REQUIREMENTS_UPDATE": "1",
           "PYTHONPATH": os.pathsep.join(filter(None, [str(STUBS), os.environ.get("PYTHONPATH")]))}
    proc = subprocess.run([sys.executable, "-c", PROBE, game], cwd=AP, env=env,
                          capture_output=True, text=True, timeout=600)
    for line in proc.stdout.splitlines():
        if line.startswith("@@RESULT@@"):
            return json.loads(line[len("@@RESULT@@"):])
    return {"game": game, "loaded": False, "error": (proc.stderr or proc.stdout)[-2000:]}


def main() -> int:
    config = yaml.safe_load((ROOT / "config" / "apworlds.yaml").read_text(encoding="utf-8"))
    entries = {**config.get("apworlds", {}), **config.get("tools", {})}
    only = set(sys.argv[1:])
    results = json.loads(OUT.read_text()) if OUT.exists() else {}
    for key, entry in entries.items():
        if only and key not in only:
            continue
        res = check(entry["game"])
        results[key] = res
        status = "OK " if res.get("loaded") else "KO "
        extra = f"{res.get('locations', '?')} loc, UT-noyaml={res.get('ut_can_gen_without_yaml')}" \
            if res.get("loaded") else (res.get("error") or "not registered")[:200]
        print(f"{status} {key:20} {entry['game']:45} {extra}", flush=True)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(results, indent=2), encoding="utf-8")
    return 0 if all(results[k].get("loaded") for k in entries if k in results) else 1


if __name__ == "__main__":
    sys.exit(main())
