#!/usr/bin/env bash
# Update this checkout (the Pi) from origin/main: started by the app (Configuration > Mises à jour) or by hand.
#   scripts/update.sh
# Fast-forward only: stops, changing nothing, on local commits not pushed or another branch than main. Local changes
# (players' yamls) are stashed and put back (git --autostash). Then reinstalls only what changed (Python deps,
# apworlds, npm packages), rebuilds the interface and restarts the app if it runs and its code changed.
# Progress in data/update/status.json (read by the app), output in data/logs/update.log when started by the app.
# MT_UPDATE_SINCE (set by the app): the commit the running app started on. Commits made in this checkout since then
# (by a dev session on the Pi) are then rebuilt and restarted too, even with nothing new on origin/main.
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
STATUS="data/update/status.json"
mkdir -p data/update .run

FROM="$(git rev-parse --short HEAD)"
TO="$FROM"
SINCE="${MT_UPDATE_SINCE:-}"
if [ -n "$SINCE" ] && git cat-file -e "$SINCE^{commit}" 2>/dev/null; then
  SINCE="$(git rev-parse "$SINCE")"
  FROM="$(git rev-parse --short "$SINCE")"
else
  SINCE=""
fi

status() {  # state step [message]
  python3 - "$STATUS" "$1" "$2" "${3:-}" "$FROM" "$TO" <<'EOF'
import json, os, sys, time
path, state, step, message, frm, to = sys.argv[1:]
with open(path + ".tmp", "w", encoding="utf-8") as f:
    json.dump({"mode": "git", "state": state, "step": step, "message": message, "from": frm, "to": to,
               "at": time.time()}, f, ensure_ascii=False)
os.replace(path + ".tmp", path)
EOF
  echo "== $2${3:+ : $3}"
}
fail() { status error "$1" "$2"; exit 1; }

exec 8> .run/update.lock
flock -n 8 || { echo "✗ une mise à jour est déjà en cours"; exit 1; }
echo "== $(date '+%F %T') mise à jour depuis $FROM"

status running "Récupération de main"
git fetch --quiet origin main || fail "Récupération de main" "git fetch a échoué (réseau ?)"
TO="$(git rev-parse --short origin/main)"
branch="$(git rev-parse --abbrev-ref HEAD)"
[ "$branch" = main ] || fail "Vérification" "le dépôt est sur la branche $branch, pas main"
ahead="$(git rev-list --count origin/main..HEAD)"
[ "$ahead" = 0 ] || fail "Vérification" "$ahead commit(s) local(aux) pas encore poussé(s) : mise à jour à faire à la main"
if [ "$FROM" = "$TO" ]; then status done "Terminé" "déjà à jour"; exit 0; fi

BASE="${SINCE:-$(git rev-parse HEAD)}"  # what the running app has: the changes to apply are BASE..main
note=""
if [ "$(git rev-parse HEAD)" != "$(git rev-parse origin/main)" ]; then
  status running "Mise à jour du code"
  out="$(git merge --ff-only --autostash origin/main 2>&1)" || { echo "$out"; fail "Mise à jour du code" "git merge a échoué, rien n'a changé"; }
  echo "$out"
  if grep -q "stash" <<<"$out" && grep -qi "conflict" <<<"$out"; then
    note="tes modifications locales n'ont pas pu être remises : elles sont dans git stash"
  fi
fi
changed="$(git diff --name-only "$BASE" HEAD)"
has() { grep -qE "$1" <<<"$changed"; }

if has '^(scripts/bootstrap\.sh|backend/requirements\.txt)$'; then
  status running "Dépendances Python et apworlds"
  bash scripts/bootstrap.sh || fail "Dépendances" "scripts/bootstrap.sh a échoué, voir data/logs/update.log"
else
  if has '^config/apworlds(\.lock)?\.yaml$'; then
    status running "Apworlds"
    .venv/bin/python scripts/fetch_apworlds.py || fail "Apworlds" "scripts/fetch_apworlds.py a échoué"
  fi
  if has '^frontend/package(-lock)?\.json$'; then
    status running "Paquets npm"
    (cd frontend && npm ci --no-audit --no-fund --loglevel=error) || fail "Paquets npm" "npm ci a échoué"
  fi
  if [ -f frontend/package.json ] && { has '^frontend/' || [ ! -f frontend/dist/index.html ]; }; then
    status running "Construction de l'interface"
    (cd frontend && npm run build --silent) || fail "Construction de l'interface" "npm run build a échoué"
  fi
fi

# The interface is served from frontend/dist as it is built: a restart is only needed for the backend.
if has '^(backend/|config/|scripts/app\.sh|scripts/bootstrap\.sh)' && scripts/app.sh status > /dev/null 2>&1; then
  status restarting "Redémarrage"
  scripts/app.sh restart 8>&- || fail "Redémarrage" "l'app n'a pas redémarré, voir data/logs/app.log"
fi
status done "Terminé" "$note"
