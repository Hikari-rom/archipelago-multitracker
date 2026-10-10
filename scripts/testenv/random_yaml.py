#!/usr/bin/env python3
"""Write a TEST player yaml with randomly rolled, *concrete* option values (test code only).

  random_yaml.py GAME NAME OUT.yaml [--seed N]

Every Toggle / Choice / Range option of the world gets a random valid value (written explicitly,
never as "random", so the regeneration from the yaml is deterministic). Complex options
(sets, lists, dicts, plando...) keep their defaults. Options listed in AVOID keep their default
because they make test generation fail or explode in size.
"""
from __future__ import annotations

import argparse
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from multitracker import apenv  # noqa: E402

COMMON = {"progression_balancing", "accessibility", "local_items", "non_local_items", "start_inventory",
          "start_inventory_from_pool", "start_hints", "start_location_hints", "exclude_locations",
          "priority_locations", "item_links", "plando_items", "death_link"}
AVOID: dict[str, set[str]] = {}


def roll(game: str, rng: random.Random) -> dict:
    apenv.setup()
    import Options
    from worlds.AutoWorld import AutoWorldRegister
    world = AutoWorldRegister.world_types[game]
    values = {}
    for name, option in world.options_dataclass.type_hints.items():
        if name in COMMON or name in AVOID.get(game, set()) or getattr(option, "visibility", 1) == 0:
            continue
        try:
            if issubclass(option, Options.Toggle):
                values[name] = rng.choice([True, False])
            elif issubclass(option, Options.Choice):
                choices = [k for k in option.options if not k.startswith("random")]
                values[name] = rng.choice(choices)
            elif issubclass(option, Options.Range):
                values[name] = rng.randint(option.range_start, option.range_end)
        except TypeError:
            continue
    return values


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("game")
    parser.add_argument("name")
    parser.add_argument("out", type=Path)
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()
    import yaml
    options = roll(args.game, random.Random(args.seed))
    doc = {"name": args.name, "game": args.game, args.game: {"progression_balancing": 50, **options}}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(yaml.safe_dump(doc, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
