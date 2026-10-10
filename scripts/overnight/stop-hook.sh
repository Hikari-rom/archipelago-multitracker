#!/usr/bin/env bash
# Empêche Claude de s'arrêter tant que BACKLOG.md contient des tâches "- [ ]".
ROOT="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "$0")/../.." && pwd)}"
STATE="$ROOT/.overnight"; mkdir -p "$STATE"
cat >/dev/null
MAX=40
notify() { bash "$ROOT/scripts/overnight/notify.sh" "$@"; }
count_tasks() { grep -cE "^[[:space:]]*[-*] \\[$1\\]" "$ROOT/BACKLOG.md" 2>/dev/null || true; }

if [ -f "$STATE/STOP" ]; then notify "Session de nuit arrêtée" "Fichier .overnight/STOP détecté."; exit 0; fi
open="$(count_tasks ' ')"; open="${open:-0}"
n="$(cat "$STATE/continues" 2>/dev/null || echo 0)"
if [ "$open" -gt 0 ] && [ "$n" -lt "$MAX" ]; then
  echo $((n + 1)) > "$STATE/continues"
  echo "Il reste $open tâche(s) ouverte(s) dans BACKLOG.md : ne t'arrête pas. Mets PROGRESS.md à jour si besoin puis attaque la prochaine tâche ouverte. Personne ne répondra avant demain : décide toi-même et note-le dans DECISIONS.md. Si une tâche est réellement bloquée, marque-la '- [!]' avec la raison." >&2
  exit 2
fi
done_="$(count_tasks x)"; blocked="$(count_tasks '!')"
notify "Session de nuit terminée" "Faites : ${done_:-0} · bloquées : ${blocked:-0} · ouvertes : $open. Détails dans PROGRESS.md."
exit 0
