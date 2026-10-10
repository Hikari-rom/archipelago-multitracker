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


async def open_socket(address: str, timeout: float = 15.0):
    """Open a websocket to the AP server, trying each candidate URL. Returns (socket, url)."""
    errors: list[str] = []
    for url in candidate_urls(address):
        try:
            sock = await asyncio.wait_for(
                websockets.connect(url, ssl=_ssl_context() if url.startswith("wss://") else None,
                                   max_size=MAX_MESSAGE_SIZE, ping_interval=30, ping_timeout=60,
                                   open_timeout=timeout),
                timeout=timeout + 1)
            return sock, url
        except (OSError, asyncio.TimeoutError, websockets.WebSocketException, ssl.SSLError) as exc:
            errors.append(f"{url}: {type(exc).__name__}: {exc}")
    raise ConnectionError("; ".join(errors))


def encode(messages: list[dict[str, Any]]) -> str:
    return json.dumps(messages, separators=(",", ":"))


def decode(data: str | bytes) -> list[dict[str, Any]]:
    msgs = json.loads(data)
    return msgs if isinstance(msgs, list) else [msgs]
