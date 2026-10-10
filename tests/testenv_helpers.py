"""Shared helpers for tests that need a generated multiworld and a local test server (test code only)."""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures"
SEEDS = ROOT / "test-output" / "seeds"
sys.path.insert(0, str(ROOT / "scripts" / "testenv"))
sys.path.insert(0, str(ROOT / "backend"))


def generated_seed(fixture: str, seed: int = 42, spoiler: int = 3) -> Path:
    """Generate (or reuse from cache) the multiworld for tests/fixtures/<fixture>. Returns the AP_*.zip path."""
    players = FIXTURES / fixture
    digest = hashlib.sha256()
    for path in sorted(players.glob("*.yaml")):
        digest.update(path.name.encode() + path.read_bytes())
    digest.update((ROOT / "scripts/testenv/generate.py").read_bytes())
    digest.update((ROOT / "config/apworlds.lock.yaml").read_bytes())
    out = SEEDS / f"{fixture}-{seed}-s{spoiler}-{digest.hexdigest()[:12]}"
    info = out / "generation.json"
    if not info.exists():
        env = {**os.environ, "PYTHONHASHSEED": os.environ.get("PYTHONHASHSEED", "0")}
        proc = subprocess.run([sys.executable, str(ROOT / "scripts/testenv/generate.py"), str(players), str(out),
                               "--seed", str(seed), "--spoiler", str(spoiler)], capture_output=True, text=True,
                              timeout=1800, env=env)
        if proc.returncode != 0:
            raise RuntimeError(f"generation of {fixture} failed:\n{proc.stderr[-4000:]}")
    return Path(json.loads(info.read_text())["zip"])


def start_server(zip_path: Path, port: int, password: str = "test") -> None:
    import pytest
    import serve
    serve.stop(port)
    try:
        serve.start(zip_path, port, password, keep_save=False)
    except SystemExit as exc:  # serve.start reports problems with SystemExit (CLI style)
        pytest.fail(f"could not start the test server: {exc}")


def stop_server(port: int) -> None:
    import serve
    serve.stop(port)
