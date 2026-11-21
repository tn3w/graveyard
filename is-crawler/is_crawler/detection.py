from __future__ import annotations

import uaid

_REASONS = {"database", "no-comment"}


def is_crawler(user_agent: str) -> bool:
    return uaid.is_bot(user_agent)


def crawler_name(user_agent: str) -> str | None:
    found = uaid.identify(user_agent)
    return found.get("name") or found.get("browser")


def crawler_version(user_agent: str) -> str | None:
    found = uaid.identify(user_agent)
    return found.get("version") or found.get("browser_version")


def crawler_url(user_agent: str) -> str | None:
    return next(iter(uaid.identify(user_agent).get("urls", [])), None)


def crawler_contact(user_agent: str) -> str | None:
    return next(iter(uaid.identify(user_agent).get("emails", [])), None)


def crawler_matches(user_agent: str) -> list[str]:
    signals = uaid.identify(user_agent).get("signals", [])
    return [signal for signal in signals if signal not in _REASONS]


def crawler_match(user_agent: str) -> str | None:
    matches = crawler_matches(user_agent)
    return matches[0] if matches else None


def crawler_signals(user_agent: str) -> list[str]:
    found = uaid.identify(user_agent)
    signals = found.get("signals", [])
    checks = [
        ("bot_signal", bool(crawler_matches(user_agent))),
        ("no_browser_signature", "no-comment" in signals),
        ("known_tool", "database" in signals),
        ("url_in_ua", bool(found.get("urls"))),
    ]
    return [name for name, fired in checks if fired]
