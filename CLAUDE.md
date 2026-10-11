# Archipelago Multitracker — notes pour Claude

App web (FastAPI + Vue) qui suit les 22 jeux de Romain dans un multiworld Archipelago 0.6.7 et calcule, sans
spoiler, les checks en logique. Le cahier des charges complet est `OVERNIGHT_BRIEF.md`.

## Avant de modifier quoi que ce soit
1. Lire `PROGRESS.md` (état en 5 lignes, « À faire par Romain »), `BACKLOG.md`, `DECISIONS.md` (D1–D10),
   `docs/COMPAT.md` (matrice des jeux) et, pour l'API, `docs/API.md`.
2. Vérifier l'état réel : `git log --oneline -10`, `scripts/app.sh status`,
   `.venv/bin/python scripts/testenv/serve.py status` (serveur de test sur 127.0.0.1:38281).
3. Tenir à jour `PROGRESS.md` / `BACKLOG.md` / `DECISIONS.md` / `COMPAT.md` après chaque changement notable,
   puis commit + push sur `main` (le dépôt est celui de Romain).

## État au 2026-10-10 (fin de la session de nuit, interrompue par la limite d'usage)
- Niveau 1 OK pour les 22 jeux de Romain. Logique validée et activée pour 17 d'entre eux (21 sur 22 au 2026-10-11,
  tous sauf OoT) (`logic: true` dans `config/apworlds.yaml`).
- Ouvert : Balatro, PokePark, Phantom Hourglass (adaptateurs partiels dans
  `backend/multitracker/logic/adapters_m7.py`, logique désactivée), Ori WotW (3/4 seeds, surestime des événements
  de combat, logique désactivée). OoT bloqué (`[!]`) : récompenses de donjon impossibles à connaître sans spoiler.
- 2026-10-11 : Balatro, Phantom Hourglass, PokePark et Ori WotW activés (21 jeux avec logique, OoT mis de côté).
  Versions d'apworlds = celles de la room (D12, vérifié par le worker) : `scripts/room_inventory.py` compare les
  checksums sans réveiller la room ; TWW HD épinglé sur un commit de `main`, AEMinecraft sur 0.7.0-rc.2.
  `validate_logic.py --no-yaml` valide le mode « slot_data seul » (slots d'autres joueurs). OoT mis de côté par Romain.
  M9 backend de configuration fait ; ordre de travail : M10 design shadcn-vue → M11 page Configuration + vraie room
  (`config/players/romain/`, `config/room.real.yaml`, gitignorés) → M12 historique/tri → M13 PokePark/WotW → M14.
- `validate_logic.py --yaml <yaml>` valide la logique avec les vraies options d'un joueur (test seulement).
- M14/M15 : logique aussi pour 22 autres jeux de la room (joués par les amis de Romain) (liste et limites dans `docs/COMPAT.md`), dont
  Stardew Valley (crochet `RECEIVED_HOOKS` dans `adapters.py`) et Lethal Company (`START_ADAPTERS` : adaptateur qui
  reçoit aussi l'inventaire de départ). Factorio impossible (slot_data vide).
- `config/room.yaml` (gitignoré) pointe sur la **vraie room** de Romain depuis le 2026-10-11 (elle dort souvent :
  `curl localhost:42753/api/slots` → `room_sleeping`) ; ne jamais y connecter le bot ni les tests.

## Règles du projet (non négociables)
- **Zéro spoiler** : le code de l'app (`backend/`, `frontend/`) n'utilise que items reçus, checks, hints, yamls du
  joueur, `slot_data`, datapackage, et la liste des locations du slot. Spoiler/multidata/zip : uniquement
  `tests/` et `scripts/testenv/`, jamais importés par l'app.
- **Lecture seule** vers le serveur AP : liste blanche `ALLOWED_COMMANDS` dans `backend/multitracker/ap/tracker.py`.
  Seul le bot de test (`scripts/testenv/bot.py`, serveur local uniquement) envoie des checks.
- **Pi** : pas de sudo/apt/systemctl, rien hors du repo, pas d'install globale (Python dans `.venv/`, Node dans
  `frontend/node_modules/`), ne tuer que ses propres process (PID dans `.run/`, vérifier la ligne de commande avant
  de tuer ; attention, `pkill -f motif` peut tuer le shell courant). Max 2–3 tâches lourdes en parallèle (8 Go).
- **Langues** : code, commentaires, commits en anglais ; interface et docs du repo en français ; noms d'items,
  locations, jeux et options jamais traduits.
- Notifications ntfy : `bash scripts/overnight/notify.sh "Titre" "Message"` (fin de jalon, blocage).

## Commandes utiles
- App : `scripts/app.sh start|stop|restart|status|logs` (port 42753, logs dans `data/logs/app.log`).
- Tests backend : `scripts/test.sh -q [fichiers]` (fixe `PYTHONHASHSEED=0`, nécessaire à la reproductibilité des
  générations). Tests front : `cd frontend && npm test && npm run build`.
- Captures de l'app qui tourne : `cd frontend && node scripts/screenshot.mjs` (→ `test-output/screenshots/live/`,
  utilise `/usr/bin/chromium`).
