#!/usr/bin/env bash
# Prépare le Pi pour la session de nuit de Claude Code (Archipelago Multitracker).
# À lancer depuis la racine du repo. Idempotent : peut être relancé sans risque.
# Ne modifie rien en dehors du repo, n'installe rien sur le système.
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || { echo "✗ Lance ce script depuis le repo cloné."; exit 1; }
cd "$ROOT"
OV="scripts/overnight"

echo "== Vérifications =="
[ -f OVERNIGHT_BRIEF.md ] || { echo "✗ OVERNIGHT_BRIEF.md introuvable à la racine du repo."; exit 1; }

missing=()
for c in git curl gcc make node npm; do command -v "$c" >/dev/null 2>&1 || missing+=("$c"); done
if ! python3 -c 'import sys; sys.exit(0 if (3,11)<=sys.version_info<(3,14) else 1)' 2>/dev/null; then
  echo "✗ Python 3.11 à 3.13 requis (trouvé : $(python3 --version 2>&1))."; exit 1
fi
tmp="$(mktemp -d)"; python3 -m venv "$tmp/v" >/dev/null 2>&1 || missing+=("python3-venv"); rm -rf "$tmp"
python3 -c "import sysconfig,os,sys; sys.exit(0 if os.path.exists(os.path.join(sysconfig.get_paths()['include'],'Python.h')) else 1)" \
  || missing+=("python3-dev")

if [ ${#missing[@]} -gt 0 ]; then
  echo "✗ Manquant : ${missing[*]}"
  echo "  Installe les dépendances système puis relance ce script :"
  echo "  sudo apt install -y git curl build-essential python3-venv python3-dev libffi-dev libssl-dev"
  exit 1
fi
echo "✓ $(python3 --version), node $(node --version), npm $(npm --version)"
echo "  RAM : $(free -h | awk '/Mem:/{print $2" total, "$7" dispo"}')   Disque : $(df -h . | awk 'NR==2{print $4" libres"}')"
if command -v ss >/dev/null && ss -ltnH 2>/dev/null | awk '{print $4}' | grep -qE '[:.]42753$'; then
  echo "⚠ Le port 42753 est déjà utilisé."
else
  echo "✓ Port 42753 libre"
fi
command -v claude >/dev/null && echo "✓ Claude Code $(claude --version 2>/dev/null | head -1)" || echo "⚠ commande 'claude' introuvable"

if git rev-parse HEAD >/dev/null 2>&1; then
  if git push --dry-run origin HEAD >/dev/null 2>&1; then echo "✓ Push GitHub OK"; else echo "⚠ git push échoue : vérifie gh auth / ta clé SSH, sinon Claude ne pourra que commiter en local."; fi
fi

echo
echo "== Notifications push (optionnel, via l'app ntfy) =="
NTFY_TOPIC=""
if [ -f .overnight.env ] && grep -q '^NTFY_TOPIC=.' .overnight.env; then
  # shellcheck disable=SC1091
  . ./.overnight.env; echo "✓ Topic existant : $NTFY_TOPIC (vide .overnight.env pour désactiver)"
else
  suggestion="apmt-$(head -c 6 /dev/urandom | od -An -tx1 | tr -d ' \n')"
  echo "  Entrée = pas de notifications. Pour en recevoir, tape un topic (ex. $suggestion)."
  read -r -p "  Topic ntfy : " NTFY_TOPIC || true
  printf 'NTFY_TOPIC=%s\n' "$NTFY_TOPIC" > .overnight.env
fi
if [ -n "$NTFY_TOPIC" ]; then
  echo "  → Dans l'app ntfy, abonne-toi au topic : $NTFY_TOPIC"
else
  echo "✓ Notifications désactivées (le script notify.sh ne fera rien)"
fi

echo
echo "== Génération des fichiers de session =="
mkdir -p "$OV" .overnight

cat > "$OV/notify.sh" <<'EOF'
#!/usr/bin/env bash
# Usage : bash scripts/overnight/notify.sh "Titre" "Message"
ROOT="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "$0")/../.." && pwd)}"
[ -f "$ROOT/.overnight.env" ] && . "$ROOT/.overnight.env"
[ -n "${NTFY_TOPIC:-}" ] || exit 0
payload="$(python3 -c 'import json,sys; print(json.dumps({"topic":sys.argv[1],"title":sys.argv[2],"message":sys.argv[3],"tags":["robot"]}))' \
  "$NTFY_TOPIC" "${1:-Archipelago Multitracker}" "${2:-(sans message)}")"
curl -fsS -m 10 -H "Content-Type: application/json" -d "$payload" "${NTFY_SERVER:-https://ntfy.sh}" >/dev/null 2>&1 || true
exit 0
EOF

cat > "$OV/stop-hook.sh" <<'EOF'
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
EOF

cat > "$OV/stop-failure-hook.sh" <<'EOF'
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
EOF

