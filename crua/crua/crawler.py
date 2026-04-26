from __future__ import annotations

from .models import CrawlerExplanation, CrawlerInfo
from .patterns import (
    BROWSER_OVERRIDE_SUBSTRINGS,
    KNOWN_TOKENS,
    LONG_SUFFIX_ALLOWLIST,
    LONG_SUFFIX_ENDINGS,
    H,
)
from .regex import captures, findall, is_match, sub
from .shared import NON_MOZILLA_BROWSERS, comment_body


def _has_suspicious_contact_marker(ua: str) -> bool:
    return ("compatible;" in ua and "+" in ua and "@" in ua) or "+http" in ua


def _has_compat_extension(ua: str) -> bool:
    if "(compatible;" not in ua:
        return False
    if is_match(H["browser"], ua):
        return False
    comment = comment_body(ua)
    parts = [part.strip() for part in comment.split(";")]
    if len(parts) < 4 or parts[0] != "compatible":
        return False
    tail = parts[-1]
    if not tail or len(tail) <= 3 or tail.lower() == tail:
        return False
    return tail.isalpha() and tail not in {
        "Windows",
        "Linux",
        "Macintosh",
        "PPC",
        "MSOCD",
        "FunWebProducts",
        "BOIE9",
        "ENUS",
        "CMDTDF",
        "LCJB",
        "DigExt",
        "Maxthon",
        "TheWorld",
        "Xbox",
        "FDM",
        "SlimBrowser",
    }


def _has_suspicious_x11_vendor(ua: str) -> bool:
    if "(X11;" not in ua or "; Linux" not in ua:
        return False
    comment = comment_body(ua)
    parts = [part.strip() for part in comment.split(";")]
    if len(parts) < 3 or parts[0] != "X11":
        return False
    vendor = parts[1]
    if (
        not vendor
        or " " in vendor
        or "/" in vendor
        or vendor in {"U", "Linux", "GNU/Linux"}
    ):
        return False
    return vendor.casefold() not in {
        "ubuntu",
        "fedora",
        "debian",
        "centos",
        "mageia",
        "arch",
        "mint",
        "suse",
        "opensuse",
        "gentoo",
        "kali",
        "freebsd",
        "netbsd",
        "openbsd",
        "dragonfly",
        "haiku",
        "wayland like x11",
    }


def _has_suspicious_long_suffix(ua: str) -> bool:
    tail = ua.rsplit(" ", 1)[-1] if " " in ua else ""
    if "/" not in tail:
        return False
    name, _, version = tail.partition("/")
    if len(name) < 10 or not version[:1].isdigit():
        return False
    lowered = name.casefold()
    return not (
        is_match(H["browser"], tail)
        or lowered.endswith(LONG_SUFFIX_ENDINGS)
        or name in LONG_SUFFIX_ALLOWLIST
    )


def _has_uppercase_acronym_suffix(ua: str) -> bool:
    tail = ua.rsplit(" ", 1)[-1] if " " in ua else ""
    if "/" not in tail:
        return False
    name, _, version = tail.partition("/")
    return name.isupper() and 3 <= len(name) <= 10 and version[:4].isdigit()


def _has_headless_shell(ua: str) -> bool:
    return "HeadlessChrome/" in ua and " Edg/" not in ua and " Edge/" not in ua


def _has_vendor_comment_url(ua: str) -> bool:
    if "http://" not in ua and "https://" not in ua:
        return False
    if " Safari/" not in ua and " Firefox/" not in ua and " Mobile/" not in ua:
        return False
    last_open = ua.rfind("(")
    last_close = ua.rfind(")")
    if last_open < 0 or last_close < last_open:
        return False
    tail = ua[last_open + 1 : last_close]
    return "http://" in tail or "https://" in tail


def _has_browser_override(ua: str) -> bool:
    if any(token in ua for token in BROWSER_OVERRIDE_SUBSTRINGS):
        return True
    if "Konqueror/" in ua and "(Exabot-Thumbnails)" in ua:
        return True
    if (
        ua.endswith(" moatbot")
        and "Mac OS X 10_10_1" in ua
        and "Chrome/40.0.2214.111 Safari/537.36" in ua
    ):
        return True
    if ua.endswith("Xbox One)-agent"):
        return True
    return "MSIE " in ua and "Trident/" in ua and not ua.rstrip().endswith(")")


def _matched_crawler_heuristics(ua: str) -> list[str]:
    matched: list[str] = []
    checks = (
        ("browser_crawler_token", lambda value: is_match(H["browser_crawler"], value)),
        ("bot_signal", lambda value: is_match(H["bot_signals"], value)),
        ("suspicious_contact_marker", _has_suspicious_contact_marker),
        ("compat_extension", _has_compat_extension),
        ("headless_shell", _has_headless_shell),
        ("vendor_comment_url", _has_vendor_comment_url),
        ("suspicious_x11_vendor", _has_suspicious_x11_vendor),
        ("uppercase_acronym_suffix", _has_uppercase_acronym_suffix),
        ("suspicious_long_suffix", _has_suspicious_long_suffix),
    )
    for name, check in checks:
        if check(ua):
            matched.append(name)

    if is_match(H["suspicious_trailing_label"], ua) and "Mobile Safari/" not in ua:
        matched.append("suspicious_trailing_label")

    is_browser = is_match(H["browser"], ua)
    if ua[:8].lower() == "mozilla/" and not is_browser:
        matched.append("mozilla_without_browser_signature")

    product = ua.split("/")[0].split()[0] if ua else ""
    if (
        not is_browser
        and ua[:8].lower() != "mozilla/"
        and "Browser/" not in ua
        and "Browser " not in ua
        and product not in NON_MOZILLA_BROWSERS
    ):
        matched.append("non_browser_product")

    return matched


def detect_crawler(ua: str) -> bool:
    matched = _matched_crawler_heuristics(ua)
    if _has_browser_override(ua) and "browser_crawler_token" not in matched:
        return False
    return bool(matched)


def explain_crawler(ua: str) -> CrawlerExplanation:
    matched = _matched_crawler_heuristics(ua)
    excluded: list[str] = []
    if _has_browser_override(ua) and "browser_crawler_token" not in matched:
        excluded.append("browser_override")
        matched = []

    return CrawlerExplanation(
        raw=ua,
        normalized=ua,
        is_crawler=bool(matched) and not excluded,
        matched=matched,
        excluded=excluded,
    )


def extract_crawler(ua: str) -> CrawlerInfo:
    urls = findall(H["url"], ua)
    url = urls[0] if urls else None

    if not ua.startswith("Mozilla/5.0"):
        first = ua.split()[0] if ua.split() else ua
        parts = first.split("/", 1)
        return CrawlerInfo(
            name=parts[0] or None,
            version=parts[1] if len(parts) > 1 else None,
            url=url,
        )

    caps = captures(H["compatible"], ua)
    if caps:
        return CrawlerInfo(
            name=caps[0],
            version=caps[1] if len(caps) > 1 else None,
            url=url,
        )

    cleaned = sub(H["comment_block"], ua, "")
    for token in cleaned.split():
        name = token.split("/")[0] if "/" in token else token
        if name not in KNOWN_TOKENS:
            ver_caps = captures(H["token_version"], token[len(name) :])
            return CrawlerInfo(
                name=name,
                version=ver_caps[0] if ver_caps else None,
                url=url,
            )

    return CrawlerInfo(name=None, version=None, url=url)
