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
    {"index": 0, "name": "Dash Refill", "sender": "KH2", "own": false, "location": "Some Location",
     "progression": true, "useful": false, "trap": false, "new": true}
  ],
  "hints_mine_elsewhere": [Hint, ...],
  "hints_in_my_world": [Hint, ...],
  "in_logic_locations": [
    {"id": 211877922, "name": "Forsaken City - Strawberry 1",
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
