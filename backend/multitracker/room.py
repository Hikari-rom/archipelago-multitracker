"""archipelago.gg (WebHost) room helpers: slot discovery and current port, from the public room API.

Only public, non-spoiler information is used: the room status endpoint returns the slot names and
games (shown on the room page to anyone with the link) and the port the room currently listens on.
"""
from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from urllib.parse import urlparse

ROOM_PATH = re.compile(r"^/room/(?P<id>[A-Za-z0-9_-]{8,40})/?$")
USER_AGENT = "archipelago-multitracker (read-only tracker)"


class RoomError(ValueError):
    pass


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
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read(5 * 1024 * 1024)


def fetch_room(url: str, timeout: float = 15.0, wake: bool = False) -> RoomInfo:
    """Read the room status. With wake=True, first load the room page, which makes the WebHost start
    the room's server if it was asleep (exactly what opening the link in a browser does)."""
    base, host, room_id = parse_room_url(url)
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
