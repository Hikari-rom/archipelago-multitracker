#!/usr/bin/env python3
"""Inventory of the games of the configured room (M14, decision D12).

For every game of the room: number of slots, whether an apworld is installed here (core Archipelago or custom),
and whether its datapackage checksum is the one the room was generated with (otherwise its logic could come from
another version and lie). Reads the room through the WebHost API only (`/api/room_status`, `/api/static_tracker`):
neither wakes a sleeping room. Writes docs/COMPAT-room.md and test-output/room_inventory.json.

Usage: .venv/bin/python scripts/room_inventory.py [room_url]   (default: room_url of config/room.yaml)
"""
from __future__ import annotations

import collections
import json
import subprocess
import sys
import urllib.request
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
AP = ROOT / "vendor" / "Archipelago"
OUT_MD = ROOT / "docs" / "COMPAT-room.md"
OUT_JSON = ROOT / "test-output" / "room_inventory.json"

PROBE = r"""
import io, json, sys, contextlib
buf = io.StringIO()
with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
    import worlds
    from worlds.AutoWorld import AutoWorldRegister
out = {}
for game, w in AutoWorldRegister.world_types.items():
    path = getattr(sys.modules.get(w.__module__), "__file__", "") or ""
    out[game] = {
        "checksum": worlds.network_data_package["games"].get(game, {}).get("checksum"),
        "custom": "custom_worlds" in path or ".apworld" in path,
        "ut_can_gen_without_yaml": bool(getattr(w, "ut_can_gen_without_yaml", False)),
    }
print("@@RESULT@@" + json.dumps(out))
"""


def fetch(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "archipelago-multitracker"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())


def local_worlds() -> dict[str, dict]:
    sys.path.insert(0, str(ROOT / "backend"))
    from multitracker import apenv
    apenv.setup()
    proc = subprocess.run([sys.executable, "-c", PROBE], cwd=AP, env=apenv.subprocess_env(),
                          capture_output=True, text=True, timeout=900)
    for line in proc.stdout.splitlines():
        if line.startswith("@@RESULT@@"):
            return json.loads(line[len("@@RESULT@@"):])
    raise RuntimeError((proc.stderr or proc.stdout)[-2000:])


def main() -> int:
    room_url = sys.argv[1] if len(sys.argv) > 1 else yaml.safe_load((ROOT / "config" / "room.yaml").read_text())["room_url"]
    base, room_id = room_url.rstrip("/").split("/room/")
    status = fetch(f"{base}/api/room_status/{room_id}")
    tracker = fetch(f"{base}/api/static_tracker/{status['tracker']}")
    slots = collections.Counter(game for _, game in status["players"])
    room_sums = {game: info.get("checksum") for game, info in tracker["datapackage"].items()}
    configured = {s.get("game") for s in yaml.safe_load((ROOT / "config" / "room.yaml").read_text()).get("slots", [])}
    enabled = {e["game"] for e in yaml.safe_load((ROOT / "config" / "apworlds.yaml").read_text())["apworlds"].values()
               if e.get("logic")}
    local = local_worlds()

    rows = []
    for game, count in sorted(slots.items(), key=lambda kv: (-kv[1], kv[0].lower())):
        mine = local.get(game)
        room_sum = room_sums.get(game)
        if mine is None:
            state = "absent"
        elif room_sum and mine["checksum"] == room_sum:
            state = "identique"
        else:
            state = "différent"
        rows.append({"game": game, "slots": count, "installed": mine is not None,
                     "kind": None if mine is None else ("custom" if mine["custom"] else "core"),
                     "checksum": state, "room_checksum": room_sum,
                     "local_checksum": mine and mine["checksum"],
                     "ut_can_gen_without_yaml": bool(mine and mine["ut_can_gen_without_yaml"]),
                     "romain": game in configured, "logic": game in enabled})
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(rows, indent=1), encoding="utf-8")

    def line(r: dict) -> str:
        installed = "—" if not r["installed"] else r["kind"]
        check = {"identique": "✅", "différent": "❌ autre version", "absent": "—"}[r["checksum"]]
        return (f"| {r['game']} | {r['slots']} | {'oui' if r['romain'] else ''} | {installed} | {check} | "
                f"{'oui' if r['ut_can_gen_without_yaml'] else ''} | {'✅' if r['logic'] else ''} |")

    counts = collections.Counter(r["checksum"] for r in rows)
    md = [
        "# Jeux de la room (M14)",
        "",
        f"Généré par `scripts/room_inventory.py` (room de {len(status['players'])} slots, {len(rows)} jeux). "
        "« Checksum » compare le datapackage de l'apworld installé ici à celui de la room : la logique d'un jeu n'est "
        "activée que s'il est identique (D12). « UT sans yaml » : Universal Tracker sait régénérer ce monde sans le "
        "yaml du joueur (seule possibilité pour les slots des autres joueurs).",
        "",
        f"Bilan : {counts['identique']} identiques, {counts['différent']} versions différentes, "
        f"{counts['absent']} jeux sans apworld ici.",
        "",
        "| Jeu | Slots | Romain | Apworld ici | Checksum | UT sans yaml | Logique activée |",
        "|---|---|---|---|---|---|---|",
        *map(line, rows),
        "",
    ]
    OUT_MD.write_text("\n".join(md), encoding="utf-8")
    for r in rows:
        if r["romain"] and r["checksum"] != "identique":
            print(f"ATTENTION: {r['game']} (slot de Romain): checksum {r['checksum']}")
    print(f"{OUT_MD.relative_to(ROOT)}: {dict(counts)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
