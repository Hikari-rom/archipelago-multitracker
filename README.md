# Archipelago Multitracker

Une seule page web pour suivre tous tes jeux d'un multiworld [Archipelago](https://archipelago.gg) (0.6.7) et répondre,
jeu par jeu, à la question : **« est-ce que je peux avancer dans ce jeu, au niveau des checks, sans le lancer ? »**

Pour chaque slot :
- **Niveau 1 (tous les jeux)** : checks faits / total, items reçus, **nouveaux items depuis ta dernière visite**
  (bouton « Marquer comme vu »), hints dans les deux sens, but atteint.
- **Niveau 2 (logique)** : nombre de **checks en logique** avec les items reçus et leur liste, les locations hintées
  mises en avant. La logique vient d'[Universal Tracker](https://github.com/FarisTheAncient/Archipelago/tree/tracker)
  piloté en headless. Jeux validés : voir [`docs/COMPAT.md`](docs/COMPAT.md).

Et aussi : fil des derniers items reçus, tri des jeux (conseillé, nombre ou % de checks en logique), jeu en cours mis
en avant, page **Historique** (checks envoyés et items reçus, jour par jour, avec leur heure et leur contenu), page
**Objectifs** (le but de chaque jeu et où tu en es), page **Configuration** (room, yamls, slots) et page **Journal**
(logs en direct).

Deux interfaces, mêmes données :
- **v2 « Observatoire »** sur `/` (l'interface par défaut ; l'ancienne adresse `/v2` y mène aussi) : affichage Cartes ou Focus, thèmes Nuit et Plan, téléphone. Un jeu en **BK**
  (plus rien en logique) est en rouge, un jeu **terminé** en or. Page **Room complète** en option (menu Plus) :
  classement, qui joue, activité et fil des checks de toute la room.
- **v1** sur `/v1` : l'interface d'origine (menu Plus → « Revenir à la v1 »).

Sur Linux (testé sur Raspberry Pi), ou sur Windows avec la [version portable](#windows--version-portable).

**Zéro spoiler** : l'app ne sait que ce que sait un tracker classique (items reçus, checks, hints, `slot_data`,
datapackage et tes yamls). Elle se connecte en **lecture seule** (tag `Tracker`) : elle n'envoie jamais de check,
de message ni de demande de hint.

## Windows : version portable

