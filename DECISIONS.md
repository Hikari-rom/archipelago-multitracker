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

## D17 — Tableau de bord : fil des items reçus et tri au choix (2026-10-11, demandé par Romain)
Le fil « Derniers items reçus » ne montre que les items envoyés par un autre joueur (ou le serveur) dont l'heure de
réception est connue : ni les items trouvés dans son propre monde (on vient de les ramasser soi-même), ni
l'inventaire de départ, ni les items reçus avant que l'app suive le slot. Le serveur garde les 20 derniers par slot
(`/api/items/recent`), pour qu'un filtre sur un joueur ait toujours sa part ; le front filtre et en montre 5 (ou 30).
Il est rechargé (regroupé sur 1 s) quand le nombre d'items reçus ou de nouveaux items d'un slot change.
Tri « % en logique » : checks en logique / total du jeu (le même rapport que la partie bleue de la barre), choix de
Romain. Dans les tris « En logique » et « % en logique », les jeux sans logique puis les jeux terminés vont à la fin
et les égalités gardent l'ordre « Conseillé ». Les jeux terminés ne comptent pas dans le total « en logique ».
Sur mobile (< 700 px), l'en-tête n'est plus collé en haut : avec les totaux et le tri, il prenait près de la moitié
de l'écran.
Jeu actif en grand panneau (demande de Romain) : tout jeu « actif » (réglage « Actif » de la page Configuration,
30 min par défaut) passe en tête dans une carte pleine largeur, détails affichés d'emploi (locations en logique,
nouveaux items, hints) et rafraîchis en direct. « Masquer les détails » reste respecté. Le fil des items reçus reste
au-dessus (bandeau du haut demandé avant), réduit à 3 items sur téléphone pour garder le jeu actif visible.

## D18 — Objectifs : un descripteur par jeu, slot_data d'abord (2026-10-12, demandé par Romain)
Les options d'objectif viennent du slot_data quand le monde les y met (c'est ce que le générateur a vraiment utilisé :
sur la vraie room, Jak and Daxter a 20/45/72 cellules et KH2 35 Lucky Emblems, alors que les yamls du dossier disent
25/50/80 et 40), sinon du yaml du joueur (valeurs aléatoires ignorées). L'avancement ne vient que de ce qu'un tracker
voit : items reçus (Lucky Emblems, Power Stars, badges…), locations cochées (boss de donjon, arbres d'Ori, decks
gagnés à Balatro…). Les étapes qui sont des événements du jeu sans location (boss final de SM64, récompenses de
donjon d'OoT, victoires de Slay the Spire) sont marquées « invisibles » ; la dernière étape, le but lui-même, vient
du statut envoyé par le serveur. Le % de la page est une estimation (moyenne des compteurs et des étapes visibles).
Un jeu sans descripteur affiche seulement « But atteint » ou non.

## D19 — Yaml d'une autre room : Celeste suit le slot_data, et l'app le signale pour les autres jeux (2026-10-13)
Romain a changé de room sans changer ses yamls (`config/players/romain/`). Les jeux régénérés depuis le yaml prenaient
donc les options de l'ancienne room ; pour Celeste (roomsanity activé dans la nouvelle), les ~680 locations de salles
manquaient au monde recalculé et la logique affichait 2 checks. Deux changements :
- **Celeste** : un adaptateur applique les options de logique que `fill_slot_data` copie telles quelles, la zone du
  but (envoyée par niveau, « 9a ») et le nombre de fraises requises (calculé dans `create_items`). Validé 9/9 avec
  l'ancien yaml contre des seeds aux bonnes options, et 6/6 sans régression avec le yaml de la seed.
- **Tous les jeux** : si le serveur annonce des locations du slot que le monde recalculé n'a pas, la carte le dit
  (« N locations du slot manquent au monde recalculé… »). Aucune fausse alerte sur les 66 slots des seeds de test.
  Sur la vraie room au 2026-10-13 : SM64, Odyssey, Ori WotW, TWW HD et AEMinecraft ont des yamls d'une autre room.
Pas de « slot_data prioritaire » générique : un nom d'option peut avoir un autre sens dans le slot_data (Ori WotW,
`bonus`, différent du yaml sur une seed pourtant cohérente). La vraie solution reste d'importer les yamls de la room.

## D20 — Historique : heure et contenu des checks faits (2026-10-14, demandé par Romain)
- **Heure d'un check** : celle où l'app le voit fait (le serveur ne date rien), mêmes règles que les items (D11) :
  inconnue pour les checks faits avant que l'app note les heures, intervalle pour ceux faits pendant une absence.
- **Contenu d'un check fait** : demandé au serveur avec `LocationScouts`, autorisé par Romain avec possibilité de le
  couper (option « Demander au serveur le contenu des checks déjà faits », `scout_checked`, activée par défaut).
  Pas de spoiler : seulement des locations **déjà faites** (l'item est déjà parti), et `create_as_hint: 0` (rien
  n'est créé ni montré aux autres joueurs). Le garde-fou est dans `SlotTracker._send` : toute autre forme est refusée.
  Le résultat est gardé en base (`check_log`) : une location n'est demandée qu'une fois. Sans l'option, le contenu
  vient des items reçus par les slots suivis (ce qui part chez un joueur non suivi reste inconnu).
- **Jeu actif choisi à la main** (sur l'appareil, `localStorage`) : « Définir comme actif » épingle un jeu ; les autres
  ne restent actifs que s'ils ont un check plus récent que ce choix. « Plus actif » retire un jeu jusqu'à son prochain
  check. En mode compact, un clic dans la liste épingle le jeu : une seule notion de « jeu actif ».
- **Mode compact** : la carte du jeu actif (choisi, sinon le check le plus récent, sinon le premier de la liste) à
  gauche, la liste de tous les jeux à droite (nom, barre, en logique, restants).
- Fond étoilé et thèmes : après les maquettes de Claude Design (`docs/design/BRIEF-claude-design.md`).

## D21 — v2 « Observatoire » servie à côté de la v1 sous /v2 (2026-10-15, demandé par Romain)
v2 servie à côté de la v1 sous `/v2` : un seul point d'entrée qui charge l'une ou l'autre (code et CSS séparés), mêmes store et API, préférences `amt-v2-*` séparées, choix du jeu actif partagé. Thèmes définis en TS (`src/v2/lib/tokens.ts`) et appliqués en variables CSS pour tester le contraste.
