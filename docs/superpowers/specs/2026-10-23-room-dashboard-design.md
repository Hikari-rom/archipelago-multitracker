# Tableau de bord de la room complète — design

Demandé par Romain le 2026-10-23. Statut : validé (« Vas y en autonomie »).

## But

Une page « Room » (menu « Plus » de la v2, à côté de Journal / Configuration) qui montre des stats sur **toute la
room** (154 slots aujourd'hui), pas seulement les slots suivis :

- classement par joueur (puis par slot) : checks faits / total, %, buts atteints ; BK seulement pour les slots de
  Romain (logique déjà calculée) ;
- fil des checks en direct : qui a trouvé quoi pour qui ;
- activité dans le temps : checks par heure et par jour, pour la room ou un joueur ;
- qui joue maintenant.

L'historique de tous les checks est **écrit dans des fichiers** (on ajoutera plus tard de quoi les nettoyer). Le
module est **à part** et **désactivé par défaut** : un réglage l'active (on l'active pour Romain).

## Contraintes (rappel des règles du projet)

- Zéro spoiler : on ne montre que des checks déjà faits (annoncés à toute la room par le serveur) et des items déjà
  reçus (API publique du tracker). Pas de `LocationScouts` dans ce module, pas de hints.
- Lecture seule : la connexion d'écoute n'envoie que `GetDataPackage`, `Connect`, `Get`, `SetNotify` (liste blanche
  existante, `LocationScouts` en plus interdit).
- Ne jamais réveiller la room depuis ce module (ni page de la room, ni connexion si l'adresse est inconnue).
- Pi : pas de dépendance nouvelle côté backend ; mémoire raisonnable (données en tuples compacts).
- Code/commentaires/commits en anglais, interface et docs en français, noms de jeux/items/locations non traduits.

## Ce qu'on sait du serveur (vérifié dans `vendor/Archipelago`)

- `register_location_checks` diffuse un `PrintJSON` `type: "ItemSend"` (`receiving`, `item` = NetworkItem
  `{item, location, player=envoyeur, flags}`) à **tous les clients de l'équipe** (`broadcast_team`), sauf ceux qui
  ont le tag `NoText`. Une seule connexion voit donc tous les checks. Les releases passent par le même chemin.
- Rien n'est rejoué : un client qui se reconnecte ne reçoit pas les `ItemSend` manqués.
- `Join` (`slot`, `team`, `tags`) et `Part` (`slot`, `team`, **sans tags**) sont diffusés à tous.
- `_read_client_status_{team}_{slot}` : 0 inconnu, 5 connecté, 10 prêt, 20 en jeu, 30 but. Repasse à 0 quand le
  dernier client du slot part ; 30 est définitif. Nos propres connexions de suivi tiennent les slots de Romain à ≥ 5.
- WebHost : `GET /api/room_status/<room>` donne `tracker` (id) ; `GET /api/tracker/<tracker>` (cache 60 s, lit la
  dernière sauvegarde de la room) donne pour chaque slot `player_items_received` (`[item, location, envoyeur,
  flags]`), `player_checks_done`, `activity_timers`, `connection_timers`, `player_status`, `total_checks_done` ;
  `GET /api/static_tracker/<tracker>` (cache 300 s) donne `player_locations_total` et `player_game`. Ces lectures
  ne réveillent pas la room.

## Architecture

Nouveau paquet `backend/multitracker/roomfeed/`, piloté par `Service` mais isolé : ses tâches attrapent leurs
erreurs, il n'écrit rien dans l'état des trackers, et `room_dashboard: false` veut dire aucune connexion, aucune
requête, aucun fichier écrit.

| Fichier | Rôle |
|---|---|
| `players.py` | Regroupement des slots en joueurs (règle auto + `config/room_players.yaml`). |
| `log.py` | `RoomLog` : fichiers JSONL du seed, index en mémoire, dédoublonnage, état persistant. |
| `catchup.py` | Lecture et analyse de l'API tracker (HTTP injectable), fusion du rattrapage. |
| `listener.py` | `RoomListener` : connexion WebSocket d'écoute (reconnexion, liste blanche). |
| `presence.py` | Modèle « qui joue » (Join/Part, statuts, checks récents). |
| `feed.py` | `RoomFeed` : orchestre écoute + relevés, calcule résumé / fil / activité, publie les événements. |

### Écoute en direct (`RoomListener`)

- Se connecte comme le **premier slot configuré** (mot de passe de la config) à l'adresse courante du service
  (`service.current_server`, rafraîchie par la logique existante de la room). Tags `["Tracker"]` (pas `NoText`),
  `items_handling: 0`, `slot_data: false`.
- À `RoomInfo` : demande les datapackages manquants via le cache partagé `DataPackageCache` (tous les jeux de la
  room, une seule fois grâce au cache SQLite).
- À `Connected` : garde `team`, la table des slots (`players` + `slot_info`), puis `Get` + `SetNotify` sur les
  clés `_read_client_status_{team}_{slot}` de tous les slots.
- `PrintJSON` `ItemSend` → `on_check(sender, receiver, item, location, flags, at=time.time())`. NetworkItem accepté
  en dict ou en liste. `Join`/`Part` → `on_presence`. `Retrieved`/`SetReply` des clés de statut → `on_status`.
  Les autres messages sont ignorés.
- Reconnexion avec délai croissant (2 s → 60 s), comme `SlotTracker`. Adresse inconnue → attendre, sans réveil.
- Chaque nouvelle session déclenche un relevé de rattrapage.

### Relevés HTTP et rattrapage (`catchup.py`)

- Id du tracker lu dans `room_status` (champ `tracker`, ajouté à `RoomInfo`). Sans `room_url` (serveur seul) :
  écoute seulement, l'état le dit (« rattrapage indisponible sans lien de room »).
- Relevé du tracker : au démarrage, après chaque (re)connexion de l'écoute, puis toutes les 5 min (10 min si la
  room dort). Statique (totaux, jeux) : au démarrage puis toutes les 30 min. HTTP en `asyncio.to_thread`, mêmes
  protections que `room.py` (hôtes autorisés, pas de redirection).
