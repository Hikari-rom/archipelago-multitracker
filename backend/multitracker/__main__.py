"""Run the app: python -m multitracker [--host 0.0.0.0] [--port 42753] [--config config/room.yaml]."""
from __future__ import annotations

import argparse
import logging
import os
from pathlib import Path

import uvicorn


def main() -> None:
    parser = argparse.ArgumentParser(prog="multitracker")
    parser.add_argument("--host", default=os.environ.get("MT_HOST", "0.0.0.0"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("MT_PORT", "42753")))
    parser.add_argument("--config", type=Path, default=None)
    parser.add_argument("--db", type=Path, default=None)
    parser.add_argument("--no-logic", action="store_true", help="disable the logic engine")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    from . import config as config_mod
    from .api import create_app
    from .service import Service
    from .store import DEFAULT_DB, Store

    def factory() -> Service:
        cfg = config_mod.load(args.config)
        store = Store(args.db or DEFAULT_DB)
        logic = None
        if not args.no_logic:
            from .logic.engine import default_engine
            logic = default_engine()
        return Service(cfg, store, logic)

    uvicorn.run(create_app(factory), host=args.host, port=args.port, log_level="info", proxy_headers=False)


if __name__ == "__main__":
    main()
