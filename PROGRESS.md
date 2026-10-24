# Progression

## État actuel (5 lignes)
0. 2026-10-15 : v2 Observatoire testable sur `/v2` (M20). 2026-10-24 : la v2 devient l'interface par défaut sur `/`, la v1 passe sur `/v1` (D24) ; release v0.1.0 ;
   mises à jour depuis l'app, Pi et Windows (M23, D25).
   2026-10-23 : tableau de bord de la room complète (M21, D22) : v2, menu Plus → « Room complète ».
1. M0 à M19 faits (M11 vérifié sur la vraie room éveillée le 2026-10-11 ; M16 : page « Journal », logs en direct ;
   M17 : totaux, fil des items reçus, tri au choix, barres vert/bleu ; M18 : page « Objectifs » ; M19 : page
   « Historique », bouton maison, jeu actif choisi à la main, mode compact).
2. L'app tourne sur le Pi : `scripts/app.sh status` → http://<ip-du-pi>:42753, branchée sur la **vraie room** (elle s'endort quand personne ne joue ; l'app se reconnecte à son réveil).
3. Logique validée (référence à chaque sphère sur des seeds aux options aléatoires + bout en bout) pour 21 jeux sur 22, voir `docs/COMPAT.md`.
   2026-10-24 : nouvelle room (M24, D26) ; les apworlds sans source publique s'importent depuis l'Archipelago du joueur
   (D27) ; lot 1 en v0.2.1 (The Wind Waker, R.E.P.O, PEAK, Slime Rancher, Clair Obscur), lot 2 en v0.2.2 (ArchipelaCode,
   Cookie Clicker, A Dance of Fire and Ice, Bloons TD6, Blue Prince), lot 3 en v0.2.3 (Trackmania, Slime Rancher 2,
   Deep Rock Galactic, The Farmer Was Replaced, Don't Starve Together), lot 4 en v0.2.4 (Burnout Paradise Remastered,
   Geometry Dash, 2048, Baldur's Gate 3, Big Walk), lot 5 en v0.2.5 (ClusterTruck, Cyberpunk 2077, Dead Rising
   Deluxe Remaster, Dome Keeper, Donut County), lot 6 en v0.2.6 (DREDGE, Enter The Gungeon, Fall Guys, Fez, Hades),
   lot 7 en v0.2.7 (Hades2Rogue, Keep Talking and Nobody Explodes, Luigi's Mansion, Nine Sols, Nodebuster), lot 8 en
   v0.2.8 (Peggle Deluxe, Peggle Nights, Powerwash Simulator, Stray, Super Meat Boy), un lot de 5 par version.
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
- Balatro, Phantom Hourglass (2026-10-11) puis PokePark (M13, 2026-10-11) : validés et activés.

### M8 — Bonus
- Page Configuration : lien de room archipelago.gg → slots découverts, mot de passe, yamls, joueur par slot.
  Le port de la room est relu automatiquement quand elle se réveille sur un autre port.
- Multi-joueurs : champ `owner` + filtre par joueur.
- Robustesse : reconnexion, room qui change de port, mauvais mot de passe, worker de logique qui meurt (tests).
- Perf sur le Pi, 22 slots : 13 s au démarrage, 0,5 s pour tout recalculer, worker ~400 Mo (`scripts/testenv/perf_all22.py`).

### Nuit du 2026-10-11
- Balatro et Phantom Hourglass : bout en bout OK (lot `tests/fixtures/m7c`), 5/5 seeds avec les **vrais yamls de Romain**
  (`validate_logic.py --yaml`), logique activée → 19 jeux avec logique.
- M9 backend : yamls (liste récursive, upload), test de connexion, sauvegarde/restauration de la config, option
  « Réveiller la room » coupée par défaut (la vraie room dort : timeout 2 h). Tests `tests/test_config_m9.py`.
- Audit de la page Configuration (captures `test-output/screenshots/audit-m9/`). Frictions :
  1. page blanche quand la config n'a pas de `room_url` (corrigé) ; `#config` tapé dans la barre d'adresse ignoré ;
  2. yamls des sous-dossiers (`config/players/romain/`) invisibles ; aucun import depuis le navigateur ;
  3. yaml à choisir à la main pour chaque slot, sans contrôle (jeu ou nom différent acceptés) ;
  4. rien n'indique quels jeux ont besoin d'un yaml ou n'ont pas de logique ;
  5. 142 slots : le champ « Nom contenant… » ne filtre pas la liste, pas de filtre par jeu ;
  6. « Découvrir » réveillait la room ; pas d'info sur la room (endormie, nombre de jeux) ;
  7. pas de test du mot de passe avant d'enregistrer, pas de retour en arrière.
- M10 (shadcn-vue) et M11 (page Configuration refaite, lien `#config?room=`, vraie room branchée) : faits et relus ;
  M11 attend encore la vérification sur la vraie room **éveillée** (connexion des 22 slots, logique, RAM, temps).
- M12 : historique des items reçus dans le détail d'un slot (date de réception, filtre ★/◆, pagination ; « avant le
  suivi » pour les items déjà là, intervalle « hier 22:15 → aujourd'hui 08:00 » pour ceux arrivés pendant que l'app
  ne suivait pas), badge « Actif » et tri actifs → checks en logique → restants (durée réglable dans Configuration →
  Affichage). Relecture : horloge du navigateur corrigée par celle du serveur, rafales `!release`/`!collect` ignorées,
  écritures SQLite regroupées, migration des tables. Captures maquette : `test-output/screenshots/m12/`.
