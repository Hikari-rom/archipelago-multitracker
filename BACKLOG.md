# Backlog

Légende : `- [ ]` ouverte · `- [x]` faite · `- [!]` bloquée (avec la raison)

## M0 — Prise en main
- [x] Inspecter le Pi (versions, RAM, disque, port 42753, exposition d'Enigmatik)
- [x] Créer BACKLOG.md, PROGRESS.md, DECISIONS.md, .gitignore, squelette
- [x] Commit + push M0

## M1 — Archipelago headless sur le Pi
- [x] `scripts/bootstrap.sh` idempotent : clone AP 0.6.7, venv, deps sans GUI
- [x] Choisir la release Universal Tracker compatible 0.6.7, vérifier sa licence
- [x] `config/apworlds.yaml` (22 jeux) + `scripts/fetch_apworlds.py` + `apworlds.lock.yaml`
- [x] Étude de compatibilité : chaque apworld se charge sur 0.6.7 (script `scripts/check_apworlds.py`)
- [x] Première version de `docs/COMPAT.md`
- [x] Relecture M1 + commit/push + notif

## M2 — Environnement de test
- [x] Yamls de test pour Celeste, KH2, Jak and Daxter, TWW HD (depuis les templates)
- [x] `scripts/testenv/generate.py` : multiworld 4-6 slots, `--skip_output`, spoiler
- [x] `scripts/testenv/serve.py` : MultiServer sur 127.0.0.1:38281 avec mot de passe, PID dans `.run/`
- [x] `scripts/testenv/bot.py` : client de jeu qui envoie des checks
- [x] Relecture M2 + commit/push + notif

## M3 — Backend niveau 1
- [x] Squelette FastAPI + config (room.yaml) + SQLite
- [x] Client AP tracker (wss puis ws, tag Tracker, reconnexion auto, lecture seule)
- [x] Datapackage (cache), items reçus, checks, hints (data storage + SetNotify), but atteint
- [x] « Dernière visite » / nouveaux items + « Marquer comme vu »
- [x] API REST + SSE
- [x] Tests d'intégration contre le serveur local (bot → API)
- [x] Relecture M3 + commit/push + notif

## M4 — Front Vue
- [ ] Projet Vue 3 + Vite + TS, client API + SSE
- [ ] Carte par jeu (état, compteurs, badge logique, locations, nouveaux items, hints)
- [ ] Tri du tableau de bord, thème clair/sombre, mobile
- [ ] Servi par le backend en prod
- [ ] Tests vitest + vérification rendu (Playwright) mobile + desktop
- [ ] Relecture M4 + commit/push + notif

## M5 — Logique priorité 1
- [ ] Moteur de logique (UT headless ou réimplémentation), cache + debounce
- [ ] Celeste (Open World) : référence + bout en bout
- [ ] Kingdom Hearts 2 : référence + bout en bout
- [ ] Jak and Daxter : référence + bout en bout
- [ ] The Wind Waker HD : référence + bout en bout
- [ ] Relecture M5 + commit/push + notif

## M6 — Déploiement
- [ ] Lancement prod sur 0.0.0.0:42753 (script start/stop, PID dans `.run/`)
- [ ] Fichier service systemd --user préparé + commandes dans « À faire par Romain »
- [ ] README.md en français (installation, config room, lancement, mise à jour d'un apworld)
- [ ] Relecture M6 + commit/push + notif

## M7 — Étendre la logique
- [ ] Super Mario 64 (sm64ex)
- [ ] Super Mario Odyssey
- [ ] Ori and the Blind Forest
- [ ] Ori and the Will of the Wisps
- [ ] Balatro
- [ ] Slay the Spire
- [ ] Kingdom Hearts: Birth by Sleep Final Mix
- [ ] Jak 3
- [ ] The Legend of Zelda: Phantom Hourglass
- [ ] Pokémon Platinum
- [ ] Pokémon Black and White
- [ ] PokéPark Wii: Pikachu's Adventure
- [ ] Ratchet & Clank 2
- [ ] Ratchet & Clank 3
- [ ] AEMinecraft
- [ ] The Binding of Isaac: Repentance
- [ ] Mario Kart Wii
- [ ] The Legend of Zelda: Ocarina of Time (en dernier)
- [ ] Relecture M7 + commit/push + notif

## M8 — Bonus
- [ ] Découverte des slots d'une room depuis son URL archipelago.gg
- [ ] Support de plusieurs joueurs
- [ ] Finitions UX
- [ ] Robustesse (coupures réseau, room qui redémarre)
- [ ] Performance de la régénération sur le Pi
