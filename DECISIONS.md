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
