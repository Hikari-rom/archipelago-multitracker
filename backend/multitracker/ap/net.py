"""Low-level Archipelago websocket helpers: address resolution (wss then ws), JSON framing."""
from __future__ import annotations

import asyncio
import json
import ssl
from typing import Any

import certifi
import websockets

AP_VERSION = {"major": 0, "minor": 6, "build": 7, "class": "Version"}
MAX_MESSAGE_SIZE = 64 * 1024 * 1024  # datapackages can be large


def candidate_urls(address: str) -> list[str]:
    """URLs to try for a server address, like the official clients: secure first, then plain.

    "archipelago.gg:38281" -> ["wss://archipelago.gg:38281", "ws://archipelago.gg:38281"].
    An explicit ws:// or wss:// scheme is respected as is.
    """
    address = address.strip()
    if address.startswith(("ws://", "wss://")):
        return [address]
    if address.startswith("archipelago://"):
        address = address[len("archipelago://"):]
    if ":" not in address.rsplit("]", 1)[-1]:
        address += ":38281"
    return [f"wss://{address}", f"ws://{address}"]


def _ssl_context() -> ssl.SSLContext:
    return ssl.create_default_context(ssl.Purpose.SERVER_AUTH, cafile=certifi.where())


async def open_socket(address: str, timeout: float = 15.0, secure_probe_timeout: float = 5.0):
    """Open a websocket to the AP server, trying each candidate URL. Returns (socket, url).

    When falling back is possible (no explicit scheme), the wss attempt gets a short timeout: a TLS
    handshake against a plain ws server can otherwise hang. A certificate verification failure is
    never a reason to fall back to plaintext: it is raised.
    """
    urls = candidate_urls(address)
    errors: list[str] = []
    for i, url in enumerate(urls):
        attempt_timeout = secure_probe_timeout if i < len(urls) - 1 else timeout
        try:
            sock = await asyncio.wait_for(
                websockets.connect(url, ssl=_ssl_context() if url.startswith("wss://") else None,
                                   max_size=MAX_MESSAGE_SIZE, ping_interval=30, ping_timeout=60,
                                   open_timeout=attempt_timeout),
                timeout=attempt_timeout + 1)
            return sock, url
        except ssl.SSLCertVerificationError as exc:
            raise ConnectionError(f"{url}: certificat TLS invalide ({exc.verify_message})") from exc
        except (OSError, asyncio.TimeoutError, websockets.WebSocketException, ssl.SSLError) as exc:
            errors.append(f"{url}: {type(exc).__name__}: {exc}")
    raise ConnectionError("; ".join(errors))


def encode(messages: list[dict[str, Any]]) -> str:
    return json.dumps(messages, separators=(",", ":"))


def decode(data: str | bytes) -> list[dict[str, Any]]:
    msgs = json.loads(data)
    return msgs if isinstance(msgs, list) else [msgs]
