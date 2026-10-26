# API du backend

Base : `http://<pi>:42753`. JSON partout. Les noms d'items, de locations et de jeux sont ceux des apworlds (non traduits).

## `GET /api/health`
`{"ok": true, "slots": 5, "connected": 5}`

## `GET /api/slots`
```json
{"server": "archipelago.gg:38281", "slots": [SlotSummary, ...]}
```

### SlotSummary
```json
{
  "name": "Romain_Celeste",            // nom du slot (identifiant, à encoder dans l'URL)
  "game": "Celeste (Open World)",
  "owner": null,                        // joueur propriétaire (optionnel, multi-joueurs)
  "status": "connected",                // idle | connecting | connected | disconnected | error
  "error": null,                        // message (français) si disconnected/error
  "seed_name": "0205...",
  "checks": {"done": 3, "total": 233, "remaining": 230},
  "items": {"received": 12, "new": 2}, // new = reçus depuis la dernière visite
  "hints": {
    "mine_elsewhere": 1,                // mes items hintés chez les autres, pas encore trouvés
    "in_my_world": 2,                   // locations de mon monde qui contiennent un item hinté, pas encore trouvées
    "in_my_world_in_logic": 1           // ... dont en logique maintenant
  },
  "goal": false,                        // but atteint
  "logic": {
    "state": "ok",                      // ok | unavailable | pending | error
    "count": 14,                        // nombre de locations en logique (si state == ok)
    "message": null,                    // explication si unavailable/error
    "computed_at": 1791593223.0,
    "seconds": 0.42
  },
  "objective": {                        // objectif du slot (backend/multitracker/goals.py), null si jeu non décrit
    "summary": "40 fraises, puis The Summit A",
    "counters": [{"label": "Strawberry", "current": 12, "target": 40}],  // + "detail" optionnel
    "steps": [{"label": "Finir The Summit A (The Summit A - Level Clear)", "done": false}],  // done null : invisible pour un tracker
    "note": null,                       // explication optionnelle
    "source": "slot_data"               // slot_data | yaml | slot_data + yaml
  },
  "updated_at": 1791593222.5,
  "last_check_at": 1791593100.0         // dernier check de ce slot vu par l'app (epoch), null avant le premier
}
```
Le tableau de bord trie avec : jeux « actifs » (`last_check_at` dans les N dernières minutes, 30 par défaut, réglable
dans Configuration → Affichage) d'abord, puis les autres, jeux finis en dernier ; dans chaque groupe, par checks en
logique puis checks restants décroissants (D11).

## `GET /api/slots/{name}`
`SlotSummary` + :
```json
{
  "items_list": [
    {"index": 0, "name": "Dash Refill", "sender": "KH2", "own": false, "origin": "other",  // start | server | own | other
     "location": "Some Location",
     "progression": true, "useful": false, "trap": false, "new": true,
     "received_at": 1791593000.0,       // date de réception (epoch) ; null = reçu avant que l'app suive ce slot
     "received_after": null}            // renseigné si l'item est arrivé pendant que l'app ne suivait pas le slot :
                                        // reçu entre received_after et received_at
  ],
  "hints_mine_elsewhere": [Hint, ...],
  "hints_in_my_world": [Hint, ...],
  "in_logic_locations": [
    {"id": 211877922, "name": "Forsaken City - Strawberry 1", "region": "Forsaken City A",  // région ou null
     "hint": {"item": "Hookshot", "receiver": "TWWHD", "progression": true}}   // ou null
  ],
  "players": {"1": {"name": "Celeste", "game": "Celeste (Open World)"}}
}
```
Historique : les dates sont stockées en SQLite (`data/`, tables `tracking` et `item_times`) par seed et par slot.
À la première synchronisation d'un slot, les items déjà reçus restent sans date (« avant le suivi ») ; chaque item
reçu ensuite prend l'heure à laquelle l'app l'a vu arriver. Les items arrivés pendant que l'app ne suivait pas le slot
(app arrêtée, room endormie, réseau coupé plus de 2 min) n'ont qu'un intervalle : de la dernière fois où l'app suivait
le slot à la synchronisation suivante. `last_check_at` ignore les rafales de plus de 10 checks (`!release`,
`!collect`). Les écritures SQLite sont regroupées (au plus une toutes les 30 s par slot, plus à la déconnexion).

`in_logic_locations` est trié : locations hintées d'abord, puis par nom.

