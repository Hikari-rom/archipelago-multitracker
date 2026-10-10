# Brief de nuit — Archipelago Multitracker

Tu travailles seul cette nuit sur le Raspberry Pi de Romain. Personne ne répondra à tes questions avant demain matin : quand tu hésites, prends la décision la plus raisonnable, note-la dans `DECISIONS.md` et continue. Lis ce brief en entier avant de commencer.

---

## 1. Mission

Romain participe à un multiworld **Archipelago** (room hébergée sur archipelago.gg, version **0.6.7**) dans lequel il joue **22 jeux**. Chaque jeu a son propre tracker, et jongler entre 22 trackers est ingérable.

Construis une **app web unique** qui répond, pour chacun de ses jeux, à la question :

> **« Est-ce que je peux avancer dans ce jeu, au niveau des checks, sans avoir à le lancer ? »**

Concrètement, pour chaque slot :

- **Niveau 1, générique et valable pour tous les jeux :** checks faits / total, checks restants, items reçus, **nouveaux items depuis la dernière visite** (avec un bouton « Marquer comme vu »), hints, état « but atteint ».
- **Niveau 2, la logique :** **nombre de checks en logique** avec les items actuellement reçus, plus la **liste dépliable** de ces locations.
- **Hints, dans les deux sens :** les items de Romain placés chez les autres (« ton X est à telle location dans tel monde ») et les locations de ses jeux qui contiennent un item hinté pour quelqu'un. Ces dernières doivent être mises en évidence quand elles sont en logique.
- Un **tableau de bord** qui place en tête les jeux où il y a quelque chose à faire.

### Règle absolue : zéro spoiler

L'outil ne doit **jamais** en savoir plus que Romain : items reçus, checks faits, hints obtenus, options de ses propres yamls, et données envoyées par le serveur à la connexion (`slot_data`, datapackage). C'est exactement ce que fait un tracker classique.

- Le code produit ne lit **jamais** de spoiler log, de `.archipelago`, de multidata ni de zip de génération.
- Les seeds de test que tu génères toi-même ont un spoiler. **Seul le code de test** (dossier `tests/`, scripts `scripts/testenv/`) peut s'en servir, pour vérifier les résultats. Aucun import de ce code depuis l'app.
- L'app est **en lecture seule vis-à-vis du serveur**. Elle n'envoie jamais `LocationChecks`, `StatusUpdate`, `Say`, de demande de hint, ni aucune écriture en data storage visible des autres. Seul le bot de test (en local) a le droit d'envoyer des checks.

---

## 2. Cadre de la session

- **Durée :** tu as toute la session jusqu'au rate limit. Va le plus loin possible **sans sacrifier la qualité**. Un jalon n'est terminé que quand ses tests passent et qu'il a été relu.
- **La coupure peut tomber n'importe quand.** Tout doit donc être reprenable : commit et push à chaque étape stable, et `PROGRESS.md` à jour à chaque jalon (voir §8).
- **Un hook Stop t'empêche de t'arrêter** tant qu'il reste des tâches `- [ ]` dans `BACKLOG.md`. Si une tâche est réellement bloquée, marque-la `- [!]` avec la raison et passe à la suivante. Ne coche jamais une tâche non terminée pour pouvoir t'arrêter.
- Quand le backlog des jalons est vide, passe aux bonus (§7, M8), puis à l'amélioration de la qualité (tests, robustesse, UX).
- **Langues :** code, commentaires, commits et noms techniques en anglais. Interface en **français**. Les termes issus des apworlds (noms d'items, de locations, de jeux, d'options) restent **tels quels, sans traduction**. Les docs du repo (`README`, `PROGRESS`…) sont en français.

---

## 3. Règles de sécurité sur le Pi (non négociables)

Le Pi est la machine de dev de Romain et héberge d'autres projets.

