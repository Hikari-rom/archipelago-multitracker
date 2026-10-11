# Décisions

Chaque choix non trivial, avec sa raison et les alternatives écartées.

## D1 — Exposition de l'app : bind sur 0.0.0.0:42753 (M0)
- **Constat :** Tailscale n'est pas installé sur le Pi (`tailscale` introuvable, pas d'interface `tailscale0`).
  Enigmatik n'a pas de déploiement en place : le back tourne via `docker compose` (nginx sur `APP_PORT`, 8080 par défaut),
  le front en `next dev -H 0.0.0.0`. Apache écoute sur `*:80` (vhost par défaut, sans rapport avec Enigmatik).
- **Choix :** même approche qu'Enigmatik-front : uvicorn écoute sur `0.0.0.0:42753`. Accessible en LAN, et via Tailscale
  dès qu'il sera installé (l'IP Tailscale du Pi sera couverte par `0.0.0.0`). Un `tailscale serve` éventuel est documenté
  dans `PROGRESS.md` (« À faire par Romain »).
- **Écarté :** reverse proxy Apache (demanderait `sudo`), bind sur l'IP Tailscale (inexistante).

## D2 — Universal Tracker : Tracker_v0.3.0, piloté comme bibliothèque (M1)
- **Choix :** `tracker.apworld` de la release **Tracker_v0.3.0** (FarisTheAncient/Archipelago), dernière release dont le
  core est AP 0.6.7 (v0.3.1+ visent 0.6.8). Installé dans `custom_worlds/` par `fetch_apworlds.py`.
- **Headless :** `worlds/tracker/TrackerCore.py` ne dépend pas de kivy (kivy n'est importé que dans les fonctions GUI de
  `TrackerClient.py`). On pilote `TrackerCore` directement (régénération mono-joueur `run_generator`/`TMain`, puis
  `updateTracker` = sweep `CollectionState`), sans lancer le client UT.