### Hint
```json
{"item": "Strawberry", "item_id": 1, "location": "Hyrule - Chest", "location_id": 2,
 "finder": "TWWHD", "finder_game": "The Wind Waker HD",
 "receiver": "Celeste", "receiver_game": "Celeste (Open World)",
 "found": false, "entrance": "", "status": "priority",   // unspecified | no_priority | avoid | priority | found
 "progression": true, "useful": false, "trap": false,
 "in_logic": false}   // true seulement pour une location de mon monde, en logique, pas encore trouvée
```

## `POST /api/slots/{name}/seen`
Corps optionnel `{"count": N}` (par défaut : tout ce qui a été reçu). Réponse `{"seen": N}`. 409 si le slot n'est pas encore connecté.

## `GET /api/events` (Server-Sent Events)
- `event: snapshot` — `data: {"type": "snapshot", "slots": [SlotSummary, ...]}` à la connexion.
- `event: slot` — `data: {"type": "slot", "slot": SlotSummary}` à chaque changement d'un slot.
- Commentaires `: keepalive` toutes les 20 s. `retry: 3000`.

Quand un `slot` arrive pour le slot affiché en détail, le front refait `GET /api/slots/{name}`.

## `GET /api/items/recent` — fil « Derniers items reçus »
`{"items": [...]}` : les derniers items reçus par les slots, du plus récent au plus ancien, au plus 20 par slot.
Mêmes champs que `items_list` de `GET /api/slots/{name}`, plus `slot`, `game` et `owner`. Seulement les items
envoyés par un autre joueur ou le serveur (`origin` `other` ou `server`) dont l'heure de réception est connue
(`received_at` jamais nul). Le front le recharge quand `items.received` ou `items.new` d'un slot change.

## `GET /api/history?kind=sent|received&slot=...&limit=200&offset=0` — page « Historique »
`kind=sent` : tous les checks faits par les slots (`slot` répétable, absent = tous), du plus récent au plus ancien
(heure inconnue en dernier). Chaque entrée : `slot`, `game`, `owner`, `location_id`, `location`, `checked_at`
(heure à laquelle l'app a vu le check ; `null` = fait avant que l'app note l'heure des checks), `checked_after` (si
seulement un intervalle est connu), `item`, `receiver`, `receiver_game`, `to_self`, `progression`, `useful`, `trap`.
`item` est `null` quand le contenu n'est pas connu : il vient de `LocationScouts` (option `scout_checked`, D20) ou
des items reçus par un slot suivi.
`kind=received` : tous les items reçus (champs de `items_list`, plus `slot`, `game`, `owner`).
Réponse : `{"kind", "total", "offset", "items": [...], "slots": [{name, game, owner, checks: {done, total},
sent: {known, to_others}, received}], "scout_checked"}`.

Le résumé de chaque slot (`GET /api/slots`, événements `slot`) a aussi `sent: {known, to_others}` : checks au contenu
connu, et parmi eux ceux partis chez un autre joueur.

## `GET /api/logs/stream?lines=300` (Server-Sent Events) — page « Journal »
Suit `data/logs/app.log` (écrit par `scripts/app.sh`) comme `tail -f`. Lecture seule ; le mot de passe de la room est
remplacé par `•••`.
- `event: init` — `data: {"lines": [...], "missing": false}` : les `lines` dernières lignes (max 2000) ; `missing` si
  le fichier n'existe pas (app lancée autrement que par `scripts/app.sh`).
- `event: lines` — `data: {"lines": [...]}` : lignes ajoutées (lecture toutes les 0,5 s).
- `event: reset` — le fichier a été remplacé (rotation au démarrage) ; la lecture reprend au début.
- `: keepalive` toutes les 20 s, `retry: 3000` ; le flux se ferme après 30 min (le navigateur se reconnecte et reçoit
  un nouveau `init`).

## Configuration depuis l'interface
Toutes les écritures (`POST`, `PUT`) refusent les requêtes d'un autre site (en-tête `Origin` différent de l'hôte, sauf
`MT_ALLOWED_ORIGINS`).

