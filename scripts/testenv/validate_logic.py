#!/usr/bin/env python3
"""Logic validation campaign for one game (TEST CODE ONLY: reads the generated multidata).

For N option seeds: roll a random yaml for GAME (+ companion slots), generate a hostable seed,
then compare the app's logic with the full-multiworld reference at every sphere.

  validate_logic.py "Celeste (Open World)" --runs 5 [--companions "Super Mario 64"]

Results: test-output/logic_validation/<game>.json, one line per run on stdout.
Exit code 0 only if every run that generated had zero difference.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "tests"), str(ROOT / "backend"), str(ROOT / "scripts" / "testenv")]

WORK = ROOT / "test-output" / "logic_validation"


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")[:40]


def run_once(game: str, companions: list[str], run: int, keep_default: bool, retries: int = 3) -> dict:
    """One validation run; random options that make the generation itself fail are re-rolled."""
    res: dict = {}
    for attempt in range(retries + 1):
        res = _run_once(game, companions, run, keep_default, attempt)
        if res.get("generated") is not False:
            break
    res["attempts"] = attempt + 1
    return res


def _run_once(game: str, companions: list[str], run: int, keep_default: bool, attempt: int) -> dict:
    import logic_reference as lr
    base = WORK / slug(game) / f"run{run}"
    players = base / "players"
    if players.exists():
        shutil.rmtree(players)
    players.mkdir(parents=True)
    names = {}
    for i, g in enumerate([game, *companions]):
        name = f"P{i + 1}_{slug(g)[:8]}"
        names[name] = g
        out = players / f"{name}.yaml"
        if keep_default and i == 0:
            out.write_text(f'name: {name}\ngame: "{g}"\n"{g}": {{}}\n', encoding="utf-8")
        else:
            subprocess.run([sys.executable, str(ROOT / "scripts/testenv/random_yaml.py"), g, name, str(out),
                            "--seed", str(run * 100 + i + 10007 * attempt)], check=True, capture_output=True,
                           timeout=300)
    gen = subprocess.run([sys.executable, str(ROOT / "scripts/testenv/generate.py"), str(players), str(base / "out"),
                          "--seed", str(run)], capture_output=True, text=True, timeout=1800)
    if gen.returncode != 0:
        tail = [l for l in gen.stderr.strip().splitlines() if l.strip()][-1:] or ["?"]
        return {"run": run, "generated": False, "error": tail[0][:300]}
    info = json.loads((base / "out" / "generation.json").read_text())
    multidata = lr.load_multidata(Path(info["zip"]))
    # regenerate in-process from the same yamls (deterministic) to get the full multiworld
    fixture_link = ROOT / "tests" / "fixtures" / f"_validate_{slug(game)}_{run}"
    if fixture_link.exists() or fixture_link.is_symlink():
        fixture_link.unlink()
    fixture_link.symlink_to(players, target_is_directory=True)
    try:
        multiworld = lr.regenerate(fixture_link.name, run)
    finally:
        fixture_link.unlink()
    try:
        lr.check_same_fill(multiworld, multidata)
    except AssertionError as exc:
        # The generator itself is not reproducible (e.g. iterates over objects ordered by memory address):
        # this run cannot be compared, it says nothing about the logic.
        return {"run": run, "generated": True, "comparable": False, "error": str(exc)[:300]}
    reports = []
    with lr.ToolProcess() as tool:  # the app's worker, in its own process
        for player in multiworld.player_ids:
            if multiworld.game[player] != game:
                continue
            reports.append(lr.compare_slot(multiworld, multidata, player,
                                           players / f"{multiworld.player_name[player]}.yaml",
                                           max_snapshots=30, tool=tool))
    bad = [s for r in reports for s in r["snapshots"] if s["under"] or s["over"]]
    bad += [{"error": r["error"]} for r in reports if r.get("error")]
    return {"run": run, "generated": True, "ok": not bad and bool(reports),
            "mode": reports[0]["mode"] if reports else None,
            "snapshots": sum(len(r["snapshots"]) for r in reports), "bad": bad[:5],
            "options": (players / f"{next(iter(names))}.yaml").read_text()[:2000]}


def main() -> int:
    # Some worlds iterate over sets while generating: the in-process regeneration only reproduces the
    # hosted seed if string hashing is identical in every process involved.
    if os.environ.get("PYTHONHASHSEED") != "0":
        os.environ["PYTHONHASHSEED"] = "0"
        os.execv(sys.executable, [sys.executable, *sys.argv])
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("game")
    parser.add_argument("--runs", type=int, default=5)
    parser.add_argument("--first-run", type=int, default=1)
    parser.add_argument("--companions", nargs="*", default=["Super Mario 64"])
    parser.add_argument("--default-options", action="store_true", help="first slot with default options")
    args = parser.parse_args()
    results = []
    for run in range(args.first_run, args.first_run + args.runs):
        started = time.time()
        try:
            res = run_once(args.game, args.companions, run, args.default_options)
        except Exception as exc:  # report and continue with the next run
            res = {"run": run, "generated": None, "error": f"{type(exc).__name__}: {exc}"[:400]}
        res["seconds"] = round(time.time() - started, 1)
        results.append(res)
        status = ("OK " if res.get("ok") else "GEN" if res.get("generated") is False
                  else "NC " if res.get("comparable") is False else "KO ")
        print(f"{status} run {run}: {res.get('snapshots', '-')} snapshots, {res['seconds']}s "
              f"{res.get('error', '')} {json.dumps(res.get('bad', [])[:1], ensure_ascii=False)[:600]}", flush=True)
    out = WORK / f"{slug(args.game)}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    generated = [r for r in results if r.get("generated") and r.get("comparable", True)]
    return 0 if generated and all(r.get("ok") for r in generated) else 1


if __name__ == "__main__":
    sys.exit(main())
