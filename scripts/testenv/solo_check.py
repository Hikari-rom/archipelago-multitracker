#!/usr/bin/env python3
"""Compat study: generate each game alone from its default options template, headless.

Uses test-output/templates (see scripts/testenv/make_templates.py). Each game runs
`scripts/testenv/generate.py --skip-output` in its own process, 2 at a time.
Results go to test-output/solo_check.json.
"""
from __future__ import annotations

import concurrent.futures
import json
import re
import subprocess
import sys
import time
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
TEMPLATES = ROOT / "test-output" / "templates"
WORK = ROOT / "test-output" / "solo"
OUT = ROOT / "test-output" / "solo_check.json"


def template_for(game: str) -> Path | None:
    for path in TEMPLATES.glob("*.yaml"):
        text = path.read_text(encoding="utf-8-sig")
        if re.search(rf"^game:\s*['\"]?{re.escape(game)}['\"]?\s*$", text, re.M):
            return path
    return None


def run(key: str, game: str) -> dict:
    template = template_for(game)
    if template is None:
        return {"key": key, "game": game, "ok": False, "error": "no template"}
    players = WORK / key / "players"
    players.mkdir(parents=True, exist_ok=True)
    text = template.read_text(encoding="utf-8-sig")
    text = re.sub(r"^name:.*$", f"name: Solo{key[:10]}", text, count=1, flags=re.M)
    (players / "player.yaml").write_text(text, encoding="utf-8")
    start = time.perf_counter()
    try:
        proc = subprocess.run([sys.executable, str(ROOT / "scripts/testenv/generate.py"), str(players),
                               str(WORK / key / "out"), "--seed", "1", "--skip-output"],
                              capture_output=True, text=True, timeout=900)
        ok = proc.returncode == 0
        err = "" if ok else (proc.stderr.strip().splitlines() or ["?"])[-1][:300]
    except subprocess.TimeoutExpired:
        ok, err = False, "timeout (900 s)"
    return {"key": key, "game": game, "ok": ok, "error": err, "seconds": round(time.perf_counter() - start, 1)}


def main() -> int:
    config = yaml.safe_load((ROOT / "config" / "apworlds.yaml").read_text(encoding="utf-8"))
    entries = config["apworlds"]
    only = set(sys.argv[1:])
    jobs = {k: v["game"] for k, v in entries.items() if not only or k in only}
    results = json.loads(OUT.read_text()) if OUT.exists() else {}
    with concurrent.futures.ThreadPoolExecutor(2) as pool:
        for res in pool.map(lambda kv: run(*kv), jobs.items()):
            results[res["key"]] = res
            print(f"{'OK' if res['ok'] else 'KO'} {res['key']:20} {res.get('seconds', '')}s {res['error']}", flush=True)
    OUT.write_text(json.dumps(results, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