- **Pas de `sudo`**, pas d'`apt`, pas de `systemctl` (c'est bloqué de toute façon). Si une dépendance système manque, note la commande exacte dans `PROGRESS.md`, section « À faire par Romain », et contourne-la ou passe à autre chose.
- **Ne désinstalle rien.** Aucune installation globale : pas de `npm -g`, pas de `pip --user` ni `--break-system-packages`. Tout le Python va dans `.venv/` du repo et tout le Node dans `node_modules/`.
- **Ne modifie rien en dehors du repo** : dotfiles (`~/.zshrc`, `~/.bashrc`…), `~/.claude`, autres projets, crontab. Exception : les caches standard de pip et npm.
- Le **projet Enigmatik** voisin (dossier frère du repo) est en **lecture seule**. Tu peux l'inspecter pour copier sa façon d'exposer l'app (§6), sans jamais y écrire.
- **Ne tue que les processus que tu as lancés.** Enregistre leurs PID dans `.run/` (gitignoré).
- **Ports :** l'app sur **42753**. Les serveurs Archipelago de test sur **127.0.0.1 uniquement**, ports 38281 à 38290.
- **Jamais de ROM, d'ISO ni de fichiers de jeu**, ni téléchargés ni commités. Génère toujours avec `--skip_output` (ou l'équivalent) pour ne pas avoir besoin de ROM.
- **Rien de secret dans git** : le mot de passe de la room va dans `config/room.yaml` (gitignoré). Seul `config/room.example.yaml` est commité.
- Surveille la RAM (8 Go) et le disque (`df -h`). Pas plus de 2 ou 3 tâches lourdes en parallèle (générations, builds).

---

## 4. Contexte technique

- **Matériel :** Raspberry Pi 5, 8 Go, Raspberry Pi OS 64 bits (aarch64), Python 3.11+, Node présent, pas de Docker.
- **Archipelago 0.6.7** depuis les sources : `git clone --branch 0.6.7 https://github.com/ArchipelagoMW/Archipelago vendor/Archipelago` (gitignoré). Sous Linux, AP accepte Python 3.11.0 à 3.13.x.
  - Pas besoin de GUI. `kivy`/`kivymd` (GUI) et `Pymem` (Windows) risquent d'échouer sur ARM. Installe les requirements **sans eux** si nécessaire, et stubbe ou évite les imports GUI.
  - Les apworlds custom vont dans `vendor/Archipelago/custom_worlds/`.
  - `Generate.py`, `MultiServer.py` et la lib `NetUtils`/`CommonClient` doivent tourner en headless.
- **Universal Tracker (UT)** fait déjà exactement le calcul de logique côté client et sans spoiler. Il régénère le monde du joueur à partir de son yaml et/ou de `slot_data`, puis calcule les locations accessibles avec les items reçus.
  - Repo : `https://github.com/FarisTheAncient/Archipelago`, branche `tracker`, releases `Tracker_v*` qui fournissent `tracker.apworld`.
  - Choisis la release compatible avec 0.6.7. **Essaie d'abord de le piloter en headless comme une bibliothèque**, sans GUI. Si c'est impossible, réimplémente la même approche (régénération mono-joueur, puis sweep `CollectionState`) en t'inspirant de son code.
  - Vérifie et respecte sa licence, et note-la dans `DECISIONS.md`.
- **Protocole réseau :** archipelago.gg utilise `wss://` (TLS). Le serveur local de test utilise `ws://`. Gère les deux, en essayant `wss` puis `ws` comme les clients officiels. Une connexion par slot avec le tag `Tracker`. Les hints se lisent dans le data storage (`_read_hints_{team}_{slot}` + `SetNotify`). Les noms d'items et de locations viennent du datapackage.

---

## 5. Architecture cible (ajustable si tu as une bonne raison, à noter dans `DECISIONS.md`)