- Ports de test déjà pris par les tests pytest : 38281 (démo), 38284 (all22), 38285/38286 (découverte de room),
  38287 (e2e), 38288 (niveau 1), 38289 (testenv). Prendre 38283 ou 38290 pour du nouveau.

## Valider la logique d'un jeu (procédure qui a marché)
1. `.venv/bin/python scripts/testenv/validate_logic.py "<nom exact du jeu>" --runs 5 [--first-run K] [--default-options]`
   (seeds aux options aléatoires, comparaison à chaque sphère avec le multiworld complet ; OK/KO/GEN/NC).
   Campagnes : `FIRST_RUN=K scripts/testenv/campaign.sh N "Jeu 1" "Jeu 2"` → `test-output/logs/campaign.summary`.
2. Sur un KO : `PYTHONHASHSEED=0 .venv/bin/python scripts/testenv/diag_logic.py <slug> <run> <sphere> 2>/dev/null`
   (items/événements/régions qui diffèrent). Lire le code de l'apworld avec `unzip -p
   vendor/Archipelago/custom_worlds/<x>.apworld <chemin>` (ne jamais modifier `vendor/`).
3. Causes déjà rencontrées : tirage aléatoire à la génération non rejoué depuis `slot_data` (→ adaptateur dans
   `backend/multitracker/logic/adapters.py` / `adapters_m7.py`, avec `patch_attr` pour restaurer proprement) ;
   hooks UT bogués dans l'apworld (WotW) ; inventaire de départ envoyé avec `flags = 0` ; génération non
   reproductible (runs « NC », sans effet sur la logique) ; état attaché aux items par le monde à leur création
   (Stardew : compteur d'items de progression → `RECEIVED_HOOKS`, appliqué aux items reçus avant le sweep).
4. Bout en bout : ajouter un lot dans `tests/fixtures/` et un test dans `tests/test_logic_e2e.py`
   (`play_until_done`), puis `logic: true` dans `config/apworlds.yaml` et mise à jour de `docs/COMPAT.md`.

## Pièges connus
- `dolphin-memory-engine` ne compile pas sur ARM : stub dans `backend/ap_stubs/` (ajouté au path seulement si absent).
- AP ouvre un sélecteur tkinter si `vendor/Archipelago/Players` manque : `apenv.setup()` le crée.
- Génération de test sans ROM : `generate_output`/`assert_generate` neutralisés, et `fill_slot_data` d'OoT débloqué
  (`scripts/testenv/generate.py`).
- Le nom de jeu de Super Mario Odyssey dans l'apworld est « Spicy Meatball Overdrive ».
- `scripts/app.sh` prend un verrou (`.run/app.lock`) : le process lancé ne doit pas hériter du descripteur 9.
