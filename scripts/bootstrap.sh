#!/usr/bin/env bash
# Idempotent setup of the dev/prod environment. Touches nothing outside the repository.
#   - clones Archipelago 0.6.7 into vendor/Archipelago
#   - creates .venv and installs AP's requirements (without the GUI / Windows-only ones) + backend deps
#   - downloads the apworlds and Universal Tracker (config/apworlds.yaml -> config/apworlds.lock.yaml)
#   - installs the frontend dependencies and builds it (if frontend/package.json exists)
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
AP_VERSION="0.6.7"
AP_DIR="vendor/Archipelago"
PY="${PYTHON:-python3}"

log() { printf '\033[1m== %s\033[0m\n' "$*"; }

"$PY" -c 'import sys; sys.exit(0 if (3,11) <= sys.version_info < (3,14) else 1)' \
  || { echo "Python 3.11 à 3.13 requis (trouvé : $("$PY" --version 2>&1))"; exit 1; }

log "Archipelago $AP_VERSION"
if [ ! -d "$AP_DIR/.git" ]; then
  mkdir -p vendor
  git -c advice.detachedHead=false clone --quiet --depth 1 --branch "$AP_VERSION" \
    https://github.com/ArchipelagoMW/Archipelago "$AP_DIR"
else
  current="$(git -C "$AP_DIR" describe --tags --exact-match 2>/dev/null || echo '?')"
  [ "$current" = "$AP_VERSION" ] || echo "⚠ $AP_DIR est sur '$current', attendu $AP_VERSION"
fi

log "Environnement Python (.venv)"
[ -x .venv/bin/python ] || "$PY" -m venv .venv
.venv/bin/pip install --quiet --upgrade pip
# AP requirements minus the GUI (kivy, kivymd) and Windows-only (Pymem) packages.
grep -vE '^\s*(kivy|kivymd|Pymem)\b|^\s*#|^\s*$' "$AP_DIR/requirements.txt" > .venv/ap-requirements.txt
.venv/bin/pip install --quiet -r .venv/ap-requirements.txt
# Client-side deps imported at world-import time by some worlds (pure Python on Linux).
.venv/bin/pip install --quiet "Pymem>=1.10.0" "PyMemoryEditor>=2.0.1"
# dolphin-memory-engine does not build on aarch64: backend/ap_stubs/ provides a stub.
.venv/bin/pip install --quiet -r backend/requirements.txt

log "Apworlds"
.venv/bin/python scripts/fetch_apworlds.py

if [ -f frontend/package.json ]; then
  log "Frontend"
  (cd frontend && npm ci --no-audit --no-fund --loglevel=error && npm run build --silent)
fi

log "Terminé"
echo "Vérifier le chargement des apworlds : .venv/bin/python scripts/check_apworlds.py"
