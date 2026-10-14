"""Room URL guard: archipelago.gg must resolve to a public address, including through NAT64 (IPv6-only networks)."""
from __future__ import annotations

import socket

import pytest

from multitracker import room


def _resolve_to(monkeypatch, *ips: str) -> None:
    def fake_getaddrinfo(host, port, *args, **kwargs):
        return [(socket.AF_INET6 if ":" in ip else socket.AF_INET, socket.SOCK_STREAM, 6, "", (ip, port))
                for ip in ips]
    monkeypatch.setattr(room.socket, "getaddrinfo", fake_getaddrinfo)
    monkeypatch.delenv("MT_ROOM_HOSTS", raising=False)


def test_public_ipv4_accepted(monkeypatch):
    _resolve_to(monkeypatch, "159.195.59.157")
    room._check_target("https", "archipelago.gg")


def test_nat64_of_public_ipv4_accepted(monkeypatch):
    # phone hotspot (IPv6-only + DNS64): 159.195.59.157 is synthesized as 64:ff9b::9fc3:3b9d
    _resolve_to(monkeypatch, "64:ff9b::9fc3:3b9d")
    room._check_target("https", "archipelago.gg")


@pytest.mark.parametrize("ip", ["10.0.0.5", "127.0.0.1", "::1", "fe80::1", "64:ff9b::a00:5", "64:ff9b::7f00:1"])
def test_private_targets_refused(monkeypatch, ip):
    _resolve_to(monkeypatch, ip)
    with pytest.raises(room.RoomError, match="adresse privée"):
        room._check_target("https", "archipelago.gg")
