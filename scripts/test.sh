#!/usr/bin/env bash
# Backend test suite with a fixed hash seed (reproducible generation). Extra args go to pytest.
cd "$(dirname "$0")/.." && PYTHONHASHSEED=0 exec .venv/bin/python -m pytest -p no:logging "$@"
