#!/usr/bin/env bash
# Notifie quand la session s'interrompt sur une erreur d'API (rate limit, surcharge…).
ROOT="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "$0")/../.." && pwd)}"
cause="$(python3 -c '
import json, sys
try: d = json.load(sys.stdin)
except Exception: d = {}
for k in ("error_type", "error", "reason", "matcher"):
    v = d.get(k)
    if isinstance(v, str) and v:
        print(v); break
else:
    print("inconnue")
' 2>/dev/null)"
bash "$ROOT/scripts/overnight/notify.sh" "Session de nuit interrompue" "Cause : ${cause:-inconnue}. L'état est dans PROGRESS.md, relance avec la commande de reprise."
exit 0
