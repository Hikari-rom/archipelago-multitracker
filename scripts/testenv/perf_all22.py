#!/usr/bin/env python3
"""Performance on the Pi: 22 slots (tests/fixtures/all22 seed), logic engine as configured in
config/apworlds.yaml. Prints per-slot logic time and the worker's memory. Test code only.

  .venv/bin/python scripts/testenv/perf_all22.py [--port 38283]
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "tests"), str(ROOT / "backend"), str(ROOT / "scripts" / "testenv")]


def rss_mb(pid: int) -> float:
    for line in Path(f"/proc/{pid}/status").read_text().splitlines():
        if line.startswith("VmRSS:"):
            return int(line.split()[1]) / 1024
    return 0.0


async def main(port: int) -> int:
    import yaml
    from testenv_helpers import FIXTURES, generated_seed, start_server, stop_server
    from multitracker import config
    from multitracker.logic.engine import UTLogicEngine
    from multitracker.service import Service
    from multitracker.store import Store

    zip_path = generated_seed("all22", 7, spoiler=1)
    slots = []
    for path in sorted((FIXTURES / "all22").glob("*.yaml")):
        doc = yaml.safe_load(path.read_text())
        slots.append({"name": doc["name"], "game": doc["game"], "yaml": str(path)})
    out = ROOT / "test-output" / "perf"
    out.mkdir(parents=True, exist_ok=True)
    room = out / "room.yaml"
    room.write_text(json.dumps({"server": f"ws://127.0.0.1:{port}", "password": "test", "slots": slots}))
    start_server(zip_path, port)
    engine = UTLogicEngine()
    service = Service(config.load(room), Store(out / "db.sqlite3"), engine, logic_debounce=0.2)
    started = time.perf_counter()
    try:
        await service.start()
        while True:
            states = {n: r.state for n, r in service.logic.items()}
            if service.trackers and all(s != "pending" for s in states.values()) and \
                    all(service.logic_settled(n) for n in service.trackers):
                break
            if time.perf_counter() - started > 1800:
                print("timeout", states)
                break
            await asyncio.sleep(0.5)
        total = time.perf_counter() - started
        rows = sorted(((n, r.state, r.seconds, len(r.in_logic)) for n, r in service.logic.items()),
                      key=lambda row: -(row[2] or 0))
        for name, state, seconds, count in rows:
            print(f"{name:20} {state:12} {seconds or 0:7.2f}s {count:5} en logique")
        mem = rss_mb(engine._proc.pid) if engine._proc else 0
        print(f"total {total:.1f}s until every slot computed; logic worker RSS {mem:.0f} MB")
        # incremental update cost: recompute everything once more (worlds cached)
        t = time.perf_counter()
        for name in service.trackers:
            service._schedule_logic(name)
        await asyncio.sleep(0.5)
        while not all(service.logic_settled(n) for n in service.trackers):
            await asyncio.sleep(0.2)
        print(f"recompute of all slots with cached worlds: {time.perf_counter() - t:.1f}s")
        (out / "perf.json").write_text(json.dumps({"total": total, "worker_rss_mb": mem, "rows": rows}, indent=1))
    finally:
        await service.stop()
        stop_server(port)
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=38283)
    sys.exit(asyncio.run(main(parser.parse_args().port)))
