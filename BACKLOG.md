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
- [x] Projet Vue 3 + Vite + TS, client API + SSE
- [x] Carte par jeu (état, compteurs, badge logique, locations, nouveaux items, hints)
- [x] Tri du tableau de bord, thème clair/sombre, mobile
- [x] Servi par le backend en prod
- [x] Tests vitest + vérification rendu (Playwright) mobile + desktop
- [x] Relecture M4 + commit/push + notif

## M5 — Logique priorité 1
- [x] Moteur de logique (UT headless ou réimplémentation), cache + debounce
- [x] Celeste (Open World) : référence + bout en bout
- [x] Kingdom Hearts 2 : référence + bout en bout
- [x] Jak and Daxter : référence + bout en bout
- [x] The Wind Waker HD : référence + bout en bout
- [x] Relecture M5 + commit/push + notif

## M6 — Déploiement
- [x] Lancement prod sur 0.0.0.0:42753 (script start/stop, PID dans `.run/`)
- [x] Fichier service systemd --user préparé + commandes dans « À faire par Romain »
- [x] README.md en français (installation, config room, lancement, mise à jour d'un apworld)
- [x] Relecture M6 + commit/push + notif

## M7 — Étendre la logique
- [x] Super Mario 64 (sm64ex) — adaptateur area rando, 6/6 seeds
- [x] Super Mario Odyssey
- [x] Ori and the Blind Forest
- [ ] Ori and the Will of the Wisps — 3/4 seeds, surestimation sur des événements de combat (à traiter en dernier)
- [ ] Balatro — adaptateur `_balatro` (adapters_m7.py) : référence OK 5/5 (runs 41–45). Reste : lot bout en bout, `logic: true`, COMPAT
- [x] Slay the Spire
- [x] Kingdom Hearts: Birth by Sleep Final Mix
- [x] Jak 3
- [ ] The Legend of Zelda: Phantom Hourglass — adaptateur `_tloz_ph` (adapters_m7.py) : référence OK 4/4 comparables (runs 41, 42, 44, 45 ; 43 = GEN). Reste : lot bout en bout, `logic: true`, COMPAT
- [x] Pokémon Platinum
- [x] Pokémon Black and White
- [ ] PokéPark Wii: Pikachu's Adventure — pas commencé (les options aléatoires ne génèrent pas : commencer par `--default-options`)
- [x] Ratchet & Clank 2
- [x] Ratchet & Clank 3
- [x] AEMinecraft
- [x] The Binding of Isaac: Repentance
- [x] Mario Kart Wii — adaptateur
- [!] The Legend of Zelda: Ocarina of Time (en dernier) — bloqué : les récompenses de donjon (y compris la Poche de Link) sont des événements sans adresse placés au hasard ; ni le slot_data ni le serveur ne les donnent, donc la logique régénérée diverge dès la sphère 0 (2/2 seeds aux options par défaut, 3/3 aléatoires). Niveau 1 OK, logique désactivée. Voir COMPAT.md. **Mis de côté à la demande de Romain (2026-10-11) : ne pas y retravailler.**
- [x] Relecture M7 + commit/push + notif

## M8 — Bonus
- [x] Découverte des slots d'une room depuis son URL archipelago.gg — page Configuration + port suivi automatiquement
- [x] Support de plusieurs joueurs — champ `owner` par slot, filtre par joueur dans le tableau de bord
- [x] Finitions UX — inventaire de départ, groupes de locations, ordre stable des cartes, reconnexion SSE, thème sans flash
- [x] Robustesse (coupures réseau, room qui redémarre) — reconnexion, changement de port de room, mauvais mot de passe, crash du worker : tests dédiés
- [x] Performance de la régénération sur le Pi — 22 slots : 13 s au démarrage, 0,5 s pour tout recalculer, worker ~400 Mo (scripts/testenv/perf_all22.py)

## M9 — Configuration (demandé par Romain le 2026-10-11)
Prérequis déposés par Romain avant la nuit : ses yamls dans `config/players/romain/`, et le lien de la room + le mot de
passe dans `config/room.real.yaml` (gitignoré ; clés `room_url` et `password`). Si un prérequis manque au moment de
brancher la room, marquer cette tâche `- [!]` et continuer le reste.
Lecture seule absolue vers la vraie room : seule l'app s'y connecte, jamais le bot de test ni les tests pytest.
- [ ] Audit de la page Configuration : parcours complet en captures mobile + desktop, frictions notées dans PROGRESS.md
- [ ] Import des yamls depuis le navigateur : upload d'un ou plusieurs fichiers (yamls multi-documents compris), écriture dans `config/players/` (noms de fichiers sûrs, .yaml/.yml uniquement, taille max, même origine, pas d'écrasement silencieux), tests backend + front
- [ ] Association automatique slot ↔ yaml par le `name` du yaml et le jeu (multi-documents, noms avec `{player}`/`{number}`), choix manuel toujours possible
- [ ] Diagnostic par slot dans la page : jeu sans apworld ou sans logique, yaml absent alors que nécessaire (jeux « UT avec yaml » de COMPAT.md), yaml d'un autre jeu ou d'un autre nom, options `random` non résolues par le `slot_data`
- [ ] Test de connexion avant enregistrement (mot de passe, slots trouvés), sauvegarde de l'ancienne config (`config/room.yaml.bak`) et retour possible à la config de test
- [ ] Brancher la vraie room de Romain via la page Configuration (Playwright ou API) : tous ses slots connectés, logique calculée pour les jeux activés, aucune erreur dans `data/logs/app.log`, RAM et temps de calcul relevés, captures, écarts avec la room de test notés ; arrêter ensuite le serveur de test local
- [ ] README et « À faire par Romain » mis à jour avec la procédure réelle
- [ ] Relecture M9 + commit/push + notif
