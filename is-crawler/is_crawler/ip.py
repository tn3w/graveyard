from __future__ import annotations

from functools import lru_cache
import socket

import uaid

__all__ = [
    "verify_crawler_ip",
    "reverse_dns",
    "forward_confirmed_rdns",
    "ip_in_range",
    "known_crawler_ip",
    "known_crawler_rdns",
]


def _address(ip: str) -> str | None:
    try:
        return str(uaid.normalize(ip.strip()))
    except ValueError:
        return None


@lru_cache(maxsize=1)
def _all_rdns_suffixes() -> tuple[str, ...]:
    rdns = [entry.get("rdns", []) for entry in uaid.data["crawlers"]]
    return tuple(sorted({suffix for suffixes in rdns for suffix in suffixes}))


def reverse_dns(ip: str) -> str | None:
    address = _address(ip)
    if address is None:
        return None
    try:
        return socket.gethostbyaddr(address)[0].lower().rstrip(".")
    except OSError:
        return None


def forward_confirmed_rdns(ip: str, suffixes: tuple[str, ...]) -> str | None:
    address = _address(ip)
    if address is None or not uaid.confirmed(address, tuple(suffixes)):
        return None
    return reverse_dns(address)


def ip_in_range(ip: str) -> bool:
    address = _address(ip)
    return address is not None and bool(uaid.networks(address))


def known_crawler_ip(ip: str) -> bool:
    return ip_in_range(ip)


def known_crawler_rdns(ip: str) -> bool:
    address = _address(ip)
    if address is None:
        return False
    if any(key.startswith(".") for key in uaid.networks(address)):
        return True
    return uaid.confirmed(address, _all_rdns_suffixes())


def verify_crawler_ip(user_agent: str, ip: str) -> bool:
    address = _address(ip)
    return address is not None and uaid.verify(user_agent, address, lookup=True)
