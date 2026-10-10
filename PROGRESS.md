# Progression

## État actuel (5 lignes)
1. M0 fait : Pi inspecté, fichiers de suivi et squelette créés.
2. Prochaine étape : M1 (Archipelago 0.6.7 headless, apworlds, Universal Tracker).
3. App : pas encore lancée.
4. Tests : aucun pour l'instant.
5. Bloquants : aucun.

## Journal

### M0 — Prise en main (2026-10-10)
- Pi 5, 8 Go RAM (≈4,9 Go dispo), 4 cœurs, 96 Go libres, Python 3.13.5, Node 24.18, npm 11.16.
- Port 42753 libre. Ports occupés notables : 22, 80 (Apache, vhost par défaut), 5432 (Postgres local).
- Tailscale **absent** du Pi. Enigmatik : docker compose (back) / `next dev -H 0.0.0.0` (front), pas de déploiement
  en place. Voir DECISIONS.md D1.
- Vérifier : `cat BACKLOG.md`.

## À faire par Romain
- **Tailscale** n'est pas installé sur le Pi. Pour accéder à l'app depuis le téléphone hors du LAN :
  `curl -fsSL https://tailscale.com/install.sh | sh && sudo tailscale up`. L'app écoute sur `0.0.0.0:42753`,
  donc `http://<ip-tailscale-du-pi>:42753` fonctionnera sans autre réglage.

## Prochaines étapes
- M1 : `scripts/bootstrap.sh`, `config/apworlds.yaml`, `scripts/fetch_apworlds.py`, étude de compatibilité.
