#!/usr/bin/env bash
# Start / stop the multitracker in the background (no root needed).
#   scripts/app.sh start|stop|restart|status|logs
# Listens on ${MT_HOST:-0.0.0.0}:${MT_PORT:-42753}. PID in .run/app.pid, log in data/logs/app.log.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
PID_FILE=".run/app.pid"
LOG_DIR="data/logs"
LOG="$LOG_DIR/app.log"
PORT="${MT_PORT:-42753}"
HOST="${MT_HOST:-0.0.0.0}"

is_ours() {  # our app: this repo's venv python running "-m multitracker" (guards against recycled PIDs)
  local pid="$1"
  [ -r "/proc/$pid/cmdline" ] || return 1
  local cmd; cmd="$(tr '\0' ' ' < "/proc/$pid/cmdline")"
  [[ "$cmd" == "$ROOT/.venv/bin/python -m multitracker"* ]]
}

port_busy() {
  ss -ltnH "sport = :$PORT" 2>/dev/null | grep -q .
}

running_pid() {
  [ -f "$PID_FILE" ] || return 1
  local pid; pid="$(cat "$PID_FILE")"
  if is_ours "$pid"; then echo "$pid"; return 0; fi
  rm -f "$PID_FILE"; return 1
}

start() {
  if pid="$(running_pid)"; then echo "déjà lancé (pid $pid)"; return 0; fi
  if port_busy; then
    echo "✗ le port $PORT est déjà utilisé par un autre programme (service systemd multitracker ?)"; exit 1
  fi
  [ -f config/room.yaml ] || { echo "✗ config/room.yaml manquant (copie config/room.example.yaml)"; exit 1; }
  if [ ! -f frontend/dist/index.html ]; then
    echo "Construction du front…"; (cd frontend && npm ci --no-audit --no-fund --loglevel=error && npm run build --silent)
  fi
  mkdir -p .run "$LOG_DIR"
  # keep the log small on the SD card: rotate at start when over 5 MB
  if [ -f "$LOG" ] && [ "$(stat -c %s "$LOG")" -gt 5242880 ]; then mv -f "$LOG" "$LOG.1"; fi
  PYTHONPATH="$ROOT/backend" PYTHONUNBUFFERED=1 nohup "$ROOT/.venv/bin/python" -m multitracker \
    --host "$HOST" --port "$PORT" >> "$LOG" 2>&1 < /dev/null 9>&- &
  echo $! > "$PID_FILE"
  for _ in $(seq 1 60); do
    is_ours "$(cat "$PID_FILE")" || { rm -f "$PID_FILE"; echo "✗ l'app s'est arrêtée, voir $LOG"; tail -20 "$LOG"; exit 1; }
    if curl -fsS "http://127.0.0.1:$PORT/api/health" > /dev/null 2>&1; then
      echo "lancé (pid $(cat "$PID_FILE")) sur http://$HOST:$PORT"; return 0
    fi
    sleep 1
  done
  echo "⚠ pas de réponse sur le port $PORT après 60 s, voir $LOG"; exit 1
}

stop() {
  if pid="$(running_pid)"; then
    kill "$pid"
    for _ in $(seq 1 50); do is_ours "$pid" || break; sleep 0.2; done
    is_ours "$pid" && kill -9 "$pid"
    rm -f "$PID_FILE"; echo "arrêté"
  else
    echo "pas lancé"
  fi
}

mkdir -p .run
exec 9> .run/app.lock
flock -n 9 || { echo "✗ une autre commande scripts/app.sh est en cours"; exit 1; }

case "${1:-status}" in
  start) start ;;
  stop) stop ;;
  restart) stop; start ;;
  status) if pid="$(running_pid)"; then echo "lancé (pid $pid)"; else echo "pas lancé"; exit 3; fi ;;
  logs) tail -n 100 -f "$LOG" ;;
  *) echo "usage: $0 start|stop|restart|status|logs"; exit 2 ;;
esac
