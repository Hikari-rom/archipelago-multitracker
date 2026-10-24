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
- [x] Relecture M10 + commit/push + notif (relu par un sous-agent, corrections dans d661ed6)

## M11 — Configuration : page et vraie room (demandé par Romain le 2026-10-11)
Prérequis prêts : yamls de Romain dans `config/players/romain/`, lien + mot de passe dans `config/room.real.yaml` (gitignoré).
Vérifié le 2026-10-11 : les 22 slots existent dans la room avec le bon jeu. La room compte **142 slots** (120 d'autres
joueurs) et dort souvent (timeout 2 h) : surveiller la taille du datapackage, la RAM et le nombre de hints.
- [x] Parcours « lien de room » en composants shadcn-vue : coller le lien → infos de la room (port, nombre de slots et de jeux, endormie ou non + bouton « Réveiller la room ») → mot de passe → « Tester la connexion » → sélection des slots ; lien direct `#config?room=<lien>` (et écoute de `hashchange`) qui pré-remplit la page et lance la découverte
- [x] Sélection dans une room de 142 slots : recherche qui filtre la liste, filtre par jeu, « cochés seulement », cocher/décocher les slots affichés, présélection des slots qui ont un yaml
- [x] Yamls dans la page : import de un ou plusieurs fichiers depuis le navigateur (confirmation avant de remplacer), association automatique slot ↔ yaml par `name` (avec `{player}`/`{number}`) et jeu, choix manuel toujours possible
- [x] Diagnostic par slot : jeu sans apworld (niveau 1 seulement), logique pas encore validée, yaml nécessaire mais absent, yaml d'un autre jeu ou d'un autre nom, yaml illisible ; résumé avant d'enregistrer ; case « Réveiller automatiquement la room » ; bouton « Restaurer la configuration précédente » ; bandeau « Room endormie » + « Réveiller maintenant » sur le tableau de bord
- [x] Options `random` non résolues par le `slot_data` — déjà remontées dans le message de logique du slot ; la carte les affiche maintenant en avertissement visible : les remonter dans l'état de la logique du slot (API + carte) au lieu de les ignorer en silence
- [x] (vérifié le 2026-10-11 vers 10 h 30, room réveillée par Romain : 22 slots connectés, logique OK pour 21 jeux, OoT « indisponible » comme prévu ; une erreur trouvée et corrigée (AEMinecraft, régions en enum) ; RAM : app 122 Mo + worker 470 Mo ; premier calcul des 21 slots ≈ 113 s en file, < 8 s par slot ; captures dans `test-output/screenshots/live/` ; serveur de test local arrêté) Brancher la vraie room de Romain via la page Configuration
- [x] README, `docs/API.md` et « À faire par Romain » mis à jour (procédure réelle, nouvelles routes)
- [x] Relecture M11 + commit/push + notif — relue (Entrée qui enregistrait, règles de noms d'Archipelago `handle_name`, slots d'une autre room, jeux pondérés, live regions : corrigés) ; reste à cocher après la vérification de la vraie room éveillée