- M13 : PokePark validé (5/5 aléatoires, 6/6 avec ton yaml, lot `m13`) et activé ; Ori WotW validé avec ton yaml
  (5/5 + lot `m13w`) et activé → **21 jeux sur 22 avec logique** (OoT mis de côté).
- M14 : inventaire de la room (`scripts/room_inventory.py` → `docs/COMPAT-room.md`, sans réveiller la room). Découverte
  importante : la room a été générée avec **TWW HD `main`** (pas la release v1.0.2-beta) et **AEMinecraft 0.7.0-rc** :
  apworlds alignés (épinglage par commit dans `config/apworlds.yaml`), logique revalidée à ces versions. Le worker
  refuse maintenant la logique si la version d'un jeu diffère de celle de la room (D12).
- M14 (suite) : logique pour **23 autres jeux de la room** (tous validés sur seeds aléatoires + lots `m14`, `m14b`) :
  13 jeux core (The Witness, Risk of Rain 2, Terraria, Undertale, A Short Hike, Inscryption, shapez, Raft,
  Civilization VI, Paint, et avec adaptateurs Subnautica, VVVVVV, Overcooked! 2) + 6 apworlds installés à la version de la room
  (Mario Kart Double Dash, Archipeladoku, Lego Star Wars TCS, Outer Wilds, Portal 2 — ces 5-là **sans yaml**, donc
  utilisables pour les slots de tes amis — et Haste). Les autres demandent le yaml du joueur (clé `yaml` du slot).
  Hollow Knight ajouté ensuite (adaptateur des coûts), puis Stardew Valley (crochet sur les items reçus ; peut retarder
  d'un point de pourcentage, jamais avancer). Lethal Company et Satisfactory aussi (adaptateurs). Non activés : Factorio (impossible
  sans spoiler : slot_data vide), TUNIC (autre version). Détail : `docs/COMPAT.md`, inventaire : `docs/COMPAT-room.md`.

- 2026-10-13 : README réécrit avec la procédure d'installation complète (prérequis, bootstrap, config, lancement,
  mise à jour, désinstallation, dépannage). Procédure rejouée sur un clone neuf : bootstrap 1 min 10, ~400 Mo,
  `check_apworlds.py` tout OK, app lancée avec le `room.example.yaml` (ouvre la page Configuration).

- 2026-10-13 : logique Celeste fausse sur la nouvelle room (yaml de l'ancienne : pas de roomsanity) → adaptateur
  `_celeste` (options du slot_data) et avertissement générique quand le monde recalculé n'a pas toutes les locations
  du slot (D19). `validate_logic.py --tool-yaml` valide la logique avec un autre yaml que celui de la seed.

- 2026-10-14, M19 : page « Historique » (`#history` : checks envoyés avec leur contenu et leur destinataire, items
  reçus, compte par slot ; contenu demandé au serveur par `LocationScouts` sur les checks faits seulement, option
  désactivable, D20), bouton maison, « Définir comme actif » / « Plus actif » sur les cartes, affichage « Compact ».
  Vérifié sur la vraie room : les 67 checks faits ont leur contenu. Captures : `test-output/screenshots/m19/`.

### 2026-10-14 — Réseau IPv6 seul et objectifs sans « ? »
- Connexion depuis un partage de connexion de téléphone (IPv6 seul, NAT64) : archipelago.gg résolu en
  `64:ff9b::…` était refusé comme « adresse privée ». `room.py` juge maintenant l'IPv4 traduite (une IPv4 privée
  derrière NAT64 reste refusée) ; tests `tests/test_room_target.py`.
- Objectifs : plus d'étape « ? » quand un check la montre. Ori BF : compteur « Cartes activées » (locations des
  cartes, ou `ProgressiveMap1..9`) ; Ori WotW : compteur « Wisps » (les 5 locations des Wisps) ; SM64 : Bowser in
  the Dark World / Fire Sea suivent leur clé. « ? » seulement si ces locations manquent au slot.