- Fusion : pour chaque `[item, location, envoyeur, flags]` reçu par un slot, clé `(envoyeur, location)`. Envoyeur 0
  (serveur, inventaire de départ) ignoré. Clé inconnue → entrée `src: "catchup"`, `at: null`, avec une fenêtre
  `after`/`before` :
  - `before` = heure du relevé ;
  - `after` = début de la dernière période sans écoute (déconnexion de l'écoute, ou dernier « battement »
    `last_live_at` enregistré avant un arrêt de l'app) ; `null` si on n'a jamais écouté ce seed (historique
    d'avant : heure inconnue).
- Les données du tracker peuvent avoir quelques minutes de retard : un check manqué peut n'apparaître qu'au relevé
  suivant ; la fenêtre reste juste (son début ne bouge pas tant qu'aucune écoute n'a couvert la période).
- Un `ItemSend` reçu pour une clé déjà rattrapée est ignoré (dédoublonnage par clé).

### Stockage (`RoomLog`)

- Dossier `data/room_feed/<seed_name>/` (le seed vient de `RoomInfo` de l'écoute ; `data/` est déjà hors git).
- `checks-AAAA-MM-JJ.jsonl` : une ligne par check, fichier du **jour d'enregistrement** (heure locale), en ajout
  seul. Champs : `recorded_at`, `at` (ou null), `after`, `before`, `src` (`live`/`catchup`), `sender`, `receiver`,
  `item`, `location`, `flags`, et pour la lecture humaine `sender_name`, `sender_game`, `receiver_name`,
  `receiver_game`, `item_name`, `location_name` (null si le datapackage manquait ; les ids font foi, les noms sont
  recalculés à la lecture).
- `presence.jsonl` : `{at, slot, event: "join"|"part", tags}`.
- `state.json` : `{last_live_at, listening_since}` (battement toutes les 60 s pendant l'écoute).
- Au démarrage : relecture de tous les `checks-*.jsonl` du seed (lignes illisibles ignorées et comptées).
- En mémoire : tuples compacts + ensemble des clés. Aucun fichier n'est jamais supprimé par l'app.
- Erreur d'écriture : journalisée, l'entrée reste en mémoire, l'état l'affiche.

### Joueurs (`players.py`)

- Base d'un nom de slot = partie avant le premier `_` (sinon le nom entier), comparaison sans casse.
- Groupe = bases partageant un préfixe d'au moins 3 lettres avec une autre base ; nom du groupe = plus long préfixe
  commun du groupe (casse de la première occurrence). Une base seule forme son propre groupe.
  Exemples : `romain_*` → romain ; `MaxFez`, `MaxTD6`, `MaxTruck` → Max ; `dashxcel`, `dashxori_blind` → dashx ;
  `experts@miami` → experts@miami.
- `config/room_players.yaml` (hors git) : `slot: joueur`, prioritaire. Créé pour Romain avec `balatrom: romain`.
- Le joueur qui possède un slot configuré dans l'app est marqué « toi ».

### Qui joue (`presence.py`)

Pour chaque slot, un état `playing` / `connected` / `offline` / `unknown` et `last_check_at` :
- `Join` d'un client sans tag `Tracker`/`TextOnly`/`HintGame` → `playing` jusqu'au prochain `Part` du slot.
- `Part` → `offline`, sauf si le statut serveur du slot est ≥ 5 et que le slot n'est pas suivi par l'app
  (→ `connected`).
- Au début d'une session d'écoute (Joins antérieurs inconnus) : slots non suivis → statut 20/10 = `playing`,
  5 = `connected`, 0 = `offline` ; slots suivis par l'app (statut faussé par nos connexions) → `unknown`.
- Un check dans les 10 dernières minutes compte comme `playing` (affiché « actif il y a N min »).
- Limites écrites dans la page (une ligne d'aide).

### API

- `GET /api/roomfeed` → `{enabled, state: "off"|"starting"|"listening"|"disconnected"|"error", error, seed,
  listening_since, last_poll_at, poll_error, catchup_available, unreadable_lines, dir}`.
- `GET /api/roomfeed/summary` → `{room: {done, total, slots, goals, playing}, players: [{player, me, done, total,
  goals, playing, last_check_at, slots: [{name, game, done, total, goal, presence, last_check_at, bk}]}]}`
  (`bk` seulement pour les slots suivis, depuis la logique du service, sinon null).
- `GET /api/roomfeed/checks?limit=50&offset=0&player=&slot=&game=` → plus récent d'abord (`at`, sinon `before`,
  sinon `recorded_at`), avec noms, catégorie (flags) et `mine` (receveur = slot suivi).
- `GET /api/roomfeed/activity?bucket=hour|day&player=` → buckets (48 h par heure, 30 jours par jour, heure locale du
  serveur) `{start, count, by_player}`, plus `undated` (checks sans heure ni fenêtre ≤ 2 h ; une fenêtre ≤ 2 h est
  placée à son milieu).
- 404 sur les trois dernières si le module est désactivé.
- SSE `/api/events` : `event: roomfeed_check` (une entrée du fil, regroupées par lot toutes les 0,5 s) et
  `event: roomfeed` (état/résumé changés, au plus toutes les 2 s). Rien si désactivé.
- `GET /api/config` et `PUT /api/config` gagnent `room_dashboard` (omis = inchangé) ; `/api/slots` gagne
  `room_dashboard` pour que la v2 sache s'il faut montrer l'entrée de menu.

### Réglage

`room_dashboard: false` dans `config/room.yaml` (lu/écrit par `config.py`). Case dans la page Configuration
(partagée v1/v2) : « Tableau de bord de la room complète » + phrase d'aide (une connexion d'écoute en plus, checks
écrits dans `data/room_feed/`). Changer le réglage recharge le service comme les autres réglages.

### Interface (v2 seulement)

- Vue `room`, hash `#room`, entrée « Room complète » dans le menu « Plus » (absente si désactivé ; `#room` affiche
  alors un message avec un lien vers Configuration).
- En-tête : état de l'écoute (« En écoute depuis 14:02 », « Déconnecté, rattrapage au retour »…), totaux de la room
  (checks faits / total, %, buts, joueurs en jeu).
- « En jeu maintenant » : puces joueur · jeu, avec l'état.
- Classement : tableau des joueurs (tri % ou checks, « toi » mis en avant), dépliable par slot (but ✓, BK pour les
  slots de Romain, présence).
- Fil : liste virtualisée (même technique que l'Historique), filtres joueur / jeu, étiquettes PROG/UTILE/PIÈGE,
  « pour toi » mis en avant, mention « rattrapé · entre 14:02 et 14:20 » ou « rattrapé · heure inconnue ».
  Nouveaux checks en tête en direct.
- Activité : barres SVG faites main, 48 h par heure / 30 jours par jour, toute la room ou un joueur, avec le nombre
  de checks non datés.
- Téléphone : sections empilées, cibles ≥ 44 px, pas de défilement horizontal de la page.

## Tests

- Unitaires (pytest) : regroupement des joueurs (exemples ci-dessus + fichier de corrections), `RoomLog` (ajout,
  relecture, dédoublonnage, fichier par jour, lignes illisibles, dossier par seed), fusion du rattrapage (fenêtres,
  envoyeur 0, clé déjà vue), présence, activité (buckets, non datés), API (désactivé → 404, réglage dans config).
- Intégration sur le serveur de test local (port 38283) avec le bot :
  1. l'écoute reçoit en direct chaque check du bot, avec l'heure ;
  2. écoute coupée, le bot fait plusieurs checks, écoute relancée : **aucun n'est rejoué** par le serveur ;
  3. le relevé de rattrapage (API tracker simulée à partir de l'état du serveur lu par des connexions de suivi, même
     format que WebHost) les retrouve tous, avec la bonne fenêtre, sans doublon.
  4. la liste blanche refuse toute autre commande.
- Front (vitest) : entrée de menu selon le réglage, page avec données factices (résumé, fil, activité), case de
  Configuration.
- Vraie room : lectures HTTP seulement pour vérifier le format, puis activation pour Romain et contrôle visuel.

## Hors périmètre (noté dans BACKLOG)

Nettoyage / archivage des fichiers, BK des autres joueurs, page dans la v1, stats par jeu croisées entre joueurs.