```
backend/   Python 3.11, FastAPI + uvicorn, dans .venv
  - une connexion AP par slot configuré (tracker, lecture seule)
  - moteur de logique (UT ou équivalent), calcul en cache, recalcul (debounce) à chaque item reçu
  - SQLite pour l'état local (« dernière visite » par slot, cache)
  - API REST + SSE pour pousser les mises à jour au front
  - en prod, sert aussi le front buildé
frontend/  Vue 3 + Vite + TypeScript
config/
  room.example.yaml     (commité)   room.yaml (gitignoré)
  apworlds.yaml         jeu → source (repo GitHub, tag/version, motif d'asset), modifiable à la main
  apworlds.lock.yaml    versions effectivement résolues et téléchargées
  players/              yamls de Romain (pour la logique)
scripts/
  bootstrap.sh          idempotent : clone AP 0.6.7, venv, deps, apworlds, UT
  fetch_apworlds.py     lit apworlds.yaml, télécharge, remplit le lock
  testenv/              génération de multiworlds de test, serveur local, bot
tests/                  pytest (+ vitest côté front)
```

Format proposé pour `config/room.yaml` :

```yaml
server: "archipelago.gg:38281"
password: ""
slots:
  - name: "Romain_Celeste"
    game: "Celeste (Open World)"
    yaml: "config/players/celeste.yaml"   # optionnel, utile pour la logique
```

La découverte automatique des slots d'une room est un bonus (M8). Pour l'instant, le fichier de config suffit.

### UX (front)

- Une carte par jeu : nom du jeu et du slot, état de connexion, checks faits/total, un badge **« Tu peux avancer : N checks en logique »** (vert), « Rien en logique pour l'instant » (neutre) ou « Logique indisponible pour ce jeu » (dans ce cas, le compteur de nouveaux items devient le signal principal).
- Une liste dépliable des locations en logique, avec les locations hintées mises en avant.
- Les nouveaux items depuis la dernière visite, avec un bouton « Marquer comme vu ».
- Les hints de la carte.
- Tri : jeux avec checks en logique ou nouveautés d'abord, jeux terminés à la fin.
- Lisible **sur mobile** (Romain y accédera depuis son téléphone via Tailscale), thème clair et sombre, sobre, sans dépendance UI lourde.
- Mise à jour en direct via SSE.

---

## 6. Les jeux et leurs apworlds

Les apworlds non officiels doivent être **modulables** : la source et la version sont dans `config/apworlds.yaml`, modifiables à la main. Par défaut, prends la **dernière release** de chaque repo, sauf si une version est précisée ci-dessous.

| Jeu | Source | Priorité logique |
|---|---|---|
| Celeste (Open World) | core AP 0.6.7 | **1** |
| Kingdom Hearts 2 | core | **1** |
| Jak and Daxter: The Precursor Legacy | core | **1** |
| The Wind Waker HD | github.com/Teotia444/twwhd-apworld | **1** |
| Super Mario 64 (sm64ex) | core | 2 |
| Super Mario Odyssey | github.com/mdietz94/smo_archipelago **tag v1.5.3** | 2 |
| Ori and the Blind Forest | github.com/c-ostic/Archipelago | 2 |
| Ori and the Will of the Wisps | github.com/Satisha10/APwotw_release | 2 |
| Balatro | github.com/BurndiL/BalatroAP | 2 |
| Slay the Spire | github.com/cjmang/StS-AP-World | 2 |
| Kingdom Hearts: Birth by Sleep Final Mix | github.com/gaithernOrg/ArchipelagoKHBBS | 3 |
| Jak 3 | github.com/Blake645/Archipelago | 3 |
| The Legend of Zelda: Phantom Hourglass | github.com/carrotinator/Archipelago **tag ph-v0.10.1** | 3 |
| Pokémon Platinum | github.com/ljtpetersen/platinum_archipelago | 3 |
| Pokémon Black and White | github.com/BlastSlimey/PokemonBWAP | 3 |
| PokéPark Wii: Pikachu's Adventure | github.com/Mekurushi/Archipelago_Pokepark | 3 |
| Ratchet & Clank 2 | github.com/evilwb/APRac2 | 3 |
| Ratchet & Clank 3 | github.com/Taoshix/Archipelago-RaC3 | 3 |
| AEMinecraft | github.com/KuroLynx/AEMinecraft **v0.6.2** | 3 |
| The Binding of Isaac: Repentance | github.com/NaveTK/Archipelago | 3 |
| Mario Kart Wii | github.com/toent/Archipelago-MKWii | 3 |
| The Legend of Zelda: Ocarina of Time | core | **en dernier** |

