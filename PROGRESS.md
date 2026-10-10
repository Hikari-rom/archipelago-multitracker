# Progression

## État actuel (5 lignes)
1. M0 à M3 faits et relus ; M4 (front), M5 (logique priorité 1) et M6 (déploiement) faits, relectures en cours.
2. L'app tourne sur le Pi : `scripts/app.sh status` → http://<ip-du-pi>:42753, branchée sur le multiworld de **test** local.
3. Logique validée (référence à chaque sphère + bout en bout + seeds aux options aléatoires) : Celeste, KH2, Jak, TWW HD.
4. Tests : `.venv/bin/python -m pytest -q` (backend) et `cd frontend && npm test`.
5. Pour la vraie room : remplir `config/room.yaml` (voir README) puis `scripts/app.sh restart`.

## Journal

### M0 — Prise en main
- Pi 5, 8 Go RAM, 4 cœurs, ~96 Go libres, Python 3.13.5, Node 24.18. Port 42753 libre.
- Tailscale **absent** du Pi. Enigmatik : docker compose (back) / `next dev -H 0.0.0.0` (front). Voir DECISIONS D1.

### M1 — Archipelago headless
- `scripts/bootstrap.sh` (idempotent), `config/apworlds.yaml` + `scripts/fetch_apworlds.py` (lock avec sha256).
- Les 22 apworlds + Universal Tracker v0.3.0 se chargent et génèrent en headless (`scripts/check_apworlds.py`,
  `scripts/testenv/solo_check.py`). Stub `dolphin_memory_engine` (ne compile pas sur ARM). Voir `docs/COMPAT.md`.

### M2 — Environnement de test
- `scripts/testenv/generate.py` : seed hébergeable **sans ROM** (sortie des jeux désactivée, multidata conservé, D4).
- `scripts/testenv/serve.py` : MultiServer sur 127.0.0.1:38281-38290, PID dans `.run/`.
- `scripts/testenv/bot.py` : client de jeu qui coche des locations (refuse tout serveur non local).
- Vérifier : `.venv/bin/python -m pytest -q tests/test_testenv.py`.

### M3 — Backend niveau 1
- Une connexion tracker (tags `Tracker`, `NoText`) par slot, lecture seule garantie par liste blanche de commandes,
  reconnexion avec backoff, datapackage en cache SQLite, items, checks, hints (data storage + SetNotify), but,
  « dernière visite » en SQLite, API REST + SSE (`docs/API.md`).
- Vérifier : `.venv/bin/python -m pytest -q tests/test_backend_level1.py` (7 tests contre le serveur local).

### M4 — Front Vue
- Vue 3 + Vite + TS, sans lib UI. Cartes triées, badge de logique, locations en logique (hintées en tête),
  nouveaux items + « Marquer comme vu », hints dans les deux sens, thème clair/sombre/auto, mobile, SSE.
- Vérifier : `cd frontend && npm test && npm run build` ; captures : `cd frontend && node scripts/screenshot.mjs`
  (→ `test-output/screenshots/live/`).

### M5 — Logique priorité 1
- Universal Tracker piloté en headless dans un process dédié (`backend/multitracker/logic/`). Régénération depuis le
  yaml (ou `slot_data` seul si le monde le permet), puis sweep maison avec la classification exacte des items
  envoyée par le serveur (D6). Adaptateurs par jeu (D7) : TWW HD rejoue les entrées du `slot_data` et déduit les
  donjons requis de la liste des locations.
- Validation : `tests/test_logic_reference.py` (comparaison à chaque sphère avec le multiworld complet),
  `tests/test_logic_e2e.py` (le bot ne coche que ce que l'API annonce en logique jusqu'au but de tous les slots),
  campagnes aux options aléatoires : `scripts/testenv/campaign.sh 5 "Celeste (Open World)" ...`
  (résultats dans `test-output/logs/campaign.summary`).

### M6 — Déploiement
- `scripts/app.sh start|stop|restart|status|logs` (0.0.0.0:42753, PID dans `.run/app.pid`, logs `data/logs/`).
- Unité systemd utilisateur prête : `deploy/multitracker.service` (installation ci-dessous, pas de root sauf linger).
- `README.md` en français.

## À faire par Romain
- **Brancher la vraie room** : éditer `config/room.yaml` (actuellement le multiworld de test local) avec
  `server`, `password`, les 22 slots et tes yamls dans `config/players/`, puis `scripts/app.sh restart`.
- **Démarrage automatique** (optionnel) :
  `mkdir -p ~/.config/systemd/user && cp deploy/multitracker.service ~/.config/systemd/user/ && systemctl --user daemon-reload && systemctl --user enable --now multitracker`
  puis `sudo loginctl enable-linger romain`. Penser à `scripts/app.sh stop` avant, pour libérer le port.
- **Tailscale** n'est pas installé sur le Pi. Pour accéder à l'app depuis le téléphone hors du LAN :
  `curl -fsSL https://tailscale.com/install.sh | sh && sudo tailscale up`. L'app écoute sur `0.0.0.0:42753`,
  donc `http://<ip-tailscale-du-pi>:42753` fonctionnera sans autre réglage.
- Le serveur de test local (port 38281) tourne pour la démo : `.venv/bin/python scripts/testenv/serve.py stop` pour l'arrêter.

## Prochaines étapes
- Finir les relectures M4/M5/M6, puis M7 : étendre la logique jeu par jeu (SM64 d'abord, OoT en dernier).