### `GET /api/config`
```json
{"room_url": "https://archipelago.gg/room/AbC...", "server": "", "has_password": true,
 "wake_room": false,                       // réveil automatique de la room (désactivé par défaut)
  "scout_checked": true,                    // contenu des checks faits demandé au serveur (Historique, D20)
 "room_dashboard": false,                  // tableau de bord de la room complète (désactivé par défaut)
 "has_backup": true,                       // config/room.yaml.bak existe (bouton « Restaurer »)
 "slots": [{"name": "Romain_KH2", "game": "Kingdom Hearts 2", "owner": "Romain", "yaml": "config/players/kh2.yaml"}],
 "player_yamls": ["config/players/kh2.yaml", "config/players/romain/romain_kh2.yaml"],
 "yamls": [{"path": "config/players/romain/romain_kh2.yaml",
            "players": [{"name": "romain_kh2", "game": "Kingdom Hearts 2"}],   // un par document du yaml
            "error": null}],                                                    // ou "yaml illisible : …"
 "games": {"Kingdom Hearts 2": {"logic": true, "needs_yaml": true,          // depuis config/apworlds.yaml
                                "user": false,       // apworld pas fourni par l'app, à importer (D27)
                                "imported": false}}} // importé dans data/apworlds/
```
Le mot de passe n'est jamais renvoyé. `yamls` couvre `config/players/` et ses sous-dossiers (500 fichiers au plus).

### `POST /api/discover` — `{"url": "https://archipelago.gg/room/AbC...", "wake": false}`
Lit le statut public de la room (slots, jeux, port). Avec `"wake": true`, charge d'abord la page de la room, ce qui la
démarre si elle dort. Réponse :
`{"room_url": "...", "server": "archipelago.gg:38281", "sleeping": false, "players": [{"name": "Romain_KH2", "game": "Kingdom Hearts 2"}]}`.
`sleeping` : aucune activité depuis plus que le délai d'arrêt de la room (+ 5 min de marge). 400 si l'URL est
invalide ou la room introuvable.

### `POST /api/config/test` — connexion d'essai
```json
{"room_url": "https://archipelago.gg/room/AbC...",   // ou "server": "host:port"
 "password": null,                                    // null = mot de passe enregistré (seulement vers la même room/serveur)
 "slot": "Romain_KH2"}
```
Une seule connexion en lecture seule (tag `Tracker`), fermée aussitôt. Réponse
`{"ok": true, "errors": [], "game": "Kingdom Hearts 2", "server": "archipelago.gg:38281"}` ou
`{"ok": false, "errors": ["InvalidPassword"]}` (`InvalidSlot`, `sleeping: true` si la room dort…).

### `POST /api/yamls` — `{"filename": "kh2.yaml", "content": "...", "overwrite": false}`
Enregistre un yaml de joueur dans `config/players/` (nom de fichier nettoyé, `.yaml`/`.yml`, 512 Ko au plus, au moins un
document avec `name` et `game`). Réponse `{"path": "...", "players": [...], "status": "created" | "replaced" | "unchanged"}`.
409 si un fichier du même nom existe avec un autre contenu et `overwrite` est faux ; 400 si le fichier est refusé.

### `PUT /api/config`
```json
{"room_url": "https://archipelago.gg/room/AbC...",   // ou "server": "host:port" (au moins l'un des deux)
 "password": "…",                                    // omis ou null = garder le mot de passe actuel
 "wake_room": false,                                 // omis = garder le réglage actuel
 "room_dashboard": false,                            // omis = garder le réglage actuel
 "slots": [{"name": "Romain_KH2", "game": "Kingdom Hearts 2", "owner": "Romain", "yaml": "config/players/kh2.yaml"}]}
```
Écrit `config/room.yaml` (l'ancienne version va dans `config/room.yaml.bak`) et recharge les connexions (un `snapshot`
SSE suit). `yaml` doit être un fichier de `config/players/` (sinon 400). Seul ce qui change se reconnecte (D29) : autre
serveur, room, mot de passe ou `scout_checked` → tous les slots ; sinon les slots retirés se déconnectent, les ajoutés
se connectent (et ceux qui changent de jeu se reconnectent), les autres restent connectés ; un autre `yaml` relance
seulement le calcul de la logique. Enregistrer sans rien changer ne déconnecte rien.

### `POST /api/config/restore`
Échange `config/room.yaml` et `config/room.yaml.bak` (un deuxième appel annule le premier) et recharge les connexions.

### `POST /api/room/wake`
Réveille la room une fois (au plus toutes les 30 s), relit son port et relance aussitôt les connexions.
Réponse `{"ok": true, "server": "...", "room_error": null}`.

### Champs ajoutés à `GET /api/slots` et événement SSE `room`
`room_url`, `room_error` (message si la room n'a pas pu être lue ou dort), `room_sleeping`, `wake_room`, `room_dashboard`, `now` (horloge
du serveur en secondes epoch : le navigateur s'en sert pour corriger son horloge avant de calculer « actif » et
« il y a 3 min »).
Le flux `/api/events` envoie aussi `event: room` — `{"type": "room", "server", "room_url", "room_error", "room_sleeping"}` —
juste après le `snapshot` puis à chaque changement.