- Objectif de Mario Kart Double Dash (jeu arrivé avec la nouvelle room, à la place d'OoT) : compteur de trophées
  (`trophy_requirement` du slot_data), puis All Cup Tour débloqué, cylindrée minimale et victoire ; le mode vient du
  yaml, sinon de la présence de la location « All Cup Tour Gold ». Les 22 slots ont maintenant un objectif.
- Yamls de `config/players/romain/` reliés aux 22 slots dans `config/room.yaml` (10 slots n'ont pas le même nom que
  leur yaml, « Associer automatiquement » ne les trouve pas) : logique OK pour les 22 jeux.

### 2026-10-23 — Tableau de bord de la room complète (M21)
- Module `backend/multitracker/roomfeed/` : écoute de la room (une connexion, lecture seule), journal JSONL,
  rattrapage par l'API du site, joueurs, présence. API `/api/roomfeed*` (docs/API.md), page v2 « Room complète ».
- Test réel sur serveur local (`tests/test_roomfeed_live.py`, port 38283) : checks entendus en direct, le serveur ne
  rejoue rien, et les checks faits pendant une coupure sont rattrapés une fois chacun.

### 2026-10-24 — Version portable pour Windows (M22, D23)
- `.github/workflows/windows.yml` : zip de 74 Mo (Python 3.13 autonome, AP 0.6.7, apworlds du lock, interface,
  `Multitracker.exe`). Premier run réussi (40042769711) : les 46 apworlds se chargent sous Windows, l'app démarre.
- Releases : **v0.1.0** et **v0.2.0** (mises à jour depuis l'app, D25) le 2026-10-24, notes en français (`gh release edit --notes-file`). Pour la suivante : pousser un tag `v*` ; les copies Windows ≥ v0.2.0 la proposent d'elles-mêmes.

### 2026-10-24 — AEMinecraft 0.7.0-rc.5
- La room utilise AEMinecraft **rc.5** (checksum `0741e682`, calculé pour rc.3, rc.4, rc.5 : rc.3/rc.4 = rc.2) : la
  logique de `romain_minecraft` était coupée par D12 (« autre version »). Épinglé sur rc.5, `room_inventory.py` :
  47 identiques, 1 différent (TUNIC, jeu core d'un ami : version d'AP différente, logique déjà désactivée).
- Validation : 5/5 seeds aléatoires, 2/2 avec `romain_mc.yaml`, e2e m7a OK. Dans l'app : 43 checks en logique.

## À faire par Romain
- **Refonte de l'affichage** : brief pour Claude Design dans `docs/design/BRIEF-claude-design.md`, captures de
  l'app actuelle dans `test-output/design/captures-app-actuelle.zip` (23 captures, refaites le 2026-10-14 après M19,
  brief inclus ; script `test-output/design/capture.mjs`).
- **Yamls de la nouvelle room** : faits le 2026-10-14 (copiés de `~/romaing/Validés`, anciens gardés dans
  `config/players/romain-ancienne-room/`, non versionné ; `config/players/romain/` est commité depuis) ; plus aucun jeu ne signale de locations manquantes.
- **Room vérifiée le 2026-10-11 vers 10 h 30** : 22 slots connectés, logique OK pour 21 jeux (OoT indisponible).
  À confirmer en jeu : Kingdom Hearts Birth by Sleep affiche 0 check en logique avec 11 checks faits.
- **Journal** : bouton « Journal » en haut de l'app (ou `http://<pi>:42753/#logs`) pour suivre les logs en direct.
- **Vraie room branchée** (2026-10-11) : 22 slots, yamls de `config/players/romain/`. La room dormait : l'app
  se connecte dès que quelqu'un l'ouvre (ou bouton « Réveiller maintenant »). Pour revenir au multiworld de test :
  Configuration → « Restaurer la configuration précédente » (et relancer le serveur de test,
  `.venv/bin/python scripts/testenv/serve.py start "$(ls -t test-output/seeds/multi5-42-*/AP_*.zip | head -1)"`).
- `config/room.real.yaml` a servi à la mise en place ; tu peux le supprimer (le mot de passe est dans `config/room.yaml`).
- **Démarrage automatique** (optionnel) : `scripts/app.sh stop`, puis
  `mkdir -p ~/.config/systemd/user && cp deploy/multitracker.service ~/.config/systemd/user/ && systemctl --user daemon-reload && systemctl --user enable --now multitracker`
  et `sudo loginctl enable-linger romain`.
- **Tailscale** n'est pas installé sur le Pi : `curl -fsSL https://tailscale.com/install.sh | sh && sudo tailscale up`.
  Ensuite `http://<ip-tailscale-du-pi>:42753` fonctionne (l'app écoute sur `0.0.0.0`).

## Prochaines étapes
Ordre de travail (BACKLOG.md, revu avec Romain le 2026-10-11) : M10 design shadcn-vue → M11 page Configuration
et vraie room → M12 historique et tri → M13 PokePark puis Ori WotW → M14 autres jeux de la room.
Reste (2026-10-11) : vérification M11 sur la room éveillée ; pistes : recherche
d'autres apworlds (jeux à 1 slot).
OoT est mis de côté à la demande de Romain.
