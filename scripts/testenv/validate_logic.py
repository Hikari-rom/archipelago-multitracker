#!/usr/bin/env python3
"""Logic validation campaign for one game (TEST CODE ONLY: reads the generated multidata).

For N option seeds: roll a random yaml for GAME (+ companion slots), generate a hostable seed,
then compare the app's logic with the full-multiworld reference at every sphere.

  validate_logic.py "Celeste (Open World)" --runs 5 [--companions "Super Mario 64"]
  validate_logic.py "Balatro" --runs 3 --yaml config/players/romain/romain_balatro.yaml   (real player options)
  validate_logic.py "Hollow Knight" --runs 3 --no-yaml   (logic from slot_data only: another player's slot)
  validate_logic.py "Celeste (Open World)" --runs 3 --tool-yaml old.yaml   (the tool gets a stale yaml)
  validate_logic.py "Factorio" --runs 3 --lower-bound   (rules known to be late: only "over" is a difference)

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
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "tests"), str(ROOT / "backend"), str(ROOT / "scripts" / "testenv")]

WORK = ROOT / "test-output" / "logic_validation"


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")[:40]


def run_once(game: str, companions: list[str], run: int, keep_default: bool, retries: int = 3,
             player_yaml: Path | None = None, tool_yaml: bool | Path = True, lower_bound: bool = False) -> dict:
    """One validation run; random options that make the generation itself fail are re-rolled."""
    res: dict = {}
    for attempt in range(retries + 1):
        res = _run_once(game, companions, run, keep_default, attempt, player_yaml, tool_yaml, lower_bound)
        if res.get("generated") is not False:
            break
    res["attempts"] = attempt + 1
    return res


def _run_once(game: str, companions: list[str], run: int, keep_default: bool, attempt: int,
              player_yaml: Path | None = None, tool_yaml: bool | Path = True, lower_bound: bool = False) -> dict:
    """tool_yaml: True = the tool gets the slot's own yaml, False = none, a Path = that yaml instead (another
    yaml than the one the seed was generated with, e.g. the player's yaml of a previous room).
    lower_bound: the tool may miss locations in logic ("under", counted), never add one ("over")."""
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
        if player_yaml and i == 0:
            import yaml
            doc = next(d for d in yaml.safe_load_all(player_yaml.read_text(encoding="utf-8-sig")) if d)
            if doc.get("game") != g:
                raise SystemExit(f"{player_yaml}: game {doc.get('game')!r} is not {g!r}")
            doc["name"] = name
            out.write_text(yaml.safe_dump(doc, allow_unicode=True, sort_keys=False), encoding="utf-8")
        elif keep_default and i == 0:
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
                                           tool_yaml if isinstance(tool_yaml, Path) else
                                           players / f"{multiworld.player_name[player]}.yaml" if tool_yaml else None,
                                           max_snapshots=30, tool=tool))
    bad = [s for r in reports for s in r["snapshots"] if s["over"] or (s["under"] and not lower_bound)]
    bad += [{"error": r["error"]} for r in reports if r.get("error")]
    return {"run": run, "generated": True, "ok": not bad and bool(reports),
            "mode": reports[0]["mode"] if reports else None,
            "snapshots": sum(len(r["snapshots"]) for r in reports), "bad": bad,
            "late": [(s["sphere"], s["tool"], s["reference"]) for r in reports for s in r["snapshots"] if s["under"]],
            "found": [sum(s[k] for r in reports for s in r["snapshots"]) for k in ("tool", "reference")],
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
    parser.add_argument("--yaml", type=Path, help="first slot from this player yaml (name replaced)")
    parser.add_argument("--no-yaml", action="store_true",
                        help="the tool gets no yaml (slot_data only), like for another player's slot")
    parser.add_argument("--tool-yaml", type=Path,
                        help="the tool gets this yaml instead of the slot's own one (stale yaml of another room)")
    parser.add_argument("--lower-bound", action="store_true",
                        help="only a location wrongly in logic is a difference; late ones are counted")
    args = parser.parse_args()
    if args.yaml:
        args.yaml = args.yaml.resolve()  # the runs change the working directory
    if args.tool_yaml:
        args.tool_yaml = args.tool_yaml.resolve()
    results = []
    for run in range(args.first_run, args.first_run + args.runs):
        started = time.time()
        try:
            res = run_once(args.game, args.companions, run, args.default_options, player_yaml=args.yaml,
                           tool_yaml=args.tool_yaml or not args.no_yaml, lower_bound=args.lower_bound)
        except Exception as exc:  # report and continue with the next run
            traceback.print_exc()
            res = {"run": run, "generated": None, "error": f"{type(exc).__name__}: {exc}"[:400]}
        res["seconds"] = round(time.time() - started, 1)
        results.append(res)
        status = ("OK " if res.get("ok") else "GEN" if res.get("generated") is False
                  else "NC " if res.get("comparable") is False else "KO ")
        print(f"{status} run {run}: {res.get('snapshots', '-')} snapshots, {res['seconds']}s "
              f"{res.get('error', '')} {json.dumps(res.get('bad', [])[:1], ensure_ascii=False)[:600]}"
              + (f" in logic, tool/reference over all snapshots: {res.get('found')}; late (sphere, tool, reference): "
                 f"{res.get('late')}" if args.lower_bound else ""), flush=True)
    out = WORK / f"{slug(args.game)}{'_yaml' if args.yaml else ''}{'_noyaml' if args.no_yaml else ''}{'_toolyaml' if args.tool_yaml else ''}{'_lower' if args.lower_bound else ''}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    generated = [r for r in results if r.get("generated") and r.get("comparable", True)]
    return 0 if generated and all(r.get("ok") for r in generated) else 1


if __name__ == "__main__":
    sys.exit(main())
