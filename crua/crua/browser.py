from __future__ import annotations

from .models import BrowserInfo
from .patterns import H
from .regex import is_match
from .shared import first_captured_version, has_any

WINDOWS_NT: dict[str, str] = {
    "10.0": "10/11",
    "6.3": "8.1",
    "6.2": "8",
    "6.1": "7",
    "6.0": "Vista",
    "5.2": "XP x64",
    "5.1": "XP",
    "5.0": "2000",
}

WINDOWS_PHONE_NAMES = (
    ("Windows Phone OS", "Windows Phone OS"),
    ("Windows Phone", "Windows Phone"),
    ("Windows Mobile", "Windows Mobile"),
)
DIRECT_OS_NAMES = (
    (("CrOS",), "Chromium OS"),
    (("PLAYSTATION",), "PLAYSTATION"),
    (("PlayStation",), "PlayStation"),
    (("Nintendo",), "Nintendo"),
    (("SymbOS", "Symbian", "S60"), "Symbian"),
    (("Tizen",), "Tizen"),
    (("SunOS", "Solaris"), "Solaris"),
    (("FreeBSD",), "FreeBSD"),
    (("NetBSD",), "NetBSD"),
    (("OpenBSD",), "OpenBSD"),
    (("DragonFly",), "DragonFly"),
)
BROWSER_RULES: list[tuple[str, str, tuple[str, ...], bool]] = [
    ("Opera GX", "opera", ("OPRGX/",), True),
    ("Opera Touch", "opera_touch", ("OPT/",), True),
    ("Opera Mini", "opera_mini", ("Opera Mini/",), True),
    ("Opera Mobi", "opera_mobi", ("Opera Mobi/",), True),
    ("Opera Tablet", "opera_tablet", ("Opera Tablet/",), True),
    ("Brave", "brave", ("Brave/", "brave/"), True),
    ("Edge", "edge", ("Edg/", "Edge/", "EdgA/", "EdgiOS/"), True),
    ("Opera", "opera", ("OPR/",), True),
    ("Samsung Browser", "samsung", ("SamsungBrowser/",), True),
    ("UC Browser", "uc_browser", ("UCBrowser/",), True),
    ("Yandex", "yandex", ("YaBrowser/",), True),
    ("Google App", "gsa", ("GSA/",), True),
    ("Chrome iOS", "crios", ("CriOS/",), True),
    ("Firefox iOS", "fxios", ("FxiOS/",), True),
    ("Huawei Browser", "huawei", ("HuaweiBrowser/",), True),
    ("Silk", "silk", ("Silk/",), True),
    ("Vivaldi", "vivaldi", ("Vivaldi/",), True),
    ("Iron", "iron", ("Iron/",), True),
    ("RockMelt", "rockmelt", ("RockMelt/",), True),
    ("DuckDuckGo", "duckduckgo", ("DuckDuckGo/",), True),
    ("Waterfox", "waterfox", ("Waterfox/",), True),
    ("Whale", "whale", ("Whale/",), True),
    ("QQBrowser", "qqbrowser", ("QQBrowser/",), True),
    ("WeChat", "wechat", ("MicroMessenger/",), True),
    ("Instagram", "instagram", ("Instagram ",), True),
    ("Snapchat", "snapchat", ("Snapchat/",), True),
    ("TikTok", "tiktok", ("musically_go/",), True),
    ("Facebook", "facebook", ("FBAV/", "FBIOS/"), True),
    ("Avant", "avant", ("Avant Browser",), False),
    ("Maxthon", "maxthon", ("Maxthon", "MAXTHON"), True),
    ("Midori", "midori", ("Midori/",), True),
    ("iCab", "icab", ("iCab ", "iCab/"), True),
    ("OmniWeb", "omniweb", ("OmniWeb/",), True),
    ("Camino", "camino", ("Camino/",), True),
    ("Arora", "arora", ("Arora/",), True),
    ("Firebird", "firebird", ("Firebird/",), True),
    ("Fennec", "fennec", ("Fennec/",), True),
    ("SeaMonkey", "seamonkey", ("SeaMonkey/",), True),
    ("PaleMoon", "palemoon", ("PaleMoon/", "Palemoon/"), True),
    ("Flock", "flock", ("Flock/",), True),
    ("Iceweasel", "iceweasel", ("Iceweasel/", "iceweasel/"), True),
    ("K-Meleon", "k_meleon", ("K-Meleon/",), True),
    ("Epiphany", "epiphany", ("Epiphany/",), True),
    ("Lunascape", "lunascape", ("Lunascape",), True),
    ("Sleipnir", "sleipnir", ("Sleipnir/",), True),
    ("Netscape", "netscape", ("Netscape/",), True),
    ("Netscape", "netscape_nav", ("Navigator/",), True),
    ("Tesla", "tesla", ("QtCarBrowser", "Tesla/"), False),
    ("Chromium", "chromium", ("Chromium/",), True),
]
ENGINE_RULES: list[tuple[str, str, tuple[str, ...]]] = [
    ("Goanna", "goanna_version", ("Goanna/",)),
    ("Presto", "presto_version", ("Presto/",)),
    ("Trident", "trident_version", ("Trident/",)),
    ("Gecko", "gecko_version", ("Gecko/",)),
]
DIRECT_DEVICE_TYPES = (
    (("Xbox", "PlayStation", "PLAYSTATION", "Nintendo"), "Console"),
    (("QtCarBrowser",), "Embedded"),
    (("SMART-TV", "SmartTV", "HbbTV"), "SmartTV"),
    (("SHIELD Android TV", "Android TV"), "SmartTV"),
    (("iPad",), "Tablet"),
    (("iPhone", "iPod"), "Mobile"),
)


