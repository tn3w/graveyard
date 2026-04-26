from __future__ import annotations

from .browser import extract_browser
from .crawler import detect_crawler
from .crawler import explain_crawler as explain_crawler_heuristics
from .crawler import extract_crawler
from .models import BrowserInfo, CrawlerExplanation, CrawlerInfo, UserAgent
from .patterns import H
from .regex import is_match
from .shared import NON_MOZILLA_BROWSERS


def normalize_user_agent(user_agent: object) -> str:
    """Return a normalized user-agent string for tolerant parsing helpers."""
    if isinstance(user_agent, bytes):
        user_agent = user_agent.decode("utf-8", errors="replace")
    elif user_agent is None:
        return ""
    elif not isinstance(user_agent, str):
        user_agent = str(user_agent)

    parts = user_agent.replace("\r", " ").replace("\n", " ").split()
    return " ".join(parts)


def _looks_like_user_agent(value: str) -> bool:
    candidate = value.strip().strip("'\"")
    if not candidate:
        return False
    if is_match(H["browser"], candidate):
        return True
    if candidate.startswith("Mozilla/"):
        return detect_crawler(candidate)
    if "://" in candidate or "@" in candidate:
        return detect_crawler(candidate)
    first = candidate.split()[0] if candidate.split() else ""
    return "/" in first and detect_crawler(candidate)


def extract_user_agents(value: str) -> list[str]:
    """Extract user agent strings from arbitrary text, including log blobs."""
    user_agents: list[str] = []
    seen: set[str] = set()

    extracted: list[tuple[int, str]] = []
    for key in ("embedded_browser_ua", "embedded_crawler_ua", "quoted_value"):
        for match in H[key].finditer(value):
            candidate = match.group(0).strip().strip("'\"")
            if _looks_like_user_agent(candidate):
                extracted.append((match.start(), candidate))

    if extracted:
        for _, candidate in sorted(extracted, key=lambda item: item[0]):
            if candidate not in seen:
                user_agents.append(candidate)
                seen.add(candidate)
        return user_agents

    for raw_line in value.splitlines() or [value]:
        line = raw_line.strip()
        if not line:
            continue
        first = line.split()[0] if line.split() else ""
        product = first.split("/", 1)[0] if "/" in first else first
        is_standalone_browser = line.startswith("Mozilla/") or (
            is_match(H["browser"], line) and product in NON_MOZILLA_BROWSERS
        )
        is_standalone_crawler = (
            "/" in first and "Mozilla/" not in first[1:] and detect_crawler(line)
        )
        if (is_standalone_browser or is_standalone_crawler) and _looks_like_user_agent(
            line
        ):
            user_agents.append(line)

    return user_agents


def parse(
    user_agent: str,
    *,
    crawlers: bool = True,
    browser: bool = True,
) -> UserAgent:
    """Parse a user agent string into structured data.

    Args:
        user_agent: The raw UA string to parse.
        crawlers: Whether to detect and extract crawler info (default True).
        browser: Whether to extract browser/OS/device info (default True).
    """
    is_bot = detect_crawler(user_agent) if crawlers else False
    crawler_info = extract_crawler(user_agent) if (crawlers and is_bot) else None
    browser_info = extract_browser(user_agent) if browser else None
    return UserAgent(
        raw=user_agent,
        is_crawler=is_bot,
        crawler=crawler_info,
        browser=browser_info,
    )


def parse_or_none(
    user_agent: object,
    *,
    crawlers: bool = True,
    browser: bool = True,
) -> UserAgent | None:
    """Parse defensively and return None when the input normalizes to an empty string."""
    normalized = normalize_user_agent(user_agent)
    if not normalized:
        return None
    return parse(normalized, crawlers=crawlers, browser=browser)


def safe_parse(
    user_agent: object,
    *,
    crawlers: bool = True,
    browser: bool = True,
) -> UserAgent | None:
    """Alias for parse_or_none()."""
    return parse_or_none(user_agent, crawlers=crawlers, browser=browser)


def parse_crawler(user_agent: str) -> CrawlerInfo | None:
    """Return extracted crawler metadata when the UA is classified as a crawler."""
    return parse(user_agent, crawlers=True, browser=False).crawler


def parse_browser(user_agent: str) -> BrowserInfo:
    """Return extracted browser metadata for a user agent string."""
    parsed = parse(user_agent, crawlers=False, browser=True).browser
    assert parsed is not None
    return parsed


def is_crawler(user_agent: str) -> bool:
    """Return True if the user agent string belongs to a crawler or bot."""
    return detect_crawler(user_agent)


def is_browser(user_agent: str) -> bool:
    """Return True if the user agent string is not classified as a crawler."""
    return not is_crawler(user_agent)


def explain_crawler(user_agent: str) -> CrawlerExplanation:
    """Explain which crawler heuristics matched for the supplied UA string."""
    normalized = normalize_user_agent(user_agent)
    explanation = explain_crawler_heuristics(normalized)
    explanation.raw = user_agent
    explanation.normalized = normalized
    return explanation