Pas besoin de WSL : un zip contient tout (Python, Archipelago 0.6.7, les apworlds, l'interface). Windows 10 ou 11,
64 bits.

1. Télécharger `ArchipelagoMultitracker-windows-x64.zip` depuis les
   [releases](https://github.com/Hikari-rom/archipelago-multitracker/releases), ou depuis le dernier run réussi de
   [Windows portable](https://github.com/Hikari-rom/archipelago-multitracker/actions/workflows/windows.yml) (artifact).
2. Dézipper (pas dans « Program Files »), double-cliquer sur `Multitracker.exe`. SmartScreen prévient que l'exe n'est
   pas signé : « Informations complémentaires » → « Exécuter quand même ».
3. Le navigateur s'ouvre sur http://127.0.0.1:42753 : page Configuration, comme ci-dessous à partir de
   [6. Choisir les slots](#6-choisir-les-slots).

La fenêtre noire doit rester ouverte (la fermer arrête l'app). `Multitracker.exe --host 0.0.0.0` ouvre l'app au
réseau local, `--port N` change le port. Le mode d'emploi complet est dans `LISEZMOI.txt`, dans le zip (mise à jour,
emplacement des données). Construction : `.github/workflows/windows.yml` et `scripts/windows/` (D23).

Mises à jour (à partir de la v0.2.0) : un bandeau signale une nouvelle release ; page Configuration → « Mises à jour »
→ « Mettre à jour ». L'app télécharge le zip, `Multitracker.exe` remplace les fichiers et redémarre, en gardant
`config\` et `data\` (l'ancienne version revient si la nouvelle ne démarre pas). Sans l'interface :
`Multitracker.exe --update` (D25).

## Installation en local, pas à pas

L'installation ne demande pas les droits root (une fois les prérequis présents) et n'écrit rien hors du dossier du
projet : Archipelago, l'environnement Python, les apworlds et les modules Node restent dedans. Pour tout
désinstaller, il suffit de supprimer le dossier (voir [Désinstaller](#désinstaller)).

### 1. Prérequis

| | |
|---|---|
| **Système** | Linux. Testé sur un Raspberry Pi 5 (8 Go) sous Raspberry Pi OS / Debian 13, 64 bits. Une autre distribution Linux (x86_64 ou ARM 64 bits) devrait marcher. macOS n'est pas testé ; pour Windows, voir la [version portable](#windows--version-portable). |
| **Python** | 3.11, 3.12 ou 3.13, avec le module `venv`. Pas 3.14 : le script d'installation le refuse (non testé avec Archipelago 0.6.7). |
| **Node.js** | 20 ou plus récent, avec `npm` (pour construire l'interface). |
| **Outils** | `git`, `curl`, `ss` (paquet `iproute2`) et `flock` (paquet `util-linux`), présents d'office sur Debian. |
| **Disque** | ~400 Mo une fois installé (dont 200 Mo de modules Node), plus les données de l'app (quelques Mo). |
| **Mémoire** | 2 Go libres conseillés : le moteur de logique régénère les mondes des jeux dans un process à part. |
| **Réseau** | Accès à GitHub (Archipelago, apworlds), PyPI et npm pendant l'installation ; à la room ensuite. |

Vérifier ce qui est déjà là :

```bash
python3 --version          # 3.11 à 3.13
python3 -m venv --help > /dev/null && echo "venv OK"
node --version             # v20 ou plus
git --version
```

Installer ce qui manque, sur Debian / Ubuntu / Raspberry Pi OS :

```bash
sudo apt install git curl python3 python3-venv
```

Pour Node, la version des dépôts Debian est parfois trop ancienne. Sans root, [nvm](https://github.com/nvm-sh/nvm)
l'installe dans ton dossier personnel (c'est ce qui est utilisé sur le Pi) :

```bash
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.3/install.sh | bash
# ferme et rouvre le terminal, puis :
nvm install 24
```

Si ta distribution n'a qu'un Python 3.14 ou plus récent, installe un 3.13 à côté (par exemple avec
[uv](https://docs.astral.sh/uv/) : `uv python install 3.13`) et indique-le au script d'installation avec
`PYTHON=/chemin/vers/python3.13` (étape 3).

### 2. Récupérer le code

Le dépôt est public : pas besoin de compte GitHub.

```bash
git clone https://github.com/Hikari-rom/archipelago-multitracker.git
cd archipelago-multitracker
```

### 3. Installer

```bash
bash scripts/bootstrap.sh
# ou, pour choisir l'interpréteur : PYTHON=/usr/bin/python3.13 bash scripts/bootstrap.sh
```

Compter 1 à 2 minutes sur un Pi 5 avec une bonne connexion (surtout des téléchargements), plus si pip et npm
n'ont encore rien en cache. Le script peut être relancé sans risque : il ne refait
que ce qui manque. Il :
1. clone Archipelago 0.6.7 dans `vendor/Archipelago` ;
2. crée l'environnement Python `.venv/` et y installe les dépendances d'Archipelago (sans l'interface graphique kivy)
   et celles de l'app ;
3. télécharge les apworlds des jeux et Universal Tracker dans `vendor/Archipelago/custom_worlds/`, aux versions
   notées dans `config/apworlds.lock.yaml` (vérifiées par sha256) ;
4. installe les modules Node de `frontend/` et construit l'interface (`frontend/dist/`).

Il se termine par `== Terminé`. Pour vérifier que tous les apworlds se chargent :

```bash
.venv/bin/python scripts/check_apworlds.py   # ~6 min sur un Pi 5 : il charge chaque monde
```

Chaque ligne doit commencer par `OK`.

Les téléchargements d'apworlds passent par l'API GitHub, limitée à 60 requêtes par heure sans compte : c'est assez
pour une installation. Si tu relances souvent, exporte un jeton (`GITHUB_TOKEN=…`) ou connecte `gh`, que le script
utilise tout seul.

### 4. Créer le fichier de configuration

L'app a besoin d'un fichier `config/room.yaml` pour démarrer. Il n'est jamais commité, puisqu'il contiendra le mot de
passe de la room. Pars de l'exemple :

```bash
cp config/room.example.yaml config/room.yaml
```

Tu peux le laisser tel quel : le lien de la room et le mot de passe se règlent dans l'interface (étape 6). Ou bien
remplis tout de suite `room_url` (la page `https://archipelago.gg/room/…`) et `password`. Pour un serveur hors
archipelago.gg, remplace `room_url` par `server: "hôte:port"`.

### 5. Lancer

```bash
scripts/app.sh start
```

L'app tourne en arrière-plan et répond sur `http://<ip-de-la-machine>:42753` (`http://localhost:42753` depuis la
machine elle-même). Les autres commandes :

```bash
scripts/app.sh status    # lancée ou pas
scripts/app.sh logs      # suivre le log (data/logs/app.log), Ctrl+C pour sortir
scripts/app.sh restart
scripts/app.sh stop
```

Variables utiles : `MT_PORT=8080 scripts/app.sh start` pour un autre port, `MT_HOST=127.0.0.1` pour n'accepter que
la machine elle-même (voir [Sécurité](#accès-depuis-un-autre-appareil-et-sécurité)).

### 6. Choisir les slots

Ouvre l'app : tant qu'aucun slot n'est suivi, elle affiche directement la page **Configuration** (détails dans
[Configurer la room](#configurer-la-room)). Avec le fichier d'exemple, elle signale « room introuvable » : c'est
normal.
1. colle le lien de la room, « Découvrir les slots », mets le mot de passe et « Tester la connexion » ;
2. importe tes yamls (« Importer des yamls ») puis « Associer automatiquement » : certains jeux en ont besoin pour
   calculer la logique ;
3. coche tes slots et « Enregistrer » (en haut de la page).

Le tableau de bord se remplit dès que l'app est connectée. Si la room dort, il affiche « Room endormie » : l'app se
reconnecte toute seule quand quelqu'un la réveille, ou tout de suite avec le bouton « Réveiller maintenant ».

### Mettre à jour l'app

Depuis l'interface : page Configuration → « Mises à jour » → « Vérifier maintenant », puis « Mettre à jour » (un
bandeau le propose aussi ; l'app vérifie une fois par jour). Ou à la main :

```bash
bash scripts/update.sh
```

Le script suit la branche `main` : `git merge --ff-only` (tes modifications non commitées sont mises de côté puis
remises), réinstalle seulement ce qui a changé (dépendances, apworlds du lock, paquets npm), reconstruit l'interface
et redémarre l'app si son code a changé. Il s'arrête sans rien toucher si le dépôt a des commits locaux non poussés
ou n'est pas sur `main`. Journal : `data/logs/update.log` (D25).

Ta configuration (`config/room.yaml`, `config/players/`) et tes données (`data/` : dernière visite, historique) sont
gardées.

### Désinstaller

```bash
scripts/app.sh stop
systemctl --user disable --now multitracker   # seulement si tu as installé le service (plus bas)
rm ~/.config/systemd/user/multitracker.service  # idem
cd .. && rm -rf archipelago-multitracker
```

Node installé avec nvm reste dans `~/.nvm` ; Python et ses paquets étaient dans le dossier supprimé.

### En cas de problème

| Symptôme | Cause et solution |
|---|---|
| `Python 3.11 à 3.13 requis` | Mauvaise version de Python : relance avec `PYTHON=/chemin/vers/python3.13 bash scripts/bootstrap.sh`. |
| `No module named venv` / `ensurepip is not available` | Il manque `python3-venv` (`sudo apt install python3-venv`). Supprime ensuite le dossier `.venv/` à moitié créé avant de relancer. |
| `npm: command not found` | Node n'est pas installé, ou nvm n'est pas chargé dans ce terminal (rouvre-le). |
| `vendor/Archipelago est sur '…', attendu 0.6.7` | Le dossier `vendor/Archipelago` vient d'ailleurs : supprime-le et relance le bootstrap. |
| Erreur `403` / `rate limit` pendant les apworlds | Limite de l'API GitHub atteinte : attends une heure, ou exporte `GITHUB_TOKEN`. |
| `✗ config/room.yaml manquant` | Étape 4 pas faite. |
| `✗ le port 42753 est déjà utilisé` | Une autre instance tourne (le service systemd ?), ou choisis un autre port avec `MT_PORT`. |
| `✗ l'app s'est arrêtée` | Les 20 dernières lignes du log sont affichées ; le log complet est dans `data/logs/app.log`. |
| Avertissements `_speedups not available` et `7 not loaded (missing dependencies)` dans le log | Sans effet : ce sont des jeux d'Archipelago que l'app n'utilise pas, et une optimisation facultative. |
| La page ne s'ouvre pas depuis un autre appareil | Pare-feu de la machine, ou app lancée avec `MT_HOST=127.0.0.1`. |
| « Room endormie » en permanence | Personne n'a ouvert la room depuis plus de 2 h : bouton « Réveiller maintenant », ou ouvre la page de la room. |
| Un jeu sans « en logique » | Logique pas validée pour ce jeu, ou yaml manquant : le diagnostic est sous le slot dans Configuration, et la liste des jeux dans [`docs/COMPAT.md`](docs/COMPAT.md). |

Le log est aussi consultable dans l'app, page **Journal**.

## Configurer la room

Le plus simple : ouvre l'app, bouton **Configuration**.
1. **Room** : colle le lien `https://archipelago.gg/room/…` puis « Découvrir les slots ». L'app affiche le nombre de
   slots et de jeux, le port, et si la room dort (bouton « Réveiller la room »). Mets le mot de passe et
   « Tester la connexion » (une connexion d'essai en lecture seule).
2. **Yamls** : « Importer des yamls » (un ou plusieurs fichiers, multi-documents acceptés) les range dans
   `config/players/` (gitignoré, sauf `config/players/romain/` : les yamls de Romain pour sa room). « Associer automatiquement » donne à chaque slot le yaml qui a le même `name`
   (avec `{player}`/`{number}` gérés) et le même jeu.
3. **Slots** : recherche, filtre par jeu, « Cocher les affichés », « Cocher ceux qui ont un yaml ». Sous chaque slot
   coché, un diagnostic : pas d'apworld (suivi des checks seulement), logique pas encore validée, yaml nécessaire mais
   absent, yaml d'un autre jeu ou d'un autre nom.
4. **Enregistrer** (barre en haut de la page) : l'ancienne configuration est gardée (`config/room.yaml.bak`) et
   « Restaurer la configuration précédente » la remet.

Deux réglages de la carte Room :
- **Demander au serveur le contenu des checks déjà faits** (activé par défaut) : pour l'Historique, l'app demande ce
  que contenaient tes checks **déjà faits**, sans créer de hint (rien n'est dévoilé, D20).
- **Tableau de bord de la room complète** (désactivé par défaut) : une connexion d'écoute en plus, en lecture seule,
  pour la page « Room complète » de la v2. Les checks de toute la room sont écrits dans `data/room_feed/` ; ceux faits
  pendant que l'app était arrêtée sont rattrapés depuis le site (sans leur heure exacte, D22). Les noms de joueurs se
  corrigent dans `config/room_players.yaml` (`slot: joueur`).

Lien direct pour partager la page pré-remplie : `http://<ip-du-pi>:42753/#config?room=<lien de la room>`.

**Room endormie** : une room archipelago.gg s'arrête après 2 h sans activité et change souvent de port au réveil.
L'app suit le port tout seul. Par défaut elle ne réveille **pas** la room (elle ne la garde donc pas allumée) : le
tableau de bord affiche « Room endormie » avec un bouton « Réveiller maintenant », et l'app se reconnecte dès que
quelqu'un a ouvert la room. La case « Réveiller automatiquement la room » change ce comportement.

À la main, `config/room.yaml` (copie de `config/room.example.yaml`, jamais commité) :

```yaml
room_url: "https://archipelago.gg/room/AbC…"   # ou server: "host:port" pour un serveur hors archipelago.gg
password: "le mot de passe"
wake_room: false
scout_checked: true      # contenu des checks déjà faits (Historique)
room_dashboard: false    # page « Room complète »
slots:
  - name: "Romain_Celeste"                # nom exact du slot
    game: "Celeste (Open World)"          # optionnel (le serveur le donne)
    yaml: "config/players/celeste.yaml"   # ton yaml pour ce jeu : nécessaire à la logique de certains jeux
```

- Les jeux qui savent se régénérer depuis le `slot_data` (colonne « UT sans yaml » de `COMPAT.md`) n'ont pas besoin
  du yaml ; les autres sont marqués `needs_yaml: true` dans `config/apworlds.yaml`.
- Si ton yaml contient des options aléatoires (`random`, poids), l'app reprend la valeur réellement tirée quand
  le jeu la met dans son `slot_data`, sinon la carte prévient que la logique peut être approximative.

## Démarrage automatique

Pour que l'app démarre avec la machine, un service systemd *utilisateur* est fourni (`deploy/multitracker.service`).
Il contient le chemin du projet sur le Pi de Romain ; la commande `sed` ci-dessous le remplace par le tien :

```bash
scripts/app.sh stop        # le service et scripts/app.sh utilisent le même port : jamais les deux à la fois
mkdir -p ~/.config/systemd/user
sed "s#/home/romain/archipelago-multitracker#$PWD#g" deploy/multitracker.service > ~/.config/systemd/user/multitracker.service
systemctl --user daemon-reload && systemctl --user enable --now multitracker
sudo loginctl enable-linger "$USER"   # une seule fois (root) : garder le service actif sans session ouverte
journalctl --user -u multitracker -f  # logs du service
```

Le service écoute sur le port 42753 de toutes les interfaces. Pour le désactiver :
`systemctl --user disable --now multitracker`.

## Accès depuis un autre appareil et sécurité

Depuis un téléphone ou un autre ordinateur du réseau : `http://<ip-de-la-machine>:42753` (avec Tailscale :
`http://<ip-tailscale-de-la-machine>:42753`). L'app écoute sur toutes les interfaces.

Derrière un reverse proxy (ex. `tailscale serve`) qui change l'en-tête `Host`, autorise son origine pour les
actions d'écriture : `MT_ALLOWED_ORIGINS=https://pi.ton-tailnet.ts.net scripts/app.sh restart`.

**Sécurité** : il n'y a pas d'authentification. Toute machine du réseau local (ou du tailnet) peut lire ta
progression, tes items et tes hints (jamais le mot de passe de la room). Pour limiter l'accès à la machine
elle-même : `MT_HOST=127.0.0.1 scripts/app.sh start`.

## Mettre à jour un apworld

Les sources sont dans [`config/apworlds.yaml`](config/apworlds.yaml) (dépôt GitHub, tag `latest` ou épinglé,
motif de l'asset). Après modification :

```bash
.venv/bin/python scripts/fetch_apworlds.py            # télécharge ce qui manque (versions du lock)
.venv/bin/python scripts/fetch_apworlds.py --update   # reprend la dernière release des entrées en "latest"
.venv/bin/python scripts/check_apworlds.py            # vérifie que tout se charge
scripts/app.sh restart
```

Les versions réellement téléchargées (et leur sha256) sont dans `config/apworlds.lock.yaml`.
La logique d'un jeu ne s'affiche que s'il a `logic: true` dans `apworlds.yaml` (mis après validation, voir
`docs/COMPAT.md`). Tu peux l'activer à la main pour un jeu non validé, à tes risques.

## Développement et tests

```bash
scripts/test.sh -q                      # backend (PYTHONHASHSEED=0) : niveau 1, logique, env de test
cd frontend && npm test && npm run build
```

Environnement de test (jamais utilisé par l'app) dans `scripts/testenv/` : génération de seeds sans ROM, serveur local
sur `127.0.0.1:38281-38291`, bot qui envoie des checks, campagnes de validation de la logique
(`validate_logic.py`, `campaign.sh`). Seul ce code de test lit les spoilers et le multidata.

Version Windows : `scripts/windows/` (lanceur, `Multitracker.exe`, assemblage du dossier), construite par
`.github/workflows/windows.yml` sur GitHub Actions (lancement à la main, ou release sur un tag `v*`, D23).

Docs : [`docs/API.md`](docs/API.md) (API REST + SSE), [`docs/COMPAT.md`](docs/COMPAT.md) (jeux),
[`DECISIONS.md`](DECISIONS.md), [`PROGRESS.md`](PROGRESS.md).

## Crédits et licences

- [Archipelago](https://github.com/ArchipelagoMW/Archipelago) (MIT), cloné dans `vendor/` au bootstrap.
- [Universal Tracker](https://github.com/FarisTheAncient/Archipelago/tree/tracker) de FarisTheAncient (MIT, licence du
  dépôt), téléchargé comme apworld et utilisé comme bibliothèque.
- Les apworlds des jeux appartiennent à leurs auteurs respectifs (liens dans `config/apworlds.yaml`).
- Version Windows : CPython de [python-build-standalone](https://github.com/astral-sh/python-build-standalone)
  (licence PSF et licences de ses composants), installé avec [uv](https://github.com/astral-sh/uv).
