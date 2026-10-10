#!/usr/bin/env bash
# Usage : bash scripts/overnight/notify.sh "Titre" "Message"
ROOT="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "$0")/../.." && pwd)}"
[ -f "$ROOT/.overnight.env" ] && . "$ROOT/.overnight.env"
[ -n "${NTFY_TOPIC:-}" ] || exit 0
payload="$(python3 -c 'import json,sys; print(json.dumps({"topic":sys.argv[1],"title":sys.argv[2],"message":sys.argv[3],"tags":["robot"]}))' \
  "$NTFY_TOPIC" "${1:-Archipelago Multitracker}" "${2:-(sans message)}")"
curl -fsS -m 10 -H "Content-Type: application/json" -d "$payload" "${NTFY_SERVER:-https://ntfy.sh}" >/dev/null 2>&1 || true
exit 0