### Lien direct
`http://<pi>:42753/#config?room=<lien de la room encodé>` ouvre la page Configuration pré-remplie et lance la découverte.

## Tableau de bord de la room complète

Optionnel, **désactivé par défaut** (`room_dashboard: false` dans `config/room.yaml`, réglable depuis la page
Configuration). Une fois activé, l'app écoute en lecture seule les annonces de toute la room (checks faits, connexions,
statuts) et en garde un journal. Rien n'est lu en dehors de ce que la room annonce déjà : pas de spoiler, pas de hint,
pas de `LocationScouts`, et la room endormie n'est jamais réveillée par cette fonction.

Les noms (`sender`, `receiver`, `item`, `location`, joueurs) sont des chaînes ou `null` quand le nom n'est pas encore
connu ; les identifiants numériques n'apparaissent que dans `key`.

### `GET /api/roomfeed`
Toujours 200. Désactivé : `{"enabled": false}`. Activé : l'état de l'écoute.
```json
{"enabled": true, "state": "listening", "error": null, "seed": "AbC123",
 "listening_since": 1790000000.0, "last_poll_at": 1790000300.0, "poll_error": null,
 "catchup_available": true, "unreadable_lines": 0, "dir": "data/room_feed/AbC123", "write_error": null}
```
`state` : `starting`, `listening`, `disconnected` ou `error` (alors `error` explique pourquoi). `last_poll_at` et
`listening_since` sont des secondes epoch ; `catchup_available` indique si la room publie un identifiant de tracker
(rattrapage possible) ; `write_error` est non nul si le journal n'a pas pu être écrit.

Les trois endpoints suivants répondent **404** `{"detail": "tableau de bord de la room désactivé"}` quand la
fonction est désactivée.

