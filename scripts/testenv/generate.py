#!/usr/bin/env python3
"""Generate a TEST multiworld (test code only: the output contains a spoiler).

Usage:
  .venv/bin/python scripts/testenv/generate.py PLAYERS_DIR OUT_DIR [--seed N] [--skip-output]

PLAYERS_DIR holds one yaml per slot. OUT_DIR receives AP_<seed>.zip (multidata + spoiler).

By default the generation is *hostable*: every world's `generate_output` (the step that
patches ROMs / writes game files) is replaced by a no-op, so no ROM is needed, but the
multidata (`.archipelago`) and the spoiler are still written, which `--skip_output` would skip.
`--skip-output` runs Archipelago's own `--skip_output` instead (fill only, nothing written).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from multitracker import apenv  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("players_dir", type=Path)
    parser.add_argument("out_dir", type=Path)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--skip-output", action="store_true", help="use AP's --skip_output (nothing is written)")
    parser.add_argument("--spoiler", type=int, default=3, help="spoiler level (default 3: with playthrough paths)")
    args = parser.parse_args()

    players_dir = args.players_dir.resolve()
    out_dir = args.out_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    ap_dir = apenv.setup()
    os.chdir(ap_dir)

    import Generate
    import Main
    from worlds.AutoWorld import AutoWorldRegister, World

    if not args.skip_output:
        def _no_output(self, output_directory: str) -> None:  # no ROM, no game files
            return None

        for world_type in AutoWorldRegister.world_types.values():
            world_type.generate_output = _no_output
        World.generate_output = _no_output

    argv = ["--player_files_path", str(players_dir), "--outputpath", str(out_dir),
            "--spoiler", str(args.spoiler), "--multi", str(len(list(players_dir.glob("*.yaml"))))]
    if args.seed is not None:
        argv += ["--seed", str(args.seed)]
    if args.skip_output:
        argv.append("--skip_output")

    start = time.perf_counter()
    erargs, seed = Generate.main(Generate.mystery_argparse(argv))
    multiworld = Main.main(erargs, seed)
    elapsed = time.perf_counter() - start
    info = {
        "seed": seed,
        "seed_name": multiworld.seed_name,
        "players": {multiworld.player_name[p]: multiworld.game[p] for p in multiworld.player_ids},
        "seconds": round(elapsed, 1),
        "zip": None if args.skip_output else str(out_dir / f"AP_{multiworld.seed_name}.zip"),
    }
    (out_dir / "generation.json").write_text(json.dumps(info, indent=2), encoding="utf-8")
    print(json.dumps(info))
    return 0


if __name__ == "__main__":
    sys.exit(main())