- **Licence :** MIT (fichier `LICENSE` racine du fork, hérité d'Archipelago ; pas de LICENSE propre à `worlds/tracker/`).
  On ne copie pas son code : on télécharge l'apworld et on l'importe. Attribution dans le README.
- **Écarté :** réimplémenter la régénération (plus de code, moins de compatibilité avec les hooks UT des apworlds :
  `interpret_slot_data`, `ut_can_gen_without_yaml`, `re_gen_passthrough`).

## D3 — Dépendances Python sur ARM (M1)
- `kivy`, `kivymd` (GUI) : non installés. `Pymem` (Windows) et `PyMemoryEditor` : installés (purs Python, importés par
  KH2 / Jak au chargement, inutilisés).
- `dolphin-memory-engine` ne compile pas sur aarch64 (sdist cassé, CMake introuvable dans l'environnement de build) et
  n'est utile qu'aux clients de jeu Dolphin. PokePark l'importe au chargement du monde : **stub** dans
  `backend/ap_stubs/dolphin_memory_engine.py`, mis en tête du `PYTHONPATH` de nos processus uniquement.
- `SKIP_REQUIREMENTS_UPDATE=1` pour empêcher `ModuleUpdate` d'AP d'essayer d'installer kivy.

## D4 — Génération de test « hébergeable » sans ROM (M2)
- `Generate.py --skip_output` saute **aussi** l'écriture du multidata (`.archipelago`) : impossible d'héberger la seed.
- **Choix :** `scripts/testenv/generate.py` remplace `World.generate_output` (l'étape qui patche les ROM / écrit les
  fichiers de jeu) par un no-op pour tous les mondes, puis lance la génération normale : on obtient le multidata et le
  spoiler sans jamais toucher de ROM. `--skip-output` reste disponible (étude de compatibilité).
- Le spoiler et le multidata ne servent qu'au code de test (`tests/`, `scripts/testenv/`).

## D5 — Format de `config/apworlds.yaml` (M1)
- Une entrée par jeu : `game` (nom exact du monde), `source` (`core`|`github`), `repo`, `tag` (`latest` ou épinglé),
  `asset` (glob), `allow_prerelease`. Section `tools` pour Universal Tracker. Le lock garde tag, URL, sha256.
- `fetch_apworlds.py` réutilise la version verrouillée tant qu'on ne passe pas `--update` (reproductible).
- Le nom de jeu de Super Mario Odyssey est **« Spicy Meatball Overdrive »** dans l'apworld v1.5.3 : c'est ce nom qui
  sert de clé (il apparaît tel quel dans le datapackage du serveur).

## D6 — Sweep maison plutôt que `TrackerCore.updateTracker` (M5)
- UT crée chaque item reçu avec `create_item` (classification par défaut) et n'applique les flags du serveur qu'en OU.
  Les items que la génération a rétrogradés (ex. fraises Celeste excédentaires, cellules de Jak) comptaient donc
  comme progression → logique surestimée (détecté par la comparaison de référence).
- **Choix :** on garde UT pour la **régénération** du monde (yaml / `slot_data` / hooks UT) et on fait le sweep
  nous-mêmes (`SlotLogic.in_logic`) avec la classification **exacte** issue de `NetworkItem.flags`.
  Exception : l'inventaire de départ (location −2) et les items serveur (−1) sont envoyés avec `flags = 0` par
  MultiServer → on garde la classification du monde (comme UT).
- La logique « glitched » d'UT n'est pas exposée (pas demandée).

## D7 — Adaptateurs de régénération par jeu (M5)
- Certains mondes font des tirages aléatoires qui changent la logique sans implémenter les hooks UT. Quand le résultat
  est connu d'un tracker classique, un adaptateur (`backend/multitracker/logic/adapters.py`) le rejoue pendant la
  régénération (patch de classe actif uniquement pendant la régénération du slot, dans le process worker).
- **TWW HD** : entrées = `slot_data["entrances"]` ; donjons requis (mode required bosses) déduits de la liste des
  locations du slot (cochées + manquantes, envoyée par le serveur au Connect) : les locations des donjons bannis
  n'existent pas. Aucune donnée de spoiler.
- **Inventaire de départ** (2026-10-11) : un adaptateur peut aussi recevoir les items reçus de la location −2
  (`START_ADAPTERS`, ex. lune de départ de Lethal Company), connus de tout client du slot. La clé de cache du monde
  régénéré les inclut pour ces jeux seulement.
- **Items reçus** (2026-10-11) : un crochet par jeu (`RECEIVED_HOOKS`) corrige les items reçus, recréés depuis leur
  nom, avant le sweep, quand le monde leur attache un état à la création (Stardew : compteur d'items de
  progression selon la classification avant remplissage). En cas d'ambiguïté, la valeur la plus prudente.

## D8 — Options aléatoires dans les yamls du joueur (M5)
- Une option `random`/pondérée serait re-tirée différemment par la régénération. Si le monde met l'option sous le
  même nom dans `slot_data`, on injecte la vraie valeur ; sinon la logique reste calculée mais un avertissement
  s'affiche sous le badge (« logique peut-être approximative »).

## D9 — Activation de la logique par jeu (M5)
- `logic: true` dans `config/apworlds.yaml` seulement pour les jeux validés (référence + bout en bout + campagne
  d'options aléatoires). Les autres affichent « Logique indisponible » (niveau 1 seulement), modifiable à la main.

## D10 — Un seul process worker pour la logique (M5)
- La génération AP n'est pas thread-safe et garde de l'état global : un process `spawn` dédié, requêtes sérialisées,
  redémarré s'il meurt ou dépasse 300 s. Un monde régénéré est gardé en mémoire par slot (clé : jeu, slot,
  `slot_data`, contenu du yaml). Sur la seed de test : ~8 s pour le premier calcul (import des mondes), puis < 0,1 s.

## D11 — « Actif » = check récent, pas le statut client (2026-10-11)
Le tri demandé par Romain met les jeux « connectés » d'abord. Le statut client du serveur ne le dit pas de façon
fiable : la connexion de l'app (tag Tracker) fait passer le slot à CLIENT_CONNECTED, et tant qu'elle reste ouverte
le serveur ne remet pas le statut à CLIENT_UNKNOWN quand le jeu se déconnecte. Un slot est donc « actif » s'il a fait
un check dans les 30 dernières minutes (horodatage vu par l'app, persisté). « Le plus de checks » = le plus de checks
en logique (ce qu'il y a à faire tout de suite), puis le plus de checks restants.
Limites acceptées (relecture M12) : une mise à jour de plus de 10 checks d'un coup (`!release`, `!collect`, but d'un
autre jeu) n'est pas de l'activité ; un `!collect` plus petit d'un autre joueur, si. L'heure affichée est celle du
serveur : le navigateur corrige son horloge avec `now` de `/api/slots`.

## D12 — Logique d'autres jeux seulement à version identique (2026-10-11)
Pour un apworld non core, la logique n'est activée que si le checksum du datapackage du jeu dans la room est
identique à celui de l'apworld installé : sinon la logique pourrait venir d'une autre version que celle de la
génération et mentir.
Appliqué partout depuis le 2026-10-11 (pas seulement aux autres jeux) : le worker de logique compare le checksum du
jeu envoyé par la room (RoomInfo) à celui de l'apworld installé et répond « logique indisponible » s'ils diffèrent.
L'inventaire `scripts/room_inventory.py` (→ `docs/COMPAT-room.md`) a montré que la room de Romain utilisait TWW HD
`main` (commit c2188264, pas la release v1.0.2-beta) et AEMinecraft 0.7.0-rc : `config/apworlds.yaml` les épingle
(`commit:` pour une branche, nouvelle source de `scripts/fetch_apworlds.py`).

## D13 — shadcn-vue + Tailwind CSS 4 pour l'interface (2026-10-11, demandé par Romain)
Composants shadcn-vue (style new-york) copiés dans `frontend/src/components/ui/` (modifiables : variantes de badge
`good`/`warn`/`info`/`muted`, `Card` avec prop `as`), sur reka-ui, Tailwind CSS 4 via `@tailwindcss/vite`, icônes
lucide. Versions figées dans `package.json`, tout en local (`node_modules/`). Les couleurs restent celles de l'app,
exposées en variables shadcn (`--background`, `--primary`…) et reliées au thème existant : la variante `dark:` suit
`data-theme="dark"`, ou le système quand le choix est « Auto » (`@custom-variant dark` dans `style.css`), donc pas de
classe `.dark` à gérer en JS. Coût : JS 92 → 221 Ko (77 Ko gzip), acceptable sur le réseau local.
Ajouter un composant : `cd frontend && npx shadcn-vue@2.8.2 add <nom>`.

## D14 — Vérification de la vraie room laissée à Romain (2026-10-11)
La room de Romain dort depuis le branchement (22 slots déconnectés, `room_sleeping`). La consigne interdit de la
réveiller pour un test : les deux tâches M11 restantes (vérification sur la room éveillée, relecture finale) sont
marquées `[!]` « à vérifier par Romain » ; la marche à suivre est dans PROGRESS.md (« À faire par Romain »).

## D15 — e2e : un tour sans progrès est rejoué une fois (2026-10-11)
Un lancement sur six de `m14b` a échoué alors que la logique recalculée hors app sur l'état bloqué était juste et que
le worker, avec tous les mondes du lot dans un même process, donnait aussi le bon résultat : course dans la boucle
du test (message du serveur arrivé tard). `play_until_done` attend 2 s et refait un tour avant de déclarer le slot
bloqué : une vraie sous-estimation reste bloquée au tour suivant et fait toujours échouer le test. Le nombre de
tours rejoués est écrit dans le résultat (`retries`).

## D16 — Journal en direct dans l'interface (2026-10-11, demandé par Romain)
La page « Journal » lit le fichier `data/logs/app.log` plutôt qu'un handler de logging : il contient tout (app,
worker de logique, sorties d'Archipelago et d'uvicorn), comme `scripts/app.sh logs`. Lecture seule, accessible comme
le reste de l'app (réseau local / Tailscale) ; rien de secret n'y est écrit et le mot de passe de la room est masqué
par sécurité. Le flux se ferme au bout de 30 min pour qu'aucune connexion ne survive à un arrêt de l'app.
Les ≈ 430 lignes d'erreurs sans gravité écrites par Archipelago à chaque démarrage du worker (mondes core dont les
dépendances ne sont pas installées, apworlds sans manifeste AP 0.7) sont résumées en une ligne : sinon le filtre
« Erreurs » ne montrait que ça. Les autres messages passent tels quels.