### `GET /api/roomfeed/summary`
Progression de la room, regroupée par joueur (les slots d'un même joueur sont réunis, les groupes d'item-link sont
exclus), du plus avancé au moins avancé.
```json
{"room": {"done": 412, "total": 2300, "slots": 24, "goals": 1, "playing": 3},
 "players": [{"player": "Romain", "me": true, "done": 120, "total": 500, "goals": 0, "playing": 1,
              "last_check_at": 1790000200.0,
              "slots": [{"name": "Romain_KH2", "game": "Kingdom Hearts 2", "done": 80, "total": 300, "goal": false,
                         "presence": "playing", "last_check_at": 1790000200.0, "active_at": 1790000200.0,
                         "bk": false}]}]}
```
`presence` : état de présence du slot (`playing` = joue ou a fait un check récemment, `connected`, `offline` ou `unknown`). `active_at` : heure (epoch) du dernier check vu **en direct** pour ce slot, ou `null` (les checks rattrapés
n'y comptent pas) ; la page affiche « actif il y a N min » quand il date de moins de 10 min. `bk` : le slot est en BK (logique calculée, plus rien en logique, pas terminé) pour les
slots suivis par l'app, `null` pour les autres.

### `GET /api/roomfeed/checks?limit=50&offset=0&player=&slot=&game=`
Checks faits dans la room, du plus récent au plus ancien. `limit` est borné à 1–500, `offset` ≥ 0 ; `player`
(joueur regroupé), `slot` (nom du slot qui a fait le check) et `game` filtrent, vides ou omis = pas de filtre.
```json
{"total": 812, "offset": 0,
 "items": [{"key": "17:4521", "at": 1790000200.0, "after": null, "before": null, "src": "live",
            "sender": "Romain_KH2", "sender_game": "Kingdom Hearts 2", "sender_player": "Romain",
            "receiver": "Alice_Celeste", "receiver_game": "Celeste (Open World)", "receiver_player": "Alice",
            "item": "Strawberry", "location": "Chapter 1 Berry", "category": "PROG",
            "mine": false, "self": false}]}
```
`key` (`<slot émetteur>:<location>`) identifie un check de façon unique. `category` : `PROG`, `UTILE`, `PIÈGE` ou
`null`. `src` : `live` (vu en direct, `at` = heure exacte) ou `catchup` (rattrapé : `at` est `null` et le check est
situé dans l'intervalle `after`–`before`). `mine` : l'item est pour un slot suivi par l'app ; `self` : le slot
s'envoie l'item à lui-même.

### `GET /api/roomfeed/activity?bucket=hour|day&player=`
Nombre de checks par tranche : 48 heures ou 30 jours, aux frontières de l'heure locale du serveur, de la plus
ancienne à la plus récente. `player` restreint à un joueur. Un autre `bucket` donne **400**.
```json
{"bucket": "hour", "undated": 3,
 "buckets": [{"start": 1789999200.0, "count": 5, "by_player": {"Romain": 3, "Alice": 2}}]}
```
`undated` compte les checks rattrapés dont l'intervalle est trop large pour être daté.

### Événements SSE (sur `/api/events`)
Aucune modification du flux : ces événements passent comme les autres, uniquement quand la fonction est activée.
- `event: roomfeed_check` — `{"type": "roomfeed_check", "checks": [Check, ...]}` : nouveaux checks (même forme
  que `items` ci-dessus), regroupés en lots de 200 au plus (un lot plus gros est envoyé en plusieurs événements), du plus récent au plus ancien.
- `event: roomfeed` — `{"type": "roomfeed", "status": {...}}` : le même objet que `GET /api/roomfeed`, à chaque
  changement d'état ou de progression (au plus un toutes les quelques secondes). Le front en profite pour
  rafraîchir `summary`.

**Pas de rejeu** : à la connexion (ou à la reconnexion) du flux, rien n'est renvoyé. Le client doit rattraper en
appelant `GET /api/roomfeed`, `/summary` et `/checks` puis appliquer les événements suivants (en dédoublonnant
sur `key`).

### Fichiers écrits
Dans `data/room_feed/<seed>/` (un dossier par seed, créé seulement quand la fonction est activée) :
`checks-AAAA-MM-JJ.jsonl` (un check par ligne, journal en ajout seul), `presence.jsonl` (connexions et
déconnexions) et `state.json`. Les regroupements de slots par joueur peuvent être forcés dans
`config/room_players.yaml`.

## Mises à jour (D25)

### `GET /api/update`
`{"mode": "portable"|"git"|"none", "current": {"version", "commit"?, "date"?, "running"?}, "latest": null|{...},
"available", "blocked", "checked_at", "check_error", "running", "status"}`. `latest` : pour la version portable,
`{"version": "v0.2.0", "url", "notes", "published_at", "asset"}` ; pour git, `{"version": "<sha de origin/main>",
"behind", "commits": [{"commit", "date", "subject"}]}` (commits absents du code qui tourne). `current.running` (git) :
le commit sur lequel l'app a démarré, quand le dépôt a bougé depuis. `blocked` : pourquoi la mise à jour ne peut pas
se faire depuis l'app. `status` : contenu de `data/update/status.json`
(`{"state": "running"|"restarting"|"done"|"error", "step", "message", "from", "to", "at", "progress"?}`).

### `POST /api/update/check` — `{}`
Vérifie tout de suite (GitHub ou `git fetch`) et renvoie la même chose que `GET`.

### `POST /api/update/apply` — `{}`
Lance la mise à jour (409 si rien à faire, si elle est bloquée ou déjà en cours) ; la suivre avec `GET /api/update`.
Les deux POST exigent `Content-Type: application/json` (415 sinon).

## Apworlds importés (D27)
Jeux que l'app ne fournit pas (`source: user` dans `config/apworlds.yaml`) : chacun les importe depuis le dossier
`custom_worlds` de son Archipelago. Copiés dans `data/apworlds/` (gardé par les mises à jour), puis dans
`vendor/Archipelago/custom_worlds/` par chaque process qui charge Archipelago (liste dans `.user_apworlds.json`).

### `GET /api/apworlds`
`{"dir": "data/apworlds", "default_source": "C:\\ProgramData\\Archipelago\\custom_worlds"|null,
"files": [{"file": "cookieclicker.apworld", "game": "Cookie Clicker", "in_room": true|false|null}]}`.
`default_source` : le dossier d'une installation habituelle, s'il existe ; `in_room` : null tant que la room n'est pas
connue.

### `POST /api/apworlds/import` — `{"path": "<chemin absolu du dossier>"}`
Remplace les apworlds importés par ceux du dossier dont le jeu est `source: user` dans le catalogue, redémarre le
worker de logique et recalcule tous les slots. Réponse : celle de `GET`, plus
`"report": [{"file", "game", "status": "imported"|"shipped"|"not_needed"|"unreadable"|"duplicate"}]`.
400 si le chemin n'est pas absolu ou n'existe pas ; 403 depuis une autre origine.

### `POST /api/apworlds/check` — `{}`
Compare chaque apworld importé à la room (checksum du datapackage, comme D12) : `files[].version` vaut `room`, `other`
(logique refusée), `not_loaded` (le monde ne se charge pas), `not_in_room` ou `unknown` (room pas connectée).
Les deux POST exigent `Content-Type: application/json` (415 sinon).