def detect_os(ua: str) -> tuple[str | None, str | None]:
    for token, name in WINDOWS_PHONE_NAMES:
        if token in ua:
            return name, None

    if has_any(ua, ("Windows", "windows")):
        if "Xbox" in ua:
            return "Xbox", None
        version = first_captured_version(ua, "windows_nt")
        if version:
            return "Windows", WINDOWS_NT.get(version, version)
        if is_match(H["windows_legacy"], ua):
            return "Windows", None

    for tokens, name in DIRECT_OS_NAMES:
        if has_any(ua, tokens):
            return name, None

    if "iPhone OS" in ua or ("CPU OS" in ua and "iPad" not in ua):
        version = first_captured_version(ua, "ios_version")
        if version:
            return "iOS", version.replace("_", ".")
        return "iOS", None

    if "iPad" in ua and "CPU OS" in ua:
        version = first_captured_version(ua, "ios_version")
        if "CriOS/" in ua:
            if version:
                return "iOS", version.replace("_", ".")
            return "iOS", None
        if version:
            return "iPadOS", version.replace("_", ".")
        return "iPadOS", None

    if has_any(ua, ("Mac OS X", "Macintosh", "PPC Mac OS", "Mac_PowerPC")):
        version = first_captured_version(ua, "mac_version")
        if version:
            return "macOS", version.replace("_", ".")
        return "macOS", None

    if "Android" in ua:
        return "Android", first_captured_version(ua, "android_version")

    if "iPad" in ua:
        return "iPadOS", None

    if has_any(ua, ("Linux", "X11")):
        distro = first_captured_version(ua, "linux_distro")
        if distro:
            return distro, None
        return "Linux", None

    return None, None


def detect_engine(ua: str) -> tuple[str | None, str | None]:
    name, version = _detect_rule_version(ua, ENGINE_RULES[:2])
    if name:
        return name, version

    if "AppleWebKit/" in ua:
        version = first_captured_version(ua, "webkit_version")
        if "Trident/" in ua:
            return "Trident", first_captured_version(ua, "trident_version")
        if "Blink" in ua or _is_blink_era(ua):
            return "Blink", version
        return "AppleWebKit", version

    if "KHTML" in ua and "Gecko" not in ua:
        return "KHTML", None

    name, version = _detect_rule_version(ua, ENGINE_RULES[2:])
    if name:
        return name, version

    return None, None


def _is_blink_era(ua: str) -> bool:
    if any(
        tok in ua
        for tok in (
            "OPR/",
            "Edg/",
            "EdgA/",
            "EdgiOS/",
            "Brave/",
            "SamsungBrowser/",
            "YaBrowser/",
            "Vivaldi/",
            "Iron/",
            "RockMelt/",
            "Flock/3",
        )
    ):
        return True
    for key in ("chrome", "chromium"):
        version = first_captured_version(ua, key)
        if version:
            major = version.split(".")[0]
            return major.isdigit() and int(major) >= 28
    return False


