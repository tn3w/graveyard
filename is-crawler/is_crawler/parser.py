from __future__ import annotations

from dataclasses import asdict, dataclass, field
from functools import lru_cache
from typing import Any

import uaid

_DEVICES = {
    "desktop": "Desktop",
    "mobile": "Mobile",
    "tablet": "Tablet",
    "tv": "SmartTV",
    "console": "Console",
    "wearable": "Wearable",
}
_APPS = {"Facebook", "Instagram", "Snapchat", "TikTok", "LINE", "WeChat", "KakaoTalk"}


@dataclass
class UserAgent:
    raw: str
    product_token: str | None
    comment: str | None
    engine: str | None
    engine_version: str | None
    browser: str | None
    browser_version: str | None
    browser_major: str | None
    os: str | None
    os_version: str | None
    cpu: str | None
    device: str | None
    device_brand: str | None
    device_model: str | None
    rendering: str | None
    is_mobile: bool
    is_tablet: bool
    is_crawler: bool
    is_webview: bool = False
    is_headless: bool = False
    channel: str | None = None
    app: str | None = None
    app_version: str | None = None
    languages: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _comment(ua: str) -> str | None:
    start = ua.find("(")
    end = ua.find(")", start)
    return ua[start : end + 1] if 0 <= start < end else None


def _rendering(ua: str) -> str | None:
    if "KHTML, like Gecko" in ua:
        return "KHTML, like Gecko"
    return "KHTML" if "KHTML" in ua else None


def normalize_user_agent(value: object) -> str:
    if isinstance(value, bytes):
        value = value.decode("utf-8", errors="replace")
    elif value is None:
        return ""
    elif not isinstance(value, str):
        value = str(value)
    return " ".join(value.split())


@lru_cache(maxsize=4096)
def parse(ua: str) -> UserAgent:
    found = uaid.identify(ua)
    browser, version = found.get("browser"), found.get("browser_version")
    device = _DEVICES.get(found.get("device", ""))
    app = browser if browser in _APPS else None
    return UserAgent(
        raw=ua,
        product_token=next(iter(ua.split()), None),
        comment=_comment(ua),
        engine=found.get("engine"),
        engine_version=found.get("engine_version"),
        browser=browser,
        browser_version=version,
        browser_major=version.split(".", 1)[0] if version else None,
        os=found.get("os"),
        os_version=found.get("os_version"),
        cpu=found.get("cpu"),
        device=device,
        device_brand=found.get("brand"),
        device_model=found.get("model"),
        rendering=_rendering(ua),
        is_mobile=device == "Mobile",
        is_tablet=device == "Tablet",
        is_crawler=found["bot"],
        is_webview=browser == "Chrome WebView" or app is not None,
        is_headless=browser == "HeadlessChrome" or "headless" in found.get("signals", []),
        app=app,
        app_version=version if app else None,
        languages=found.get("languages", []),
    )


def parse_or_none(value: object) -> UserAgent | None:
    normalized = normalize_user_agent(value)
    return parse(normalized) if normalized else None


def is_crawler(ua: str) -> bool:
    return uaid.is_bot(ua)


def is_browser(ua: str) -> bool:
    return not is_crawler(ua)
