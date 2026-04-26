from __future__ import annotations

from typing import Any

try:
    import re2 as _regex  # type: ignore[reportMissingImports]
except ImportError:
    import re as _regex


Pattern = Any


def compile_pattern(pattern: str) -> Pattern:
    return _regex.compile(pattern)


def captures(pattern: Pattern, value: str) -> tuple[str | None, ...]:
    match = pattern.search(value)
    return match.groups() if match else ()


def findall(pattern: Pattern, value: str) -> list[str]:
    matches = pattern.findall(value)
    if not matches:
        return []
    if isinstance(matches[0], tuple):
        return [item[0] for item in matches if item]
    return list(matches)


def is_match(pattern: Pattern, value: str) -> bool:
    return pattern.search(value) is not None


def sub(pattern: Pattern, value: str, replacement: str) -> str:
    return pattern.sub(replacement, value)