cat > "$OV/settings.json" <<'EOF'
{
  "permissions": {
    "allow": [
      "Bash(bash scripts/overnight/notify.sh *)",
      "Bash(scripts/overnight/notify.sh *)"
    ],
    "deny": [
      "Bash(sudo *)", "Bash(su *)", "Bash(doas *)",
      "Bash(apt *)", "Bash(apt-get *)", "Bash(dpkg *)", "Bash(snap *)",
      "Bash(systemctl *)", "Bash(crontab *)", "Bash(chsh *)",
      "Bash(reboot*)", "Bash(shutdown*)", "Bash(poweroff*)", "Bash(halt*)",
      "Bash(rm -rf /)", "Bash(rm -rf /*)", "Bash(rm -rf ~)", "Bash(rm -rf ~/*)", "Bash(rm -rf $HOME*)", "Bash(rm -rf ..*)",
      "Bash(npm install -g *)", "Bash(npm i -g *)", "Bash(npm uninstall -g *)",
      "Bash(pip install --user *)", "Bash(pip3 install --user *)",
      "Bash(pip install --break-system-packages*)", "Bash(pip3 install --break-system-packages*)",
      "Bash(pip uninstall *)", "Bash(pip3 uninstall *)",
      "Bash(git push --force*)", "Bash(git push -f*)",
      "Bash(tailscale up*)", "Bash(tailscale down*)", "Bash(tailscale logout*)", "Bash(tailscale serve reset*)",
      "Edit(~/.bashrc)", "Edit(~/.zshrc)", "Edit(~/.profile)", "Edit(~/.zprofile)", "Edit(~/.oh-my-zsh/**)",
      "Edit(~/.claude/**)", "Edit(~/.ssh/**)", "Edit(~/.gitconfig)"
    ]
  },
  "hooks": {
    "Stop": [
      { "hooks": [ { "type": "command", "command": "bash \"$CLAUDE_PROJECT_DIR/scripts/overnight/stop-hook.sh\"" } ] }
    ],
    "StopFailure": [
      { "hooks": [ { "type": "command", "command": "bash \"$CLAUDE_PROJECT_DIR/scripts/overnight/stop-failure-hook.sh\"" } ] }
    ],
    "Notification": [
      { "matcher": "permission_prompt",
        "hooks": [ { "type": "command", "command": "bash \"$CLAUDE_PROJECT_DIR/scripts/overnight/notify.sh\" \"Claude attend une validation\" \"Une action demande ton accord dans la session de nuit.\"" } ] }
    ]
  },
  "autoMode": {
    "environment": [
      "$defaults",
      "Primary use: building a personal web app (Archipelago multiworld tracker) on the user's own Raspberry Pi dev server",
      "Source control: github.com/Hikari-rom/archipelago-multitracker is the user's own repository; committing and pushing to its main branch is expected",
      "Trusted sources: cloning and downloading public releases from github.com (ArchipelagoMW/Archipelago, FarisTheAncient/Archipelago and the Archipelago apworld repositories listed in OVERNIGHT_BRIEF.md); installing packages from PyPI and npm into the project's own .venv and node_modules",
      "Notifications: ntfy.sh is the user's own push notification service; posting short progress messages through scripts/overnight/notify.sh is expected",
      "Local services: Archipelago test servers on 127.0.0.1 ports 38281-38290 and the app on port 42753 are started by the agent itself for testing",
      "Host containment: the sibling Enigmatik project directory may be read but must never be modified; nothing outside the repository may be modified"
    ]
  }
}
EOF
chmod +x "$OV"/*.sh
rm -f .overnight/continues .overnight/STOP

touch .gitignore
for l in ".overnight/" ".overnight.env" ".run/" ".venv/" "vendor/" "node_modules/" "frontend/dist/" "config/room.yaml" "*.archipelago" "AP_*.zip" "*_Spoiler.txt" "test-output/"; do
  grep -qxF "$l" .gitignore || echo "$l" >> .gitignore
done
echo "✓ scripts/overnight/ généré, .gitignore à jour"

if [ -n "$NTFY_TOPIC" ]; then
  bash "$OV/notify.sh" "Test Archipelago Multitracker" "Si tu lis ça, les notifications de la session de nuit fonctionnent."
  echo "✓ Notification de test envoyée"
fi

cat <<EOF

== Lancement ==
  tmux new -s apmt
  claude --model opus --permission-mode auto --settings scripts/overnight/settings.json \\
    "Lis OVERNIGHT_BRIEF.md en entier et exécute la mission jusqu'au bout, sans attendre de réponse de ma part."

== Reprise (après un rate limit) ==
  rm -f .overnight/continues
  claude --model opus --permission-mode auto --settings scripts/overnight/settings.json \\
    "Reprends la mission : lis OVERNIGHT_BRIEF.md puis PROGRESS.md, BACKLOG.md, DECISIONS.md, et continue."

== Arrêt propre ==
  touch .overnight/STOP   (puis Échap dans la session)

Les hooks et règles ne s'appliquent qu'aux sessions lancées avec --settings scripts/overnight/settings.json.
EOF
