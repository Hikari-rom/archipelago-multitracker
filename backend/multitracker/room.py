"""archipelago.gg (WebHost) room helpers: slot discovery and current port, from the public room API.

Only public, non-spoiler information is used: the room status endpoint returns the slot names and
games (shown on the room page to anyone with the link) and the port the room currently listens on.
"""
from __future__ import annotations

import ipaddress
import json
import os
import re
import socket
import urllib.error
import urllib.request
from dataclasses import dataclass
from urllib.parse import urlparse

ROOM_PATH = re.compile(r"^/room/(?P<id>[A-Za-z0-9_-]{8,40})/?$")
USER_AGENT = "archipelago-multitracker (read-only tracker)"


class RoomError(ValueError):
    pass


# Only these WebHost sites may be queried (the Pi fetches the URL: keep it from probing the LAN).
# Extra hosts: MT_ROOM_HOSTS="host1,host2" (e.g. a self-hosted WebHost).
DEFAULT_HOSTS = {"archipelago.gg"}


def allowed_hosts() -> set[str]:
    extra = {h.strip().lower() for h in os.environ.get("MT_ROOM_HOSTS", "").split(",") if h.strip()}
    return DEFAULT_HOSTS | extra


def _check_target(scheme: str, host: str) -> None:
    host = host.lower()
    if host not in allowed_hosts():
        raise RoomError(f"site non autorisé : {host} (autorisés : {', '.join(sorted(allowed_hosts()))} ; "
                        "voir MT_ROOM_HOSTS)")
    explicitly_allowed = host in {h.strip().lower() for h in os.environ.get("MT_ROOM_HOSTS", "").split(",")}
    if scheme != "https" and not explicitly_allowed:
        raise RoomError("seules les URLs https sont acceptées")
    if not explicitly_allowed:
        try:
            infos = socket.getaddrinfo(host, 443, proto=socket.IPPROTO_TCP)
        except OSError as exc:
            raise RoomError(f"impossible de résoudre {host}") from exc
        for info in infos:
            ip = ipaddress.ip_address(info[4][0])
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
                raise RoomError(f"{host} pointe vers une adresse privée ({ip}) : refusé")


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None  # a redirect is reported as an HTTP error instead of being followed


@dataclass
class RoomInfo:
    url: str
    host: str
    port: int | None
    players: list[tuple[str, str]]  # (slot name, game)

    @property
    def server(self) -> str | None:
        return f"{self.host}:{self.port}" if self.port else None


def parse_room_url(url: str) -> tuple[str, str, str]:
    """'https://archipelago.gg/room/AbC...' -> (scheme://host base, host, room id)."""
    parsed = urlparse(url.strip())
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise RoomError("URL de room invalide (attendu : https://archipelago.gg/room/...)")
    match = ROOM_PATH.match(parsed.path)
    if not match:
        raise RoomError("URL de room invalide : le chemin doit être /room/<identifiant>")
    base = f"{parsed.scheme}://{parsed.netloc}"
    return base, parsed.hostname, match.group("id")


def _get(url: str, timeout: float) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json, text/html"})
    opener = urllib.request.build_opener(_NoRedirect)
    with opener.open(req, timeout=timeout) as resp:
        return resp.read(5 * 1024 * 1024)


def fetch_room(url: str, timeout: float = 15.0, wake: bool = False) -> RoomInfo:
    """Read the room status. With wake=True, first load the room page, which makes the WebHost start
    the room's server if it was asleep (exactly what opening the link in a browser does)."""
    base, host, room_id = parse_room_url(url)
    _check_target(urlparse(base).scheme, host)
    try:
        if wake:
            _get(f"{base}/room/{room_id}", timeout)
        data = json.loads(_get(f"{base}/api/room_status/{room_id}", timeout))
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            raise RoomError("room introuvable (lien expiré ou erroné ?)") from exc
        raise RoomError(f"le site a répondu {exc.code}") from exc
    except (urllib.error.URLError, OSError, ValueError) as exc:
        raise RoomError(f"impossible de joindre {host} : {exc}") from exc
    players = [(str(p[0]), str(p[1])) for p in data.get("players", []) if isinstance(p, (list, tuple)) and len(p) >= 2]
    port = data.get("last_port")
    port = int(port) if isinstance(port, int) and port > 0 else None
    return RoomInfo(url=f"{base}/room/{room_id}", host=host, port=port, players=players)
