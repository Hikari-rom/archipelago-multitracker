# Archipelago Multitracker

Une seule page web pour suivre tous tes jeux d'un multiworld [Archipelago](https://archipelago.gg) (0.6.7) et répondre,
jeu par jeu, à la question : **« est-ce que je peux avancer dans ce jeu, au niveau des checks, sans le lancer ? »**

Pour chaque slot :
- **Niveau 1 (tous les jeux)** : checks faits / total, items reçus, **nouveaux items depuis ta dernière visite**
  (bouton « Marquer comme vu »), hints dans les deux sens, but atteint.
- **Niveau 2 (logique)** : nombre de **checks en logique** avec les items reçus et leur liste, les locations hintées
  mises en avant. La logique vient d'[Universal Tracker](https://github.com/FarisTheAncient/Archipelago/tree/tracker)
  piloté en headless. Jeux validés : voir [`docs/COMPAT.md`](docs/COMPAT.md).

**Zéro spoiler** : l'app ne sait que ce que sait un tracker classique (items reçus, checks, hints, `slot_data`,
datapackage et tes yamls). Elle se connecte en **lecture seule** (tag `Tracker`) : elle n'envoie jamais de check,
de message ni de demande de hint.

## Installation (Raspberry Pi / Linux, sans root)

Prérequis : Python 3.11 à 3.13 avec `venv`, Node 20+, git.

```bash
git clone https://github.com/Hikari-rom/archipelago-multitracker.git
cd archipelago-multitracker
bash scripts/bootstrap.sh
```

`bootstrap.sh` est idempotent : il clone Archipelago 0.6.7 dans `vendor/`, crée `.venv/`, installe les dépendances
(sans l'interface graphique kivy), télécharge les apworlds et Universal Tracker, puis construit le front.
Rien n'est installé hors du dossier du projet.

## Configurer la room

```bash
cp config/room.example.yaml config/room.yaml   # room.yaml n'est jamais commité (mot de passe)
```

```yaml
server: "archipelago.gg:38281"   # adresse de la room (wss:// puis ws:// sont essayés automatiquement)
password: "le mot de passe"
slots:
  - name: "Romain_Celeste"                # nom exact du slot
    game: "Celeste (Open World)"          # optionnel (le serveur le donne)
    yaml: "config/players/celeste.yaml"   # ton yaml pour ce jeu : nécessaire à la logique de certains jeux
```

- Mets tes yamls dans `config/players/` (un fichier par jeu, ou un fichier multi-documents ; ce dossier
  n'est pas commité).
- Les jeux qui savent se régénérer depuis le `slot_data` (colonne « UT sans yaml » de `COMPAT.md`) n'ont pas besoin
  du yaml. Pour les autres, sans yaml le badge affiche « Logique indisponible ».
- Si ton yaml contient des options aléatoires (`random`, poids), l'app reprend la valeur réellement tirée quand
  le jeu la met dans son `slot_data`, sinon elle prévient que la logique peut être approximative.
- Sur archipelago.gg, une room endormie peut **changer de port** au réveil : mets à jour `server` puis relance l'app.

## Lancer

```bash
scripts/app.sh start     # en arrière-plan, sur http://<ip-du-pi>:42753
scripts/app.sh status
scripts/app.sh logs
scripts/app.sh stop
```

Démarrage automatique (service utilisateur systemd, voir `deploy/multitracker.service`) :

```bash
mkdir -p ~/.config/systemd/user && cp deploy/multitracker.service ~/.config/systemd/user/
systemctl --user daemon-reload && systemctl --user enable --now multitracker
sudo loginctl enable-linger romain   # une fois : garder le service actif sans session ouverte
journalctl --user -u multitracker -f # logs du service
```

N'utilise pas `scripts/app.sh` et le service en même temps (même port) : `scripts/app.sh stop` avant d'activer le service.

Depuis le téléphone : `http://<ip-tailscale-du-pi>:42753` (l'app écoute sur toutes les interfaces).

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
sur `127.0.0.1:38281-38290`, bot qui envoie des checks, campagnes de validation de la logique
(`validate_logic.py`, `campaign.sh`). Seul ce code de test lit les spoilers et le multidata.

Docs : [`docs/API.md`](docs/API.md) (API REST + SSE), [`docs/COMPAT.md`](docs/COMPAT.md) (jeux),
[`DECISIONS.md`](DECISIONS.md), [`PROGRESS.md`](PROGRESS.md).

## Crédits et licences

- [Archipelago](https://github.com/ArchipelagoMW/Archipelago) (MIT), cloné dans `vendor/` au bootstrap.
- [Universal Tracker](https://github.com/FarisTheAncient/Archipelago/tree/tracker) de FarisTheAncient (MIT, licence du
  dépôt), téléchargé comme apworld et utilisé comme bibliothèque.
- Les apworlds des jeux appartiennent à leurs auteurs respectifs (liens dans `config/apworlds.yaml`).
