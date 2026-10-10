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