Le niveau 1 doit marcher pour **tous** les jeux, puisqu'il est générique. Pour le niveau 2, suis les priorités, en ordonnant les niveaux 2 et 3 par facilité une fois l'étude de compatibilité faite. OoT passe en dernier. Un jeu dont la logique ne fonctionne pas reste en niveau 1 avec le badge « Logique indisponible ».

Tiens `docs/COMPAT.md` à jour, avec une ligne par jeu et les colonnes : version apworld · se charge sur 0.6.7 · génère en headless · niveau 1 OK · UT sans yaml · UT avec yaml · validé par test · notes.

---

## 7. Jalons

Chaque jalon se termine par : tests verts, relecture par un sous-agent neuf (§9), mise à jour de `PROGRESS.md` / `BACKLOG.md` / `COMPAT.md`, commit, push, notification (§10).

**M0 : prise en main (rapide).** Inspecte le Pi en lecture seule : versions, RAM, disque, port 42753 libre, et le dossier Enigmatik voisin pour voir comment il est exposé (Tailscale serve ? reverse proxy ? bind sur l'IP Tailscale ? service user ?). Crée `BACKLOG.md` (tous les jalons découpés en tâches), `PROGRESS.md`, `DECISIONS.md`, `.gitignore` et le squelette. Commit et push.

**M1 : Archipelago headless sur le Pi.** `scripts/bootstrap.sh` idempotent : AP 0.6.7, venv, deps sans GUI, `fetch_apworlds.py` + lock, UT. Vérifie que chaque apworld se charge (étude de compatibilité, à paralléliser avec des sous-agents Haiku pour la lecture des repos et des releases). Première version de `COMPAT.md`.

**M2 : environnement de test.** Des yamls de test pour les jeux de priorité 1 (générés depuis les templates d'options), et un script qui génère un multiworld de test (4 à 6 slots) avec `--skip_output`, puis l'héberge sur `127.0.0.1:38281` avec un mot de passe. Un **bot** (dans `scripts/testenv/`) qui se connecte comme un vrai client de jeu et envoie des checks.

**M3 : backend niveau 1.** Connexions tracker par slot, reconnexion automatique, datapackage, items reçus, checks, hints, but atteint, « dernière visite » en SQLite, API + SSE. Tests d'intégration contre le serveur local : le bot envoie des checks, l'API reflète l'état.

**M4 : front Vue.** Le tableau de bord du §5, servi par le backend. Vérifie le rendu (Playwright est disponible si besoin) en largeur mobile et desktop.

**M5 : logique, jeux de priorité 1** (Celeste, KH2, Jak and Daxter, TWW HD), via UT en headless ou une réimplémentation. Validation obligatoire, côté test uniquement :
  - **Comparaison de référence :** pour plusieurs états d'avancement (par exemple en rejouant les sphères du spoiler), compare les locations que l'outil dit en logique avec celles calculées par l'état de logique du multiworld complet de génération, pour les mêmes items reçus. Tout écart est corrigé ou documenté dans `COMPAT.md`.
  - **Bout en bout :** le bot ne coche **que** les locations que l'API annonce en logique, pour tous les slots du test, jusqu'à ce que la seed soit terminée. Si le bot se retrouve bloqué alors que la seed n'est pas finie, la logique sous-estime.

**M6 : déploiement sur le Pi**, port **42753**, exposé de la même façon qu'Enigmatik. Si ça demande `sudo` ou `systemctl`, prépare les fichiers et écris la commande exacte dans `PROGRESS.md`, section « À faire par Romain ». En attendant, lance l'app toi-même en arrière-plan pour qu'elle soit testable. `README.md` en français : installation, config de la room, lancement, mise à jour d'un apworld.

**M7 : étendre la logique** aux autres jeux (priorités 2 puis 3), OoT en dernier, avec la même validation qu'en M5, jeu par jeu.

**M8 : bonus**, une fois tout le reste fait ou bloqué :
  - découverte des slots d'une room à partir de son URL archipelago.gg, avec choix de l'utilisateur ;
  - support de plusieurs joueurs (le code doit déjà le permettre structurellement) ;
  - finitions UX ;
  - robustesse (coupures réseau, room qui redémarre) ;
  - performance de la régénération sur le Pi.

---

## 8. Fichiers de suivi (reprise dans une autre session)

- `BACKLOG.md` : tâches `- [ ]` ouvertes, `- [x]` faites, `- [!]` bloquées (avec la raison). Le hook Stop les compte.
- `PROGRESS.md` : en tête, l'**état actuel en 5 lignes**, puis le journal par jalon (fait, comment le vérifier, problèmes), « À faire par Romain » (actions sudo, infos manquantes), et « Prochaines étapes ».
- `DECISIONS.md` : chaque choix non trivial, avec sa raison et les alternatives écartées.
- `docs/COMPAT.md` : la matrice des jeux.

**Si tu démarres dans une nouvelle session :** lis ce brief, puis `PROGRESS.md`, `BACKLOG.md`, `DECISIONS.md` et `git log --oneline -30`. Vérifie l'état réel (tests, processus lancés), puis reprends à la première tâche ouverte.

---

## 9. Organisation et délégation (pour aller loin avant le rate limit)

Tu es l'**orchestrateur**. Garde ton contexte léger et délègue avec l'outil Agent et son paramètre `model` :

- **`haiku`** pour la lecture et la recherche : explorer le code d'AP ou d'UT et en résumer l'API utile, lire les README et releases des apworlds, faire des recherches web, trier des logs d'erreur, remplir les colonnes de `COMPAT.md`. Lance plusieurs agents en parallèle quand les tâches sont indépendantes (par exemple un agent par lot de 4 ou 5 apworlds).
- **`sonnet`** pour le code bien spécifié : un endpoint, un composant Vue, un script, des tests. Donne à chaque agent une spec précise, la liste des fichiers qu'il possède et le critère de fin (les tests à faire passer). Si plusieurs agents codent en parallèle, utilise `isolation: "worktree"` ou des périmètres de fichiers disjoints.
- **Toi (le modèle principal)** : l'architecture, l'intégration délicate (moteur de logique / UT, protocole), la vérification de ce que rendent les sous-agents, et les décisions.
- **Relecture de fin de jalon :** un sous-agent `sonnet` **neuf**, qui n'a pas écrit le code, relit le diff du jalon (bugs, règle zéro spoiler, lecture seule envers le serveur, sécurité Pi). Tu corriges ce qui est fondé.

Pour économiser :
- Ne `cat` pas de gros fichiers : utilise Grep et des lectures ciblées, ou délègue la lecture à Haiku.
- Ne relance pas une génération lourde quand un cache suffit.
- Écris les résultats dans des fichiers plutôt que de les faire transiter par ton contexte.

---

## 10. Notifications push (optionnelles)

`bash scripts/overnight/notify.sh "Titre" "Message"` envoie une notification sur le téléphone de Romain (ntfy) si elles sont configurées. Sinon, le script ne fait rien et sort sans erreur : appelle-le quand même, sans t'en soucier. Utilise-le :

- à la fin de chaque jalon (une ligne : ce qui marche, et comment le voir) ;
- quand tu tombes sur un blocage qui demande Romain (une action `sudo`, une info manquante) ;
- pas plus d'une notification toutes les 20 minutes environ, hors fin de jalon.

Les hooks envoient eux-mêmes la notification de fin de session et celle de coupure (rate limit ou erreur).

---

## 11. Définition du « fini » pour cette nuit

**Minimum attendu :** l'app tourne sur le Pi (port 42753) contre un multiworld de test local. Le niveau 1 marche pour n'importe quel jeu, la logique est validée pour Celeste, KH2, Jak and Daxter et TWW HD, et il suffit de remplir `config/room.yaml` pour la brancher sur la vraie room.

**Ensuite :** le plus possible de M7 et de M8, toujours testé et documenté.
