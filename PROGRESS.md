# Progression

## État actuel (5 lignes)
1. M0 à M6 faits et relus ; M7 quasi fini (17 jeux sur 22 avec logique validée) ; M8 fait (découverte de room, multi-joueurs, robustesse, perf).
2. L'app tourne sur le Pi : `scripts/app.sh status` → http://<ip-du-pi>:42753, branchée sur le multiworld de **test** local (5 jeux).
3. Logique validée (référence à chaque sphère sur des seeds aux options aléatoires + bout en bout) pour 15 jeux, voir `docs/COMPAT.md`.
4. Tests : `scripts/test.sh -q` (backend, ~10 min) et `cd frontend && npm test`.
5. Pour la vraie room : page **Configuration** de l'app (lien archipelago.gg + mot de passe + choix des slots), ou `config/room.yaml`.

## Journal

### M0 — Prise en main
- Pi 5, 8 Go RAM, 4 cœurs, ~96 Go libres, Python 3.13.5, Node 24.18. Port 42753 libre.
- Tailscale **absent** du Pi. Enigmatik : docker compose (back) / `next dev -H 0.0.0.0` (front). Voir DECISIONS D1.

### M1 — Archipelago headless
- `scripts/bootstrap.sh` (idempotent), `config/apworlds.yaml` + `scripts/fetch_apworlds.py` (lock avec sha256).
- Les 22 apworlds + Universal Tracker v0.3.0 se chargent et génèrent en headless (`scripts/check_apworlds.py`,
  `scripts/testenv/solo_check.py`). Stub `dolphin_memory_engine` (ne compile pas sur ARM).

### M2 — Environnement de test
- `scripts/testenv/generate.py` : seed hébergeable **sans ROM** (sortie des jeux et vérifs de ROM désactivées, D4).
- `scripts/testenv/serve.py` : MultiServer sur 127.0.0.1:38281-38290, PID dans `.run/`.
- `scripts/testenv/bot.py` : client de jeu qui coche des locations (refuse tout serveur non local).

### M3 — Backend niveau 1
- Une connexion tracker (tags `Tracker`, `NoText`) par slot, lecture seule garantie par liste blanche de commandes,
  reconnexion, datapackage en cache SQLite, items, checks, hints, but, « dernière visite », API REST + SSE.
- Vérifier : `scripts/test.sh -q tests/test_backend_level1.py tests/test_level1_all22.py` (22 jeux).

### M4 — Front Vue
- Vue 3 + Vite + TS, sans lib UI. Cartes triées (ordre figé quand une carte est ouverte), badge de logique,
  locations en logique groupées (hintées en tête), nouveaux items + « Marquer comme vu », hints dans les deux sens,
  thème clair/sombre/auto, mobile, SSE avec reconnexion. Captures : `cd frontend && node scripts/screenshot.mjs`.

### M5 — Logique priorité 1
- Universal Tracker en headless dans un process dédié ; sweep maison avec la classification exacte des items (D6) ;
  adaptateurs par jeu (D7) ; options aléatoires des yamls résolues via `slot_data` (D8).
- Validation : `tests/test_logic_reference.py`, `tests/test_logic_e2e.py`, campagnes
  `scripts/testenv/campaign.sh N "Jeu" ...` (résultats dans `test-output/logs/campaign.summary`).

### M6 — Déploiement
- `scripts/app.sh start|stop|restart|status|logs`, unité systemd utilisateur `deploy/multitracker.service`, README.

### M7 — Logique étendue
- Validés et activés : SM64 (adaptateur area rando), SMO, Ori BF, Slay the Spire, KH BBS, Jak 3, Pokémon Platinum/BW,
  R&C 2/3, AEMinecraft, Isaac, Mario Kart Wii (adaptateur). Lots bout en bout : `m7a`, `m7b`.
- Ori WotW : 3/4 seeds (adaptateurs spawn + doublons, régénération yaml + slot_data), logique désactivée.
- OoT : **bloqué** (récompenses de donjon inconnaissables sans spoiler), niveau 1 seulement.
- Balatro, PokePark, Phantom Hourglass : en cours.

### M8 — Bonus
- Page Configuration : lien de room archipelago.gg → slots découverts, mot de passe, yamls, joueur par slot.
  Le port de la room est relu automatiquement quand elle se réveille sur un autre port.
- Multi-joueurs : champ `owner` + filtre par joueur.
- Robustesse : reconnexion, room qui change de port, mauvais mot de passe, worker de logique qui meurt (tests).
- Perf sur le Pi, 22 slots : 13 s au démarrage, 0,5 s pour tout recalculer, worker ~400 Mo (`scripts/testenv/perf_all22.py`).

## À faire par Romain
- **Brancher la vraie room** : ouvrir l'app → Configuration → coller le lien de la room archipelago.gg,
  le mot de passe, cocher tes slots, choisir les yamls. Les yamls doivent être copiés avant dans
  `config/players/` sur le Pi. (`config/room.yaml` pointe actuellement vers le multiworld de test local.)
- Pour les jeux sans logique « sans yaml » (Celeste, KH2, Jak, TWW HD, SM64, SMO, Ori BF, KH BBS, Jak 3, R&C 2,
  AEMinecraft), le yaml est **nécessaire** à la logique.
- **Démarrage automatique** (optionnel) : `scripts/app.sh stop`, puis
  `mkdir -p ~/.config/systemd/user && cp deploy/multitracker.service ~/.config/systemd/user/ && systemctl --user daemon-reload && systemctl --user enable --now multitracker`
  et `sudo loginctl enable-linger romain`.
- **Tailscale** n'est pas installé sur le Pi : `curl -fsSL https://tailscale.com/install.sh | sh && sudo tailscale up`.
  Ensuite `http://<ip-tailscale-du-pi>:42753` fonctionne (l'app écoute sur `0.0.0.0`).
- Serveur de test local (port 38281) lancé pour la démo : `.venv/bin/python scripts/testenv/serve.py stop` pour l'arrêter.

## Prochaines étapes
- Finir Balatro / PokePark / Phantom Hourglass, retenter Ori WotW (événements de combat).
