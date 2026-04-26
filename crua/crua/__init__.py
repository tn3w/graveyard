from __future__ import annotations

from .api import (
    explain_crawler,
    extract_user_agents,
    is_browser,
    is_crawler,
    normalize_user_agent,
    parse,
    parse_browser,
    parse_crawler,
    parse_or_none,
    safe_parse,
)
from .models import BrowserInfo, CrawlerExplanation, CrawlerInfo, UserAgent

__version__ = "1.1.0"

__all__ = [
    "BrowserInfo",
    "CrawlerExplanation",
    "CrawlerInfo",
    "UserAgent",
    "__version__",
    "explain_crawler",
    "extract_user_agents",
    "is_browser",
    "is_crawler",
    "normalize_user_agent",
    "parse",
    "parse_or_none",
    "parse_browser",
    "parse_crawler",
    "safe_parse",
]
