from __future__ import annotations

from collections.abc import Iterable
from contextlib import contextmanager
import re
from typing import NamedTuple

import uaid


class CrawlerInfo(NamedTuple):
    url: str
    description: str
    tags: tuple[str, ...]
    rdns: tuple[str, ...]


_custom: dict[str, tuple[re.Pattern, CrawlerInfo]] = {}
_GOOD_TAGS = frozenset(
    {"search-engine", "social-preview", "feed-reader", "archiver", "academic"}
)
_BAD_TAGS = frozenset(
    {"ai-crawler", "scanner", "http-library", "browser-automation", "seo"}
)


def _as_set(tags: str | Iterable[str]) -> set[str]:
    return {tags} if isinstance(tags, str) else set(tags)


def _info(entry: dict) -> CrawlerInfo:
    return CrawlerInfo(
        entry.get("url", ""),
        entry.get("description", ""),
        tuple(entry.get("tags", ())),
        tuple(entry.get("rdns", ())),
    )


def crawler_info(user_agent: str) -> CrawlerInfo | None:
    for pattern, info in _custom.values():
        if pattern.search(user_agent):
            return info
    found = uaid.identify(user_agent)
    return _info(found) if "description" in found else None


def register_crawler(
    name: str,
    pattern: str,
    *,
    url: str = "",
    description: str = "",
    tags: Iterable[str] = (),
    rdns: Iterable[str] = (),
) -> None:
    info = CrawlerInfo(url, description, tuple(tags), tuple(rdns))
    _custom[name] = (re.compile(pattern), info)


def unregister_crawler(name: str) -> bool:
    return _custom.pop(name, None) is not None


def clear_custom_crawlers() -> None:
    _custom.clear()


@contextmanager
def custom_crawlers(*entries: dict):
    saved = dict(_custom)
    try:
        for entry in entries:
            register_crawler(**entry)
        yield
    finally:
        _custom.clear()
        _custom.update(saved)


def assert_crawler(user_agent: str) -> CrawlerInfo:
    info = crawler_info(user_agent)
    if info is None:
        raise ValueError(f"not a known crawler: {user_agent!r}")
    return info


def crawler_has_tag(user_agent: str, tags: str | Iterable[str]) -> bool:
    info = crawler_info(user_agent)
    return bool(info and _as_set(tags) & set(info.tags))


def is_search_engine(user_agent: str) -> bool:
    return crawler_has_tag(user_agent, "search-engine")


def is_ai_crawler(user_agent: str) -> bool:
    return crawler_has_tag(user_agent, "ai-crawler")


def is_ai_fetcher(user_agent: str) -> bool:
    return crawler_has_tag(user_agent, "ai-fetcher")


def is_seo(user_agent: str) -> bool:
    return crawler_has_tag(user_agent, "seo")


def is_social_preview(user_agent: str) -> bool:
    return crawler_has_tag(user_agent, "social-preview")


def is_advertising(user_agent: str) -> bool:
    return crawler_has_tag(user_agent, "advertising")


def is_archiver(user_agent: str) -> bool:
    return crawler_has_tag(user_agent, "archiver")


def is_feed_reader(user_agent: str) -> bool:
    return crawler_has_tag(user_agent, "feed-reader")


def is_monitoring(user_agent: str) -> bool:
    return crawler_has_tag(user_agent, "monitoring")


def is_scanner(user_agent: str) -> bool:
    return crawler_has_tag(user_agent, "scanner")


def is_academic(user_agent: str) -> bool:
    return crawler_has_tag(user_agent, "academic")


def is_http_library(user_agent: str) -> bool:
    return crawler_has_tag(user_agent, "http-library")


def is_browser_automation(user_agent: str) -> bool:
    return crawler_has_tag(user_agent, "browser-automation")


def is_good_crawler(user_agent: str) -> bool:
    return crawler_has_tag(user_agent, _GOOD_TAGS)


def is_bad_crawler(user_agent: str) -> bool:
    return crawler_has_tag(user_agent, _BAD_TAGS)


def iter_crawlers() -> Iterable[tuple[CrawlerInfo, str]]:
    rules, crawlers = uaid.data["rules"], uaid.data["crawlers"]
    names = {index: parts[0].strip(uaid.rule_edges) for parts, index in rules}
    return iter([(_info(entry), names[index]) for index, entry in enumerate(crawlers)])


def robots_agents_for_tags(tags: str | Iterable[str]) -> list[str]:
    return uaid.agents(*_as_set(tags))


def build_robots_txt(
    disallow: str | Iterable[str] = (),
    allow: str | Iterable[str] = (),
    path: str = "/",
    rules: Iterable[tuple[str, str | Iterable[str]]] = (),
) -> str:
    blocked = set(robots_agents_for_tags(disallow))
    allowed = sorted(set(robots_agents_for_tags(allow)) - blocked)
    blocks = [uaid.robots_txt(*_as_set(disallow), path=path)]
    if allowed:
        lines = [f"User-agent: {agent}" for agent in allowed]
        blocks.append("\n".join([*lines, f"Allow: {path}", ""]))
    for rule_path, rule_tags in rules:
        blocks.append(uaid.robots_txt(*_as_set(rule_tags), path=rule_path))
    return "\n".join(block for block in blocks if block)


def build_ai_txt(disallow: str | Iterable[str] = "ai-crawler") -> str:
    return uaid.robots_txt(*_as_set(disallow)).replace("User-agent:", "User-Agent:")
