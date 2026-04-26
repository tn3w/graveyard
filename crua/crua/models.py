from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass
class CrawlerInfo:
    name: str | None
    version: str | None
    url: str | None

    def to_dict(self) -> dict[str, str | None]:
        return asdict(self)


@dataclass
class BrowserInfo:
    product_token: str | None
    comment: str | None
    engine: str | None
    engine_version: str | None
    browser: str | None
    browser_version: str | None
    os: str | None
    os_version: str | None
    device: str | None
    rendering: str | None

    def to_dict(self) -> dict[str, str | None]:
        return asdict(self)


@dataclass
class UserAgent:
    raw: str
    is_crawler: bool
    crawler: CrawlerInfo | None
    browser: BrowserInfo | None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class CrawlerExplanation:
    raw: str
    normalized: str
    is_crawler: bool
    matched: list[str]
    excluded: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