## M16 — Journal en direct (demandé par Romain le 2026-10-11)
- [x] Page « Journal » (bouton dans l'en-tête, lien `#logs`) : `data/logs/app.log` en direct par SSE
  (`GET /api/logs/stream`), filtres Tout / Avertissements / Erreurs, requêtes HTTP masquées par défaut, recherche,
  pause, défilement automatique ; mot de passe de la room masqué
- [x] Bruit du démarrage du worker (≈ 430 lignes d'erreurs d'AP sans gravité : mondes core sans dépendances,
  apworlds sans manifeste) résumé en une ligne

## M12 — Historique et tri (demandé par Romain le 2026-10-11)
- [x] Historique des items reçus par slot : date de réception (persistée en SQLite, à partir du moment où l'app suit le slot ; les items reçus avant sont marqués « avant le suivi »), envoyeur, location d'origine, classification ; affiché dans le détail du slot, du plus récent au plus ancien, filtrable (progression / utile / tous), paginé ; API documentée dans `docs/API.md` ; tests
- [x] Tri du tableau de bord : d'abord les jeux **actifs** (en cours de partie), puis par nombre de checks en logique décroissant, puis par checks restants ; jeux finis en dernier. « Actif » = un check fait par ce slot dans les 30 dernières minutes (horodatage persisté, seuil réglable), voir D11. Badge « actif » sur la carte. Ordre figé quand une carte est ouverte (comme aujourd'hui). Tests vitest + captures (maquette : `test-output/screenshots/m12/`)
- [x] Relecture M12 + commit/push + notif (horloge serveur, rafales release/collect, intervalles pendant les absences, écritures regroupées, migration)

## M13 — Logique : jeux restants de Romain
- [x] PokéPark Wii: Pikachu's Adventure — 5/5 aléatoires + 6/6 avec le yaml de Romain, lot `m13` bout en bout, logique activée (2026-10-11). Était : compléter (seeds aléatoires si elles génèrent, sinon `--default-options`), lot bout en bout, activation, COMPAT
- [x] Ori and the Will of the Wisps — 5/5 avec le yaml de Romain + lot `m13w` bout en bout : logique activée (2026-10-11). Options aléatoires : 3/4, et les écarts sont des **sous-estimations** (quelques locations atteignables non montrées, jamais l'inverse)
- [x] Relecture M13 + commit/push + notif (D12 fermé par défaut, archives vérifiées)

## M14 — Autres jeux de la room (seulement quand tout le reste est fini ou bloqué)
Le niveau 1 marche déjà pour n'importe quel jeu (noms via le datapackage du serveur) : ce jalon ne concerne que la logique.
La room a 74 jeux qu'on ne gère pas encore. Pour les slots des autres joueurs, on n'a pas leurs yamls : seuls les jeux
`ut_can_gen_without_yaml` (ou dont le yaml serait fourni) auront une logique. Règle D12 : version identique obligatoire.
- [x] Inventaire `docs/COMPAT-room.md` (`scripts/room_inventory.py`, sans réveiller la room) — a révélé que la room utilise TWW HD `main` et AEMinecraft 0.7.0-rc : apworlds alignés (2026-10-11). Était : pour chaque jeu de la room, apworld core 0.6.7 ou repo trouvé, version, et **checksum du datapackage identique à celui de la room** (sinon logique interdite pour ce jeu), `ut_can_gen_without_yaml`, nombre de slots
- [x] (2026-10-11 : import des 100 mondes 472 Mo et 8,2 s, contre 446 Mo et 7,6 s avant les 7 ajouts ; pas besoin de filtrer) Mesurer le coût de chaque apworld en plus (RAM et démarrage du worker, tous les mondes sont importés) ; si besoin, ne charger que les mondes des slots configurés
- [x] (2026-10-11 : 10 activés avec yaml, 7 non — détail dans COMPAT) Jeux core d'AP 0.6.7 présents dans la room (Factorio, Terraria, Subnautica, Stardew Valley, TUNIC, The Witness, Risk of Rain 2, Hollow Knight, Undertale, VVVVVV, A Short Hike, Overcooked! 2, Raft, Inscryption, shapez…) : yaml de test depuis le template, validation de référence, activation si OK ; résultats dans COMPAT
- [x] (2026-10-11 : 7 installés, 6 activés dont 5 sans yaml — détail dans COMPAT) Apworlds non core au checksum identique, par nombre de slots décroissant (Portal 2, Mario Kart Double Dash, R.E.P.O, PEAK…) : idem ; au plus 15 jeux dans cette session, le reste listé dans PROGRESS
- [x] Relecture M14 + commit/push + notif (fixture Subnautica réaliste, `door_cost` VVVVVV plus tôt, avertissements)

## M15 — Écarts restants sur les jeux de la room (en attendant que la room se réveille)
- [x] Hollow Knight : coûts (encoches, CostSanity) tirés au hasard et non rejoués → adaptateur, 5/5 + e2e (2026-10-11)
- [x] Stardew Valley : items de progression comptés selon leur classification avant remplissage → crochet `RECEIVED_HOOKS` sur les items reçus, 6/8 (2 retards d'un point, jamais d'avance) + e2e (2026-10-11)
- [x] Factorio : bloqué [!] — slot_data vide, coûts des technologies seulement dans le mod (2026-10-11)
- [x] Lethal Company : lune de départ et carte des scraps tirées au hasard → adaptateur (inventaire de départ transmis aux adaptateurs `START_ADAPTERS`), 8/8 + e2e (2026-10-11)
- [x] (2026-10-11 : le test rejoue un tour sans progrès après 2 s avant de conclure ; une vraie sous-estimation
  reste bloquée et échoue toujours) e2e `m14b` instable (1 échec sur 4, le premier lancement, celui qui a généré la seed) : slot Stardew bloqué
  alors que la logique recalculée hors app sur le même état donne bien « Coop Blueprint » et « Quest: Raising
  Animals » (`scripts/testenv/diag_e2e_stuck.py m14b 17 sdv`, état sauvé dans
  `test-output/e2e_stuck_m14b_flaky_sdv.json`). Le worker, avec les 10 mondes du lot régénérés dans un
  même process, donne aussi les 2 locations : interaction entre mondes écartée ; piste restante, une course
  entre réception d'items et `logic_settled` (service ou boucle du test).
- [x] Satisfactory : options de placement absentes du slot_data et paliers 1–2 du Hub assouplis pour UT → yaml + slot_data obligatoire (`YAML_REQUIRED`) et adaptateur, 8/8 + e2e (2026-10-11)
- [x] Relecture M15 (sous-agent Sonnet : pas de bug ; doc et robustesse corrigées) + commit/push + notif

## M17 — Tableau de bord : totaux, fil des items reçus, tri, barres en deux couleurs (demandé par Romain le 2026-10-11)
- [x] Bandeau en haut : totaux des slots du filtre joueur (checks faits / total, en logique, nouveaux items) avec une barre globale, et fil « Derniers items reçus » (5, ou les 30 derniers) tous jeux confondus (`GET /api/items/recent`)
- [x] Tri au choix : « Conseillé » (ordre d'avant), « En logique » (nombre), « % en logique » (part du total du jeu) ; mémorisé sur l'appareil
- [x] Barre de progression de chaque jeu : vert = checks faits, bleu = checks en logique
- [x] Tests (backend `test_history.py`, front `dashboard.test.ts`), captures clair/sombre, mobile/bureau
- [x] Jeu actif (location cochée dans les dernières minutes) en premier, dans un grand panneau sur toute la ligne, détails ouverts par défaut (masquables) ; plusieurs jeux actifs : le plus récent d'abord, quel que soit le tri ; fil réduit à 3 items sur téléphone

## M18 — Objectifs (demandé par Romain le 2026-10-12)
- [x] Objectif de chaque slot lu dans le slot_data (sinon le yaml du joueur) et avancement mesuré sans spoiler (items reçus, checks faits) : `backend/multitracker/goals.py`, un descripteur par jeu écrit d'après les règles de victoire de l'apworld, pour les 22 jeux de Romain
- [x] Ligne « But » sur chaque carte du tableau de bord (avec le premier compteur pas encore atteint) et page « Objectifs » (`#goals`) : compteurs avec barres, étapes (faite / à faire / invisible pour un tracker), tri par avancement
- [x] Tests : `tests/test_goals.py` (les 22 jeux sur la seed all22 : compteurs à 0 au départ, pleins avec tout le pool), `frontend/tests/goals.test.ts`
- [x] (2026-10-14) Étapes « ? » remplacées quand un check les montre : cartes d'Ori BF, Wisps d'Ori WotW, Bowser de SM64
- [x] (2026-10-14) Mario Kart Double Dash (remplace OoT dans la nouvelle room) : trophées, puis All Cup Tour (débloqué, cylindrée minimale, victoire) ou objectif « trophées »
- Plus tard, si Romain suit d'autres slots : descripteurs pour les autres jeux de la room (Stardew, Hollow Knight, Subnautica…)


## M19 — Historique, bouton maison, jeu actif choisi, mode compact (demandé par Romain le 2026-10-13)
Fond étoilé et thèmes : après les maquettes de Claude Design (`docs/design/BRIEF-claude-design.md`).
- [x] Heure de chaque check (première fois que l'app voit la location faite), persistée comme celle des items
- [x] Contenu des checks faits demandé au serveur (`LocationScouts`, uniquement des locations déjà faites, sans hint), mis en cache ; désactivable dans Configuration ; sans ça, l'item n'est connu que s'il va vers un slot suivi
- [x] `GET /api/history` (checks envoyés et items reçus, par slot) et nombre de checks envoyés aux autres dans le résumé de chaque slot
- [x] Page « Historique » (`#history`) : onglets Envoyés / Reçus, filtre par jeu, tableau du nombre de checks envoyés par slot
- [x] Bouton maison dans l'en-tête (retour au tableau de bord)
- [x] Jeu actif choisi à la main (« Définir comme actif ») et carte active désactivable (« Plus actif » : redevient active seulement au prochain check)
- [x] Mode compact : à gauche la carte du jeu actif (un seul : choisi à la main, sinon le check le plus récent), à droite la liste compacte des jeux (nom, barre, en logique) ; un clic change le jeu affiché
- [x] Hints dans les cartes au format « Objet → check ∆ monde » (demandé par Romain le 2026-10-14)
- [x] Tests (backend 69 + `test_history_checks.py`, front 75), captures `test-output/screenshots/m19/`, docs (API, D20, PROGRESS), relecture, commit/push

## M20 — v2 « Observatoire » sous /v2 (demandé par Romain le 2026-10-15)
- [x] Entrée séparée `/v2` et lien depuis la v1
- [x] Thèmes Nuit et Plan (tokens, contraste AA testé) + ciel animé
- [x] Tableau de bord Cartes et Focus, téléphone
- [x] Historique par jour (pages de 50, liste virtualisée, page suivante chargée en arrivant en bas : 2026-10-22)
- [x] Historique par jour
- [x] Objectifs
- [x] Captures `test-output/screenshots/v2/` prises avec Firefox headless (puppeteer-core) ; `screenshot-v2.mjs` (Playwright) demande Chromium, absent ici
- [ ] 3e/4e thème
- [x] Configuration : barre « Enregistrer » en haut, une ligne compacte par slot (2026-10-24)
- [x] Cartes et Focus : BK en rouge (bordure, fond, chiffre), jeu terminé en or (liseré, filet intérieur, halo qui respire, inspiré des cartes d'Enigmatik) (2026-10-24)
- [x] Listes longues dans un cadre de hauteur fixe : Historique v1/v2, slots de Configuration (2026-10-24)
- [x] v2 par défaut sur `/`, v1 sur `/v1`, `/v2` redirige vers `/` (2026-10-24, D24)
- [ ] Refonte Journal/Configuration
- [ ] Retrait de la v1 quand la v2 est validée

## M21 — Tableau de bord de la room complète (demandé par Romain le 2026-10-23)
- [x] Connexion d'écoute en lecture seule, journal JSONL par seed dans `data/room_feed/`
- [x] Rattrapage des checks manqués depuis l'API du site (testé : checks manqués retrouvés une fois chacun)
- [x] Joueurs (auto + `config/room_players.yaml`), qui joue, classement, activité 48 h / 30 jours, fil des checks
- [x] Réglage dans Configuration (désactivé par défaut), page « Room complète » dans le menu Plus de la v2
- [x] Fil des checks dans un cadre de hauteur fixe (défilement virtuel dans le cadre, la page ne s'allonge plus) : 2026-10-24
- [ ] Nettoyage des fichiers `data/room_feed/`
- [ ] BK des autres joueurs
- [ ] Page v1

## M22 — Version portable pour Windows (demandé par Romain le 2026-10-24)
- [x] Lanceur (`scripts/windows/launcher.py`) + `Multitracker.exe` (Go) + assemblage du dossier (`build_portable.py`)
- [x] Workflow GitHub Actions `windows.yml` : Python autonome, AP 0.6.7, apworlds du lock, interface, zip, test de démarrage
- [x] Première release : v0.1.0 (2026-10-24)
- [x] Mise à jour depuis l'app, sans recopier `config/` et `data/` (M23, D25)
- [ ] Icône de l'exe, signature

## M23 — Mises à jour depuis l'app (demandé par Romain le 2026-10-24, D25)
- [x] `updater.py` + `/api/update`, `/api/update/check`, `/api/update/apply` ; vérification quotidienne
- [x] Windows : téléchargement + sha256, `Multitracker.exe` échange les dossiers et remet l'ancienne version si besoin ; `--update`
- [x] Pi : `scripts/update.sh` (fast-forward, réinstallation ciblée, build, redémarrage), commits faits sur le Pi compris
- [x] Bloc « Mises à jour » (Configuration) et bandeau v1/v2
- [x] Release v0.2.0 (premier zip qui sait se mettre à jour)
- [ ] Vérifier une vraie mise à jour Windows de la v0.2.0 vers la suivante sur un PC (la CI la simule)


## M24 — Logique pour les jeux de la nouvelle room (demandé par Romain le 2026-10-24, D26)
Par lots de 5 jeux validés, une release `v0.2.N` par lot.
- [x] Inventaire : apworlds et yamls fournis, 99 jeux sur 102 au checksum de la room
- [x] 32 apworlds sourcés sur GitHub (même sha256) dans `config/apworlds.yaml`
- [x] Distribution des 20 apworlds sans source publique identique : importés depuis l'Archipelago du joueur (D27)
- [x] Pi : les 20 copies manuelles de `custom_worlds` passées dans `data/apworlds/` par l'import (2026-10-24)
- [x] The Wind Waker (core) : adaptateur (entrées, donjons requis ; cartes mélangées = logique indisponible)
- [x] Campagne de validation des 52 jeux (2026-10-24) : 37 OK, 4 corrigés avant (PEAK, ArchipelaCode,
  Clair Obscur, Cookie Clicker) ; adaptateurs pour Trackmania, Slime Rancher 2,
  Deep Rock Galactic, The Farmer Was Replaced, Don't Starve Together ; restent Plants vs. Zombies, Spirit Tracks,
  Cuphead (1/3), CloverPit (NC), Trombone Champ et Zuma Deluxe (génération)
- [x] Lot 1 (v0.2.1) : The Wind Waker, R.E.P.O, PEAK, Slime Rancher, Clair Obscur Expedition 33 (e2e `m24a`)
- [x] Lot 2 (v0.2.2) : ArchipelaCode, Cookie Clicker, A Dance of Fire and Ice, Bloons TD6, Blue Prince (e2e `m24b`)
- [x] Lot 3 (v0.2.3) : Trackmania, Slime Rancher 2, Deep Rock Galactic, The Farmer Was Replaced, Don't Starve
  Together (un adaptateur chacun, e2e `m24c`)
- [x] Lot 4 (v0.2.4) : Burnout Paradise Remastered, Geometry Dash, 2048, Baldur's Gate 3, Big Walk (sans
  adaptateur, e2e `m24d`)
- [x] Lot 5 (v0.2.5) : ClusterTruck, Cyberpunk 2077, Dead Rising Deluxe Remaster, Dome Keeper, Donut County (sans
  adaptateur, e2e `m24e`)
- [x] Lot 6 (v0.2.6) : DREDGE, Enter The Gungeon, Fall Guys, Fez, Hades (sans adaptateur, e2e `m24f`)
- [x] Lot 7 (v0.2.7) : Hades2Rogue, Keep Talking and Nobody Explodes, Luigi's Mansion, Nine Sols, Nodebuster (sans
  adaptateur, e2e `m24g`)
- [x] Lot 8 (v0.2.8) : Peggle Deluxe, Peggle Nights, Powerwash Simulator, Stray, Super Meat Boy (sans adaptateur,
  e2e `m24h`)
- [ ] TUNIC et Pokemon Emerald : passage en Archipelago 0.6.8
