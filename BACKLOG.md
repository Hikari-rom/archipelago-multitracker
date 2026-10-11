# Backlog

Légende : `- [ ]` ouverte · `- [x]` faite · `- [!]` bloquée (avec la raison) · `- [>]` déplacée

Les jalons ouverts sont dans l'ordre où les traiter (M10 → M14).

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
- [>] Ori and the Will of the Wisps — déplacé en M14
- [x] Balatro — adaptateur `_balatro` : 5/5 seeds aléatoires + 5/5 avec le yaml de Romain + e2e (lot `m7c`), logique activée
- [x] Slay the Spire
- [x] Kingdom Hearts: Birth by Sleep Final Mix
- [x] Jak 3
- [x] The Legend of Zelda: Phantom Hourglass — adaptateur `_tloz_ph` : 4/4 aléatoires comparables + 5/5 avec le yaml de Romain + e2e (lot `m7c`), logique activée
- [x] Pokémon Platinum
- [x] Pokémon Black and White
- [>] PokéPark Wii: Pikachu's Adventure — déplacé en M14
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

## M9 — Configuration : backend (demandé par Romain le 2026-10-11)
Lecture seule absolue vers la vraie room : seule l'app s'y connecte, jamais le bot de test ni les tests pytest.
- [x] Audit de la page Configuration (captures `test-output/screenshots/audit-m9/`, frictions dans PROGRESS.md). Bug corrigé : la page plantait (page blanche) quand la config n'avait pas de `room_url`
- [x] Yamls : liste récursive de `config/players/` avec les joueurs (`name`, `game`) de chaque document ; upload `POST /api/yamls` (noms sûrs, .yaml/.yml, 512 Ko max, même origine, 409 au lieu d'écraser) — `backend/multitracker/players.py`
- [x] Catalogue des jeux pour le diagnostic : `logic` et `needs_yaml` par jeu dans `config/apworlds.yaml`, exposés par `GET /api/config`
- [x] Test de connexion `POST /api/config/test` (connexion unique en lecture seule, `probe()` dans `ap/tracker.py`), sauvegarde `room.yaml.bak` à chaque enregistrement et `POST /api/config/restore` (échange, donc annulable)
- [x] Option « Réveiller la room » **désactivée par défaut** (`wake_room`) : sans elle l'app ne charge plus jamais la page de la room, détecte la room endormie (`last_activity` + `timeout` de `/api/room_status`), affiche « room endormie » et se reconnecte quand quelqu'un l'a réveillée ; `POST /api/room/wake` pour un réveil ponctuel. Tests `tests/test_config_m9.py`

## M10 — Design avec shadcn-vue (demandé par Romain le 2026-10-11)
Avant de refaire la page Configuration, pour ne pas la coder deux fois. Garder : interface en français, clair/sombre/auto
sans flash, mobile d'abord (390 px), accessibilité (labels, focus, aria), perf sur le Pi (bundle raisonnable).
- [x] Mettre en place Tailwind CSS + shadcn-vue dans `frontend/` (dépendances locales uniquement, versions figées, composants copiés dans `src/components/ui/`, thème via variables CSS reliées au thème clair/sombre existant) ; noter le choix dans DECISIONS.md
- [x] Migrer le tableau de bord : cartes (Card), badges (Badge), boutons (Button), sections repliables (Collapsible/Accordion), barre de progression (Progress), filtres par joueur (Toggle group), bandeaux (Alert) ; tests vitest adaptés, captures avant/après mobile + desktop, clair + sombre
- [ ] Relecture M10 + commit/push + notif

## M11 — Configuration : page et vraie room (demandé par Romain le 2026-10-11)
Prérequis prêts : yamls de Romain dans `config/players/romain/`, lien + mot de passe dans `config/room.real.yaml` (gitignoré).
Vérifié le 2026-10-11 : les 22 slots existent dans la room avec le bon jeu. La room compte **142 slots** (120 d'autres
joueurs) et dort souvent (timeout 2 h) : surveiller la taille du datapackage, la RAM et le nombre de hints.
- [x] Parcours « lien de room » en composants shadcn-vue : coller le lien → infos de la room (port, nombre de slots et de jeux, endormie ou non + bouton « Réveiller la room ») → mot de passe → « Tester la connexion » → sélection des slots ; lien direct `#config?room=<lien>` (et écoute de `hashchange`) qui pré-remplit la page et lance la découverte
- [x] Sélection dans une room de 142 slots : recherche qui filtre la liste, filtre par jeu, « cochés seulement », cocher/décocher les slots affichés, présélection des slots qui ont un yaml
- [x] Yamls dans la page : import de un ou plusieurs fichiers depuis le navigateur (confirmation avant de remplacer), association automatique slot ↔ yaml par `name` (avec `{player}`/`{number}`) et jeu, choix manuel toujours possible
- [x] Diagnostic par slot : jeu sans apworld (niveau 1 seulement), logique pas encore validée, yaml nécessaire mais absent, yaml d'un autre jeu ou d'un autre nom, yaml illisible ; résumé avant d'enregistrer ; case « Réveiller automatiquement la room » ; bouton « Restaurer la configuration précédente » ; bandeau « Room endormie » + « Réveiller maintenant » sur le tableau de bord
- [x] Options `random` non résolues par le `slot_data` — déjà remontées dans le message de logique du slot ; la carte les affiche maintenant en avertissement visible : les remonter dans l'état de la logique du slot (API + carte) au lieu de les ignorer en silence
- [ ] Brancher la vraie room de Romain via la page Configuration (Playwright) — **fait le 2026-10-11 vers 02 h** (22 slots, 19 avec logique, ancienne config de test en `.bak`, serveur de test local arrêté) ; la room dort (11 h sans activité) : reste à vérifier connexion, logique, RAM et temps quand quelqu'un l'aura ouverte : tous ses slots connectés, logique calculée pour les jeux activés, aucune erreur dans `data/logs/app.log`, RAM et temps de calcul relevés, captures, écarts avec la room de test notés ; arrêter ensuite le serveur de test local. La room dort : ne pas la réveiller juste pour ce test, attendre qu'elle soit éveillée ou marquer « à vérifier par Romain »
- [x] README, `docs/API.md` et « À faire par Romain » mis à jour (procédure réelle, nouvelles routes)
- [ ] Relecture M11 + commit/push + notif — relue (Entrée qui enregistrait, règles de noms d'Archipelago `handle_name`, slots d'une autre room, jeux pondérés, live regions : corrigés) ; reste à cocher après la vérification de la vraie room éveillée

## M12 — Historique et tri (demandé par Romain le 2026-10-11)
- [x] Historique des items reçus par slot : date de réception (persistée en SQLite, à partir du moment où l'app suit le slot ; les items reçus avant sont marqués « avant le suivi »), envoyeur, location d'origine, classification ; affiché dans le détail du slot, du plus récent au plus ancien, filtrable (progression / utile / tous), paginé ; API documentée dans `docs/API.md` ; tests
- [x] Tri du tableau de bord : d'abord les jeux **actifs** (en cours de partie), puis par nombre de checks en logique décroissant, puis par checks restants ; jeux finis en dernier. « Actif » = un check fait par ce slot dans les 30 dernières minutes (horodatage persisté, seuil réglable), voir D11. Badge « actif » sur la carte. Ordre figé quand une carte est ouverte (comme aujourd'hui). Tests vitest + captures (maquette : `test-output/screenshots/m12/`)
- [ ] Relecture M12 + commit/push + notif

## M13 — Logique : jeux restants de Romain
- [x] PokéPark Wii: Pikachu's Adventure — 5/5 aléatoires + 6/6 avec le yaml de Romain, lot `m13` bout en bout, logique activée (2026-10-11). Était : compléter (seeds aléatoires si elles génèrent, sinon `--default-options`), lot bout en bout, activation, COMPAT
- [ ] Ori and the Will of the Wisps — 3/4 seeds, surestimation sur des événements de combat ; tester aussi avec le yaml de Romain
- [ ] Relecture M13 + commit/push + notif

## M14 — Autres jeux de la room (seulement quand tout le reste est fini ou bloqué)
Le niveau 1 marche déjà pour n'importe quel jeu (noms via le datapackage du serveur) : ce jalon ne concerne que la logique.
La room a 74 jeux qu'on ne gère pas encore. Pour les slots des autres joueurs, on n'a pas leurs yamls : seuls les jeux
`ut_can_gen_without_yaml` (ou dont le yaml serait fourni) auront une logique. Règle D12 : version identique obligatoire.
- [ ] Inventaire `docs/COMPAT-room.md` : pour chaque jeu de la room, apworld core 0.6.7 ou repo trouvé, version, et **checksum du datapackage identique à celui de la room** (sinon logique interdite pour ce jeu), `ut_can_gen_without_yaml`, nombre de slots
- [ ] Mesurer le coût de chaque apworld en plus (RAM et démarrage du worker, tous les mondes sont importés) ; si besoin, ne charger que les mondes des slots configurés
- [ ] Jeux core d'AP 0.6.7 présents dans la room (Factorio, Terraria, Subnautica, Stardew Valley, TUNIC, The Witness, Risk of Rain 2, Hollow Knight, Undertale, VVVVVV, A Short Hike, Overcooked! 2, Raft, Inscryption, shapez…) : yaml de test depuis le template, validation de référence, activation si OK ; résultats dans COMPAT
- [ ] Apworlds non core au checksum identique, par nombre de slots décroissant (Portal 2, Mario Kart Double Dash, R.E.P.O, PEAK…) : idem ; au plus 15 jeux dans cette session, le reste listé dans PROGRESS
- [ ] Relecture M14 + commit/push + notif
