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
  "updated_at": 1791593222.5
}
```

## `GET /api/slots/{name}`
`SlotSummary` + :
```json
{
  "items_list": [
    {"index": 0, "name": "Dash Refill", "sender": "KH2", "own": false, "origin": "other",  // start | server | own | other
     "location": "Some Location",
     "progression": true, "useful": false, "trap": false, "new": true}
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

## Configuration depuis l'interface
Toutes les écritures (`POST`, `PUT`) refusent les requêtes d'un autre site (en-tête `Origin` différent de l'hôte, sauf
`MT_ALLOWED_ORIGINS`).

### `GET /api/config`
```json
{"room_url": "https://archipelago.gg/room/AbC...", "server": "", "has_password": true,
 "wake_room": false,                       // réveil automatique de la room (désactivé par défaut)
 "has_backup": true,                       // config/room.yaml.bak existe (bouton « Restaurer »)
 "slots": [{"name": "Romain_KH2", "game": "Kingdom Hearts 2", "owner": "Romain", "yaml": "config/players/kh2.yaml"}],
 "player_yamls": ["config/players/kh2.yaml", "config/players/romain/romain_kh2.yaml"],
 "yamls": [{"path": "config/players/romain/romain_kh2.yaml",
            "players": [{"name": "romain_kh2", "game": "Kingdom Hearts 2"}],   // un par document du yaml
            "error": null}],                                                    // ou "yaml illisible : …"
 "games": {"Kingdom Hearts 2": {"logic": true, "needs_yaml": true}}}          // depuis config/apworlds.yaml
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
 "slots": [{"name": "Romain_KH2", "game": "Kingdom Hearts 2", "owner": "Romain", "yaml": "config/players/kh2.yaml"}]}
```
Écrit `config/room.yaml` (l'ancienne version va dans `config/room.yaml.bak`) et recharge les connexions (un `snapshot`
SSE suit). `yaml` doit être un fichier de `config/players/` (sinon 400).

### `POST /api/config/restore`
Échange `config/room.yaml` et `config/room.yaml.bak` (un deuxième appel annule le premier) et recharge les connexions.

### `POST /api/room/wake`
Réveille la room une fois (au plus toutes les 30 s), relit son port et relance aussitôt les connexions.
Réponse `{"ok": true, "server": "...", "room_error": null}`.

### Champs ajoutés à `GET /api/slots` et événement SSE `room`
`room_url`, `room_error` (message si la room n'a pas pu être lue ou dort), `room_sleeping`, `wake_room`.
Le flux `/api/events` envoie aussi `event: room` — `{"type": "room", "server", "room_url", "room_error", "room_sleeping"}` —
juste après le `snapshot` puis à chaque changement.

### Lien direct
`http://<pi>:42753/#config?room=<lien de la room encodé>` ouvre la page Configuration pré-remplie et lance la découverte.