def _detect_rule_version(
    ua: str,
    rules: (
        tuple[tuple[str, str, tuple[str, ...]], ...]
        | list[tuple[str, str, tuple[str, ...]]]
    ),
) -> tuple[str | None, str | None]:
    for name, key, indicators in rules:
        if has_any(ua, indicators):
            version = first_captured_version(ua, key)
            if version:
                return name, version
    return None, None


def _detect_browser_rule(ua: str) -> tuple[str | None, str | None]:
    for name, key, indicators, needs_version in BROWSER_RULES:
        if not has_any(ua, indicators):
            continue
        version = first_captured_version(ua, key)
        if version or not needs_version:
            return name, version
    return None, None


def detect_browser(ua: str) -> tuple[str | None, str | None]:
    if ("iPad" in ua or "iPhone" in ua) and "CriOS/" in ua:
        version = first_captured_version(ua, "crios")
        if version:
            return "Mobile Chrome", version

    name, version = _detect_browser_rule(ua)
    if name:
        return name, version

    if "Chrome/" in ua:
        version = first_captured_version(ua, "chrome")
        if version:
            if "; wv)" in ua and "Version/" in ua:
                return "Chrome WebView", version
            if ("Android" in ua or "iPad" in ua) and "Mobile Safari/" in ua:
                return "Mobile Chrome", version
            return "Chrome", version

    if "Firefox/" in ua:
        version = first_captured_version(ua, "firefox")
        if version:
            if "Android" in ua and "Mobile;" in ua:
                return "Mobile Firefox", version
            return "Firefox", version

    if "Opera" in ua:
        version = first_captured_version(ua, "opera_legacy")
        if version:
            return "Opera", version

    if "MSIE " in ua and "IEMobile" not in ua:
        version = first_captured_version(ua, "ie_msie")
        if version:
            return "IE", version

    if "Konqueror/" in ua:
        version = first_captured_version(ua, "konqueror")
        if version:
            return "Konqueror", version

    if "IEMobile" in ua:
        version = first_captured_version(ua, "iemobile")
        if version:
            return "IEMobile", version

    if "Android" in ua and "Version/" in ua and "Safari/" in ua:
        if "Chrome/" not in ua or "; wv)" not in ua:
            version = first_captured_version(ua, "safari_version")
            if version and ("Chrome/" not in ua or "Mobile Safari/" in ua):
                return "Android Browser", version

    if "Safari/" in ua and "Version/" in ua and "Chrome/" not in ua:
        version = first_captured_version(ua, "safari_version")
        if version:
            if "Mobile/" in ua or "Mobile Safari/" in ua:
                return "Mobile Safari", version
            return "Safari", version

    if "Safari/" in ua and "Chrome/" not in ua and "Version/" not in ua:
        version = first_captured_version(ua, "mobile_safari")
        if version:
            return "Safari", version

    if is_match(H["links"], ua):
        return "Links", None

    return None, None


def detect_device(ua: str) -> str:
    for tokens, device in DIRECT_DEVICE_TYPES:
        if has_any(ua, tokens):
            return device
    if "Tesla/" in ua and "Android" not in ua:
        return "Embedded"
    if "Tizen" in ua and ("SMART-TV" in ua or "TV" in ua):
        return "SmartTV"
    if "Android" in ua:
        return "Mobile" if "Mobile" in ua else "Tablet"
    if "Mobile" in ua:
        return "Mobile"
    return "Desktop"


def extract_browser(ua: str) -> BrowserInfo:
    product_token = ua.split()[0] if ua.split() else None

    open_idx = ua.find("(")
    close_idx = ua.find(")", open_idx) if open_idx >= 0 else -1
    comment = (
        ua[open_idx : close_idx + 1] if open_idx >= 0 and close_idx > open_idx else None
    )

    rendering = None
    if "KHTML, like Gecko" in ua:
        rendering = "KHTML, like Gecko"
    elif "KHTML" in ua:
        rendering = "KHTML"

    engine, engine_version = detect_engine(ua)
    browser, browser_version = detect_browser(ua)
    os_name, os_version = detect_os(ua)
    device = detect_device(ua)

    return BrowserInfo(
        product_token=product_token,
        comment=comment,
        engine=engine,
        engine_version=engine_version,
        browser=browser,
        browser_version=browser_version,
        os=os_name,
        os_version=os_version,
        device=device,
        rendering=rendering,
    )
