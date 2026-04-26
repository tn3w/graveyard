from __future__ import annotations

from .patterns import H
from .regex import captures

NON_MOZILLA_BROWSERS: frozenset[str] = frozenset(
    {
        "Opera",
        "Webkit",
        "Midori",
        "Links",
        "ELinks",
        "Elinks",
        "w3m",
        "NetSurf",
        "iCab",
        "Surf",
        "Lynx",
        "NCSA_Mosaic",
        "NCSA",
        "Iron",
        "Uzbl",
        "Konqueror",
        "Epiphany",
        "Galeon",
        "Chimera",
        "SeaMonkey",
        "Camino",
        "K-Meleon",
        "Dillo",
        "Amaya",
        "OmniWeb",
        "Outlook-Express",
        "Thunderbird",
        "Dalvik",
        "Nokia",
        "NokiaN",
        "NokiaC",
        "NokiaE",
        "Samsung",
        "SAMSUNG",
        "SonyEricsson",
        "BlackBerry",
        "HTC",
        "LG",
        "HUAWEI",
        "Chrome",
        "Chromium",
    }
)


def first_captured_version(ua: str, key: str) -> str | None:
    caps = captures(H[key], ua)
    return caps[0] if caps and caps[0] else None


def has_any(ua: str, tokens: tuple[str, ...]) -> bool:
    return any(token in ua for token in tokens)


def comment_body(ua: str) -> str:
    return ua[ua.find("(") + 1 : ua.find(")")] if ")" in ua else ua
